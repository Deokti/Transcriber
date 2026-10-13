"""Загрузка модели продолжается с места обрыва (FR-26).

Ошибка: huggingface_hub 1.x качает файл во временный файл с уникальным
именем и удаляет его при любой ошибке. Оборвалась сеть на 2.9 ГБ из 3 —
начинай сначала. Мы проверили на настоящей модели: оборвали на 43 МБ, на
диске осталось 3 МБ мелких файлов, вторая попытка пошла с нуля.

Теперь модель качается своим загрузчиком, запросом Range с места обрыва.
Проверяем без сети, на своём маленьком сервере, который отвечает как
HuggingFace: список файлов с размерами и суммами, файлы с поддержкой Range.

Заодно — то, что проверял прежний тест прогресса: показанное не превышает
размера модели (раньше счётчики библиотеки удваивали 145 МБ до 282) и
доходит ровно до конца.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core.env import hub, models
from core.events import Cancelled, CoreError

REPO = "test/faster-whisper-fake"
FILES = {
    "model.bin": bytes(range(256)) * 4096,          # 1 МБ
    "config.json": b'{"fake": true}',
    "tokenizer.json": b"{}" * 100,
    "README.md": b"not needed",                     # движку не нужен — качать не должны
}
asked: list[str] = []          # какие Range просили — по ним видно, продолжили ли


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path.startswith("/api/models/"):
            siblings = [{"rfilename": name, "size": len(data),
                         **({"lfs": {"sha256": hashlib.sha256(data).hexdigest()}}
                            if name == "model.bin" else {})}
                        for name, data in FILES.items()]
            body = json.dumps({"sha": "rev1", "siblings": siblings}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        name = self.path.rsplit("/", 1)[-1]
        data = FILES[name]
        wanted = self.headers.get("Range", "")
        asked.append(f"{name}:{wanted or 'всё'}")
        start = int(wanted.split("=")[1].split("-")[0]) if wanted else 0
        self.send_response(206 if wanted else 200)
        self.send_header("Content-Length", str(len(data) - start))
        self.end_headers()
        self.wfile.write(data[start:])


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    hub.API = base + "/api/models/{repo}"
    hub.RESOLVE = base + "/{repo}/resolve/{revision}/{name}"
    hub.CHUNK = 64 * 1024              # мелкими кусками, чтобы было где оборвать

    home = Path(tempfile.mkdtemp(prefix="transcriber-hub-")) / "fake"
    size = sum(len(data) for name, data in FILES.items() if name != "README.md")
    seen: list[tuple[int, int]] = []
    problems: list[str] = []

    try:
        try:
            hub.download(REPO, home, models.FILES,
                         on_progress=lambda d, t: seen.append((d, t)),
                         should_cancel=lambda: bool(seen) and seen[-1][0] >= size // 2)
            problems.append("загрузка не оборвалась")
        except Cancelled:
            pass
        part = home / "model.bin.part"
        kept = part.stat().st_size if part.exists() else 0
        print(f"оборвали на {seen[-1][0]} байт из {size} | на диске обрывок {kept} байт")
        if kept < size // 4:
            problems.append("обрывок не сохранился — докачивать нечего")

        seen.clear()
        hub.download(REPO, home, models.FILES, on_progress=lambda d, t: seen.append((d, t)))
        resumed = [a for a in asked if a.startswith("model.bin:bytes=")]
        print("вторая попытка просила:", resumed or "файл целиком")
        print(f"прогресс: первый отчёт {seen[0][0]}, последний {seen[-1][0]} из {seen[-1][1]}")

        if not resumed:
            problems.append("вторая попытка начала с нуля")
        if any(done > total for done, total in seen) or seen[-1] != (size, size):
            problems.append("прогресс вышел за размер модели или не дошёл до конца")
        if (home / "model.bin").read_bytes() != FILES["model.bin"]:
            problems.append("склеенный файл не совпадает с оригиналом")
        if (home / "README.md").exists():
            problems.append("скачан файл, который движку не нужен")
        if not models._complete(home):
            problems.append("модель не признана целой")

        # Испорченное по дороге не должно лечь на место готового файла
        broken = home / "other.bin.part"
        broken.write_bytes(b"broken")
        try:
            hub._verify(broken, hub.Remote("other.bin", 6, hashlib.sha256(b"intact").hexdigest()))
            problems.append("файл с чужой суммой принят")
        except CoreError:
            print("файл с чужой суммой отвергнут, обрывок удалён:", not broken.exists())
            if broken.exists():
                problems.append("испорченный обрывок остался и пойдёт в докачку")
    finally:
        server.shutdown()

    if problems:
        print("ПРОВАЛ:", "; ".join(problems))
        return 1
    print("УСПЕХ: загрузка продолжается с места обрыва, прогресс честный")
    return 0


if __name__ == "__main__":
    sys.exit(main())
