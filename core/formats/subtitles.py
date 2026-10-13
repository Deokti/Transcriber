"""Субтитры: SRT и WebVTT (FR-17).

Оформление здесь не применяется: субтитр — это и есть сегмент со своим
временем, склеить их в абзацы значит потерять, когда что говорилось.
Заголовка тоже нет: проигрыватель показал бы его поверх видео.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from core.asr.base import Segment
from core.timecode import stamp

#: Длина строки субтитра. Больше — глаз не успевает дочитать до смены кадра;
#: столько же советуют правила субтитров у вещательных компаний.
LINE_CHARS = 42


def _cues(segments: list[Segment]) -> list[tuple[float, float, str]]:
    """Сегменты, пригодные в субтитры: с текстом и с ненулевой длительностью."""
    cues = []
    for s in segments:
        text = " ".join(s.text.split())
        if not text:
            continue
        end = s.end if s.end > s.start else s.start + 1.0
        cues.append((s.start, end, "\n".join(textwrap.wrap(text, LINE_CHARS))))
    return cues


def write_srt(path: Path, segments: list[Segment], *, layout: str = "",
              title: str = "", meta: str = "") -> Path:
    blocks = [f"{number}\n{stamp(start, comma=True)} --> {stamp(end, comma=True)}\n{text}\n"
              for number, (start, end, text) in enumerate(_cues(segments), 1)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path


def write_vtt(path: Path, segments: list[Segment], *, layout: str = "",
              title: str = "", meta: str = "") -> Path:
    blocks = ["WEBVTT\n"]
    blocks += [f"{stamp(start)} --> {stamp(end)}\n{text}\n"
               for start, end, text in _cues(segments)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path
