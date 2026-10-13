"""Markdown: тот же документ, но с разметкой — для заметок и вики.

В оформлении «по строкам» каждый сегмент — пункт списка с моментом начала.
Конец не пишем: в документе для чтения он лишний, следующий пункт и так
показывает, где кончился предыдущий. Точный диапазон — в txt и субтитрах.
"""
from __future__ import annotations

import re
from pathlib import Path

from core.asr.base import Segment
from core.formats.text import to_paragraphs
from core.profile import LAYOUT_PLAIN
from core.timecode import stamp

#: Знаки, которые Markdown прочёл бы как разметку: звёздочка сделала бы
#: курсив из обычной фразы, квадратные скобки — ссылку.
_SPECIAL = re.compile(r"([\\`*_\[\]<>#|])")


def escape(text: str) -> str:
    return _SPECIAL.sub(r"\\\1", text)


def write(path: Path, segments: list[Segment], *, layout: str,
          title: str = "", meta: str = "") -> Path:
    lines: list[str] = []
    if title:
        lines += [f"# {escape(title)}", ""]
    if meta:
        lines += [f"_{escape(meta)}_", ""]

    if layout == LAYOUT_PLAIN:
        for _started, paragraph in to_paragraphs(segments):
            lines += [escape(paragraph), ""]
    else:
        for s in segments:
            text = s.text.strip()
            if text:
                lines.append(f"- `{stamp(s.start)}` {escape(text)}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
