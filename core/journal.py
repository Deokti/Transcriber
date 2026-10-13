"""Журнал запуска: события ядра построчно, в JSON, без слов.

Окно пишет сюда всё, что приходит из ядра, кроме процентов, а экран
«Диагностика» показывает последний запуск. Слова подбираются при показе
(принцип П-1): журнал, записанный при русском интерфейсе, прочитается и
при английском. Командная строка ведёт свой журнал, уже словами: там
читатель — человек с текстовым редактором.

Пишется построчно и сразу на диск: если работа уронит программу, журнал
должен дожить до следующего запуска — ради этого он и ведётся.
"""
from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path

from core.events import Event, Kind

#: Имя файла в папке журналов. Один на окно: нужен последний запуск, а не история.
LAST_RUN = "last-run.jsonl"

#: Сколько строк читать с конца. Журнал больше этого — уже не про «последний запуск».
READ_LIMIT = 2000


def entry(event: Event, when: datetime | None = None) -> dict:
    return {
        "time": (when or datetime.now()).isoformat(timespec="seconds"),
        "kind": event.kind.value,
        "stage": event.stage.value if event.stage else "",
        "code": event.code or "",
        "data": event.data,
    }


def _jsonable(value):
    """Пути и перечисления — строкой; остального в событиях не бывает."""
    if isinstance(value, Enum):
        return value.value
    return str(value)


class Journal:
    """Открытый журнал: каждый новый запуск начинает файл заново."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._file = path.open("w", encoding="utf-8", buffering=1)

    def write(self, event: Event) -> None:
        # Проценты идут десятками в минуту и ничего не объясняют задним числом
        if event.kind is Kind.PROGRESS or self._file.closed:
            return
        line = json.dumps(entry(event), ensure_ascii=False, default=_jsonable)
        self._file.write(line + "\n")

    def close(self) -> None:
        self._file.close()


def read(path: Path) -> list[dict]:
    """Строки журнала по порядку. Нет файла или битая строка — не беда."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    result = []
    for line in lines[-READ_LIMIT:]:
        try:
            item = json.loads(line)
        except ValueError:
            continue         # строку оборвало падением программы — пропускаем
        if isinstance(item, dict):
            result.append(item)
    return result
