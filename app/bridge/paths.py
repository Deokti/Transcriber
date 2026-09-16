"""Мелочь, нужная всем мостам: путь из файлового диалога."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl


def clean(value) -> str:
    """Адрес из диалога превращаем в обычный путь.

    Диалоги и перетаскивание отдают адрес: file:///C:/Мои%20записи. Пробелы
    и кириллица в нём закодированы процентами, и если просто отрезать
    «file:///», в настройках окажется папка с «%20» в имени. Раскодировать
    умеет сам Qt — этим и пользуемся.
    """
    if isinstance(value, QUrl):
        return str(Path(value.toLocalFile())) if value.isLocalFile() else ""
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("file:"):
        url = QUrl(text)
        return str(Path(url.toLocalFile())) if url.isLocalFile() else ""
    return str(Path(text))
