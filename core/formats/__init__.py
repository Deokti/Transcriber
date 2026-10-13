"""Писатели файлов: из сегментов получаются документы.

Здесь же список того, что уже умеем: спрашивают его и стадия конвейера,
и окно — чтобы в списке форматов не оказалось того, что программа не
соберёт. Знание одно, и живёт оно рядом с теми, кто пишет файлы.

Каждый формат — чистая функция от сегментов (принцип П-3): поэтому
переэкспорт стоит секунду, а не восемьдесят минут повторного счёта.
"""
from __future__ import annotations

from pathlib import Path

from core.asr.base import Segment
from core.formats import docx, markdown, subtitles, text

#: Формат → писатель. Порядок — тот, в каком их видит человек.
WRITERS = {
    "txt": text.write,
    "md": markdown.write,
    "docx": docx.write,
    "srt": subtitles.write_srt,
    "vtt": subtitles.write_vtt,
}

SUPPORTED = set(WRITERS)

#: Для списка в окне: множество порядка не держит, а алфавит здесь ни к чему.
ORDER = tuple(WRITERS)

#: Субтитры: у них нет оформления — каждый сегмент живёт со своим временем.
TIMED = {"srt", "vtt"}


def write(fmt: str, path: Path, segments: list[Segment], *, layout: str,
          title: str = "", meta: str = "") -> Path:
    """Пишет документ формата fmt. Неизвестный формат — KeyError, и это честно."""
    return WRITERS[fmt](path, segments, layout=layout, title=title, meta=meta)
