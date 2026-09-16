"""Мелочь, нужная всем мостам: путь из файлового диалога."""
from __future__ import annotations

from pathlib import Path


def clean(value: str) -> str:
    """Путь из файлового диалога приходит как file:///C:/… — приводим к обычному."""
    value = (value or "").strip()
    if value.startswith("file:///"):
        value = value[8:] if len(value) > 9 and value[9] == ":" else value[7:]
    return str(Path(value)) if value else ""
