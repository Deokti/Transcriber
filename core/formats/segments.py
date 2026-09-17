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


def mark_partial(path: Path) -> None:
    """Помечает файл как обрывок: работу отменили, это не вся запись.

    Заголовок пишется в самом начале, когда ещё неизвестно, дойдёт ли счёт
    до конца, — поэтому пометка дописывается задним числом. Строки с
    сегментами не трогаем, файл подменяется целиком и только после записи.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        head = json.loads(lines[0]) if lines else None
    except (OSError, ValueError):
        return
    if not isinstance(head, dict) or not isinstance(head.get("meta"), dict):
        return
    head["meta"]["partial"] = True
    lines[0] = json.dumps(head, ensure_ascii=False) + "\n"
    pending = path.with_name(path.name + ".tmp")
    try:
        pending.write_text("".join(lines), encoding="utf-8")
        pending.replace(path)
    except OSError:
        pending.unlink(missing_ok=True)


def _rows(path: Path) -> Iterator[dict]:
    """Строки файла одна за другой. Битую последнюю после обрыва пропускает."""
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue  # оборванный хвост — не повод терять остальное


def _segment(obj: dict) -> Segment:
    return Segment(
        start=float(obj.get("start", 0.0)),
        end=float(obj.get("end", 0.0)),
        text=obj.get("text", ""),
        no_speech_prob=float(obj.get("no_speech_prob", 0.0)),
        avg_logprob=float(obj.get("avg_logprob", 0.0)),
    )


def read(path: Path) -> tuple[dict[str, Any], list[Segment]]:
    """Читает файл целиком: заголовок и все сегменты списком."""
    meta: dict[str, Any] = {}
    segments: list[Segment] = []
    for obj in _rows(path):
        if "meta" in obj:
            meta = obj["meta"]
        else:
            segments.append(_segment(obj))
    return meta, segments


def iter_segments(path: Path) -> Iterator[Segment]:
    """Сегменты потоком, не держа файл в памяти: у длинной записи их тысячи."""
    for obj in _rows(path):
        if "meta" not in obj:
            yield _segment(obj)
