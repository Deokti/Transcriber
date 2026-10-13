"""Скачивание моделей с HuggingFace — своё, с продолжением после обрыва.

Почему своё. huggingface_hub 1.x качает каждый файл во временный файл с
уникальным именем и удаляет его при любой ошибке: сеть оборвалась на 2.9 ГБ
из 3 — начинай сначала, а FR-26 требует продолжения. Вдобавок у библиотеки
своё понятие «полного слепка», из-за которого скачанная нами модель не
открывалась без сети. Модель же — это пять файлов по прямым ссылкам, и
качать их можно самим, запросом Range с того места, где остановились.

Раскладка: <папка моделей>/<модель>/<файлы>. Недокачанное лежит рядом как
<имя>.part, ревизия хранилища — в файле .revision: если модель на сервере
обновилась между попытками, обрывки от старой ревизии не годятся и
выбрасываются. Большие файлы сверяются по SHA-256, который сообщает сервер.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from core.events import Cancelled, Code, CoreError

API = "https://huggingface.co/api/models/{repo}?blobs=true"
RESOLVE = "https://huggingface.co/{repo}/resolve/{revision}/{name}"

#: Сколько читаем за раз. Отмена проверяется между кусками.
CHUNK = 1024 * 1024

_HEADERS = {"User-Agent": "Transcriber"}

Progress = Callable[[int, int], None]
Cancel = Callable[[], bool]


@dataclass(frozen=True)
class Remote:
    """Файл модели на сервере."""

    name: str
    size: int
    sha256: str          # пусто у мелких файлов: сервер их суммой не снабжает


def listing(repo: str, patterns: list[str]) -> tuple[str, list[Remote]]:
    """Ревизия хранилища и нужные движку файлы из него."""
    request = urllib.request.Request(API.format(repo=repo), headers=_HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    files = [Remote(item["rfilename"], int(item.get("size") or 0),
                    (item.get("lfs") or {}).get("sha256", ""))
             for item in data.get("siblings", [])
             if any(fnmatch(item["rfilename"], pattern) for pattern in patterns)]
    return str(data.get("sha") or "main"), files


def download(repo: str, home: Path, patterns: list[str], *,
             on_progress: Progress | None = None,
             should_cancel: Cancel | None = None) -> Path:
    """Скачивает модель в папку home, продолжая то, что уже начато."""
    revision, files = listing(repo, patterns)
    if not any(f.name == "model.bin" for f in files):
        raise CoreError(Code.DOWNLOAD_FAILED, reason="no_model_in_repo", repo=repo)

    home.mkdir(parents=True, exist_ok=True)
    _forget_other_revision(home, revision)

    total = sum(f.size for f in files)
    done = 0
    for remote in files:
        final = home / remote.name
        if final.is_file() and final.stat().st_size == remote.size:
            done += remote.size           # уже на месте с прошлой попытки
            _say(on_progress, done, total)
            continue
        part = home / (remote.name + ".part")
        url = RESOLVE.format(repo=repo, revision=revision, name=remote.name)
        _fetch(url, part, remote.size, base=done, total=total,
               on_progress=on_progress, should_cancel=should_cancel)
        _verify(part, remote)
        part.replace(final)
        done += remote.size
    return home


def _forget_other_revision(home: Path, revision: str) -> None:
    """Обрывки другой ревизии выбрасываем: склеенный из двух версий файл — мусор."""
    marker = home / ".revision"
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() != revision:
        for item in home.iterdir():
            if item.is_file():
                item.unlink()
    marker.write_text(revision, encoding="utf-8")


def _fetch(url: str, part: Path, size: int, *, base: int, total: int,
           on_progress: Progress | None, should_cancel: Cancel | None) -> None:
    """Докачивает файл part до размера size, начиная с того, что уже есть."""
    have = part.stat().st_size if part.is_file() else 0
    if have > size:                     # обрывок длиннее файла — чужой, начинаем заново
        part.unlink()
        have = 0
    if have == size:
        return

    headers = dict(_HEADERS)
    if have:
        headers["Range"] = f"bytes={have}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        # 206 — сервер продолжает с нужного места; 200 — отдаёт файл целиком,
        # и тогда начатое придётся переписать
        resumed = have and response.status == 206
        if not resumed:
            have = 0
        with part.open("ab" if resumed else "wb") as file:
            while True:
                if should_cancel is not None and should_cancel():
                    raise Cancelled(stage="download")   # обрывок остаётся — для докачки
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                file.write(chunk)
                have += len(chunk)
                _say(on_progress, base + have, total)

    if have != size:
        raise CoreError(Code.DOWNLOAD_FAILED, reason="short_read",
                        file=part.name, got=have, expected=size)


def _verify(part: Path, remote: Remote) -> None:
    """Сверяет скачанное с суммой сервера. Не сошлось — обрывок не годится."""
    if not remote.sha256:
        return
    digest = hashlib.sha256()
    with part.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK), b""):
            digest.update(chunk)
    if digest.hexdigest() != remote.sha256:
        part.unlink(missing_ok=True)
        raise CoreError(Code.DOWNLOAD_FAILED, reason="checksum", file=remote.name)


def _say(on_progress: Progress | None, done: int, total: int) -> None:
    if on_progress is not None:
        on_progress(done, total)


def is_network_error(error: BaseException) -> bool:
    """Обрыв сети, а не наша ошибка: так окно решает, что сказать человеку."""
    return isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError))
