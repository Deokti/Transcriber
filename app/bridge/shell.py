"""Открыть готовое: документ — в его программе, папку — в проводнике.

Единственное место, где окно просит систему что-то сделать с файлом. Как
именно это делается на каждой системе, знает `core/platform` — принцип
П-5: различия платформ живут в одном модуле, а не расползаются по кнопкам.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Slot

from app.bridge.paths import clean
from core import platform


class ShellBridge(QObject):
    """Действия над готовыми файлами: открыть, показать в папке."""

    @Slot(str)
    def open(self, path: str) -> None:
        target = Path(clean(path))
        if target.exists():
            platform.open_file(target)

    @Slot(str)
    def reveal(self, path: str) -> None:
        """Показывает файл в проводнике. Нет файла — открываем папку."""
        target = Path(clean(path))
        if target.exists():
            platform.reveal_file(target)
        elif target.parent.is_dir():
            platform.open_file(target.parent)
