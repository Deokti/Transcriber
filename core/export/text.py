"""Сборка текстовых документов из сегментов.

Полный набор форматов — этап M5. Здесь то, что нужно этапу M1: txt в двух
видах оформления, чтобы повторить поведение прежнего скрипта.
"""
from __future__ import annotations

from pathlib import Path

from core.asr.base import Segment
from core.timecode import stamp

#: Пауза, после которой начинается новый абзац.
PARAGRAPH_PAUSE = 1.5
#: Длина, после которой абзац разрывается даже без паузы.
PARAGRAPH_CHARS = 900

_SENTENCE_END = (".", "!", "?", "…")


def write_timecoded(path: Path, segments: list[Segment], header: str = "") -> Path:
    """Строка на сегмент: `[ЧЧ:ММ:СС.ммм --> ЧЧ:ММ:СС.ммм] текст`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        if header:
            f.write(f"# {header}\n\n")
        for s in segments:
            f.write(f"[{stamp(s.start)} --> {stamp(s.end)}] {s.text}\n")
    return path


def to_paragraphs(segments: list[Segment]) -> list[tuple[float, str]]:
    """Склеивает короткие куски в читаемые абзацы.

    Whisper режет речь на отрезки по пять-шесть секунд — читать такое тяжело.
    Границей абзаца считаем заметную паузу, конец предложения или накопленную
    длину. Возвращаем время начала абзаца, чтобы по нему можно было прыгнуть
    в нужное место записи.
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


def write_plain(path: Path, segments: list[Segment], header: str = "") -> Path:
    """Связный текст абзацами, с тайм-кодом в начале каждого."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        if header:
            f.write(f"# {header}\n\n")
        for started, text in to_paragraphs(segments):
            f.write(f"[{stamp(started)}]\n{text}\n\n")
    return path
