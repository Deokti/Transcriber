"""Окружение выполнения задачи: инструменты, движок, события, отмена."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from core.asr.base import AsrBackend
from core.events import Cancelled, Emit, Event, Kind, Stage
from core.media import Tools
from core.platform import Paths


def _never() -> bool:
    return False


@dataclass
class RunContext:
    """То, что стадии получают одинаково и не создают сами.

    Отмена спрашивается, а не присылается: стадия сама выбирает безопасные
    места, где прерваться, — между сегментами, между файлами, между шагами.
    """

    paths: Paths
    tools: Tools
    backend: AsrBackend
    emit: Emit
    should_cancel: Callable[[], bool] = field(default=_never)

    def event(self, kind: Kind, stage: Stage | None = None,
              code: str | None = None, **data: Any) -> None:
        self.emit(Event(kind=kind, stage=stage, code=code, data=data))

    def check_cancel(self) -> None:
        if self.should_cancel():
            raise Cancelled()
