"""Сегменты на диске — источник истины (принцип П-3).

Формат построчный (jsonl) нарочно: пишется по ходу распознавания, читается
кусками и не портится при обрыве — испорченной окажется последняя строка,
остальные целы. Из этого файла любой документ пересобирается за секунду,
без повторных 80 минут счёта.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from core.asr.base import Segment

SUFFIX = ".segments.jsonl"


class SegmentWriter:
    """Пишет сегменты по одному, сразу сбрасывая на диск."""

    def __init__(self, path: Path, meta: dict[str, Any] | None = None) -> None:
        self.path = path
        self._meta = meta or {}
        self._file = None

    def __enter__(self) -> "SegmentWriter":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8", buffering=1)
        self._write({"meta": self._meta})
        return self

    def __exit__(self, *exc: object) -> None:
        if self._file:
            self._file.close()
            self._file = None

    def _write(self, obj: dict) -> None:
        assert self._file is not None
        self._file.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def add(self, segment: Segment) -> None:
        self._write({
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text,
            "no_speech_prob": round(segment.no_speech_prob, 4),
            "avg_logprob": round(segment.avg_logprob, 4),
        })


def meta(path: Path) -> dict[str, Any]:
    """Только заголовок: чем и как считали этот текст.

    Читаем первую строку, а не файл целиком: у часовой лекции это мегабайты,
    а спрашивают обычно одно — какой моделью получен документ.
    """
    try:
        with path.open("r", encoding="utf-8") as file:
            first = file.readline()
    except OSError:
        return {}
    try:
        head = json.loads(first or "{}")
    except ValueError:
        return {}
    return head.get("meta", {}) if isinstance(head, dict) else {}


def read(path: Path) -> tuple[dict[str, Any], list[Segment]]:
    """Читает файл целиком. Битую последнюю строку после обрыва пропускает."""
    meta: dict[str, Any] = {}
    segments: list[Segment] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue  # оборванный хвост — не повод терять остальное
            if "meta" in obj:
                meta = obj["meta"]
                continue
            segments.append(Segment(
                start=float(obj.get("start", 0.0)),
                end=float(obj.get("end", 0.0)),
                text=obj.get("text", ""),
                no_speech_prob=float(obj.get("no_speech_prob", 0.0)),
                avg_logprob=float(obj.get("avg_logprob", 0.0)),
            ))
    return meta, segments


def iter_segments(path: Path) -> Iterator[Segment]:
    _meta, segments = read(path)
    yield from segments
