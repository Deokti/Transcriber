"""Текст (txt) и общая для документов склейка сегментов в абзацы.

Два вида оформления (FR-18):

- **по строкам с тайм-кодами** — сегмент на строку, «как есть», с началом и
  концом. Самый честный вид: по нему видно, что и где распознано;
- **связный текст** — сегменты склеены в абзацы, тайм-кодов нет. Для чтения
  и для того, чтобы отдать текст дальше.
"""
from __future__ import annotations

from pathlib import Path

from core.asr.base import Segment
from core.profile import LAYOUT_PLAIN
from core.timecode import stamp

#: Пауза, после которой начинается новый абзац.
PARAGRAPH_PAUSE = 1.5
#: Длина, после которой абзац разрывается даже без паузы.
PARAGRAPH_CHARS = 900

_SENTENCE_END = (".", "!", "?", "…")


def to_paragraphs(segments: list[Segment]) -> list[tuple[float, str]]:
    """Склеивает короткие куски в читаемые абзацы.

    Whisper режет речь на отрезки по пять-шесть секунд — читать такое тяжело.
    Границей абзаца считаем заметную паузу, конец предложения или накопленную
    длину. Возвращаем и время начала абзаца: документу оно не нужно, а тому,
    кто ищет место в записи, — пригодится.
    """
    paragraphs: list[tuple[float, str]] = []
    current: list[str] = []
    started = 0.0
    previous_end = 0.0

    for s in segments:
        text = s.text.strip()
        if not text:
            continue
        if not current:
            started = s.start
        else:
            pause = s.start - previous_end
            long_enough = sum(len(p) for p in current) >= PARAGRAPH_CHARS
            ended = current[-1].endswith(_SENTENCE_END)
            if (pause >= PARAGRAPH_PAUSE and ended) or long_enough:
                paragraphs.append((started, " ".join(current)))
                current, started = [], s.start
        current.append(text)
        previous_end = s.end

    if current:
        paragraphs.append((started, " ".join(current)))
    return paragraphs


def write(path: Path, segments: list[Segment], *, layout: str,
          title: str = "", meta: str = "") -> Path:
    """Текстовый файл в выбранном оформлении."""
    lines: list[str] = []
    head = " | ".join(part for part in (title, meta) if part)
    if head:
        lines += [f"# {head}", ""]

    if layout == LAYOUT_PLAIN:
        for _started, paragraph in to_paragraphs(segments):
            lines += [paragraph, ""]
    else:
        lines += [f"[{stamp(s.start)} --> {stamp(s.end)}] {s.text}" for s in segments]
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
