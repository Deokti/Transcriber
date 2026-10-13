"""Сегменты на диске — источник истины (принцип П-3).

Формат построчный (jsonl) нарочно: пишется по ходу распознавания, читается
кусками и не портится при обрыве — испорченной окажется последняя строка,
остальные целы. Из этого файла любой документ пересобирается за секунду,
без повторных 80 минут счёта.

После удачной работы файл по умолчанию убирается — человеку он рядом с
документом ни к чему (решение D-17). Но заголовок у него не только про
текст: в нём записано, чей это документ и с какими настройками он
посчитан. Без этого две «Урок 1.mp4» из разных папок делили бы один
документ в общей папке результата, а смена модели не замечалась бы. Поэтому
заголовок переезжает в папку данных программы — «квитанцией» в пару сотен
байт — и действует, пока жив хоть один документ, к которому он относится.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from core import platform
from core.asr.base import Segment

SUFFIX = ".segments.jsonl"

#: Папка квитанций внутри папки данных.
RECEIPTS = "receipts"


class SegmentWriter:
    """Пишет сегменты по одному, сразу сбрасывая на диск."""

    def __init__(self, path: Path, meta: dict[str, Any] | None = None) -> None:
        self.path = path
        self._meta = meta or {}
        self._file = None

    def __enter__(self) -> "SegmentWriter":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        forget(self.path)            # считаем заново — прежняя квитанция устарела
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
    а спрашивают обычно одно — какой моделью получен документ. Файла нет —
    смотрим квитанцию, оставшуюся от него в папке данных.
    """
    try:
        with path.open("r", encoding="utf-8") as file:
            first = file.readline()
    except OSError:
        return _receipt(path)
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
        for raw in file:
            line = raw.strip()
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


# --- квитанции ------------------------------------------------------------
def _receipt_path(path: Path) -> Path:
    key = hashlib.sha1(str(Path(path).resolve()).encode("utf-8")).hexdigest()[:16]
    return platform.paths().root / RECEIPTS / f"{key}.json"


def _receipt(path: Path) -> dict[str, Any]:
    """Заголовок из квитанции — если документы, к которым она относится, живы.

    Документ удалили — и квитанция ни о чём больше не говорит: иначе она
    продолжала бы утверждать, что имя занято, когда его уже никто не держит.
    """
    target = _receipt_path(path)
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    documents = record.get("documents", []) if isinstance(record, dict) else []
    if not any(Path(doc).is_file() for doc in documents):
        target.unlink(missing_ok=True)
        return {}
    head = record.get("meta", {})
    return head if isinstance(head, dict) else {}


def retire(path: Path, documents: list[Path]) -> int:
    """Убирает файл сегментов, оставляя квитанцию. Возвращает освобождённые байты.

    Без документов рядом убирать нельзя: тогда сегменты — единственное, что
    осталось от счёта. Квитанцию пишем раньше, чем удаляем файл: оборвётся
    между ними — останутся оба, а не ни одного.
    """
    head = meta(path)
    if not documents or not head or not path.is_file():
        return 0
    size = path.stat().st_size
    target = _receipt_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"meta": head, "documents": [str(d) for d in documents]},
                                 ensure_ascii=False), encoding="utf-8")
    path.unlink()
    return size


def forget(path: Path) -> None:
    """Квитанция больше не нужна: файл сегментов пишется заново."""
    try:
        _receipt_path(path).unlink(missing_ok=True)
    except OSError:
        pass
