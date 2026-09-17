"""Очередь принимает адреса, а не только строки.

Ошибка: перетаскивание и файловый диалог отдают список из QUrl, а не из
строк — QML так устроен. Мост, который умел разбирать только строку,
падал на первом же брошенном файле с AttributeError, и в очередь не
попадало ничего.

Проверяем оба вида, какими они приходят из окна: список QUrl (диалог и
перетаскивание) и строку с адресом. Имя с пробелами и кириллицей — не
украшение: именно на нём ломается разбор адреса по символам.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication

from app.bridge import QueueBridge, SettingsBridge

NAME = "Лекция 1 — введение.mp3"


def _clean(folder: Path) -> None:
    """Убирает за собой, не споря с ffprobe.

    Разбор идёт в рабочих потоках, и файл может быть ещё открыт: на Windows
    это отказ в доступе. Ждём немного, а не сумеем — оставляем системе:
    временная папка не стоит упавшего теста.
    """
    for _ in range(20):
        try:
            for item in folder.iterdir():
                item.unlink()
            folder.rmdir()
            return
        except OSError:
            time.sleep(0.1)


def main() -> int:
    _app = QGuiApplication(sys.argv)         # мостам нужен живой QGuiApplication
    folder = Path(tempfile.mkdtemp(prefix="transcriber-test-"))
    source = folder / NAME
    source.write_bytes(b"not really audio")   # разбор провалится, и это не мешает

    queue = QueueBridge(SettingsBridge())
    problems = []

    queue.add([QUrl.fromLocalFile(str(source))])
    if queue.count != 1:
        problems.append("список QUrl не принят")
    elif queue.files[0]["name"] != NAME:
        problems.append("имя испорчено: " + queue.files[0]["name"])

    queue.clear()
    queue.add([QUrl.fromLocalFile(str(source)).toString()])
    if queue.count != 1:
        problems.append("строка с адресом не принята")

    queue.clear()
    queue.add([QUrl.fromLocalFile(str(folder))])     # папку разворачиваем
    if queue.count != 1:
        problems.append(f"папка развёрнута неверно: файлов {queue.count}")

    _clean(folder)

    if problems:
        print("ПРОВАЛ: " + "; ".join(problems))
        return 1
    print("УСПЕХ: очередь принимает и QUrl, и строку, и папку")
    return 0


if __name__ == "__main__":
    sys.exit(main())
