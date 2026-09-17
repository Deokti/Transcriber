"""Job — одна задача: файл, настройки, состояние, созданные артефакты."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from core.asr.base import Segment
from core.media import MediaInfo
from core.profile import Profile


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Задача и всё, что о ней известно по ходу работы.

    `artifacts` — что создано на диске, по именам: `temp_wav`, `segments`,
    `txt`, `docx`… Из него же работает стадия уборки.
    """

    source: Path
    profile: Profile
    state: JobState = JobState.QUEUED
    media: MediaInfo | None = None
    artifacts: dict[str, Path] = field(default_factory=dict)
    segments: list[Segment] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    error_code: str | None = None
    error_data: dict = field(default_factory=dict)
    #: Имя результата, когда исходное занято чужим файлом (см. pipeline)
    alias: str | None = None

    @property
    def stem(self) -> str:
        return self.alias or self.source.stem

    @property
    def fingerprint(self) -> str:
        """Короткая метка пути: два «Урок 1.mp4» из разных папок различимы."""
        return hashlib.sha1(str(self.source.resolve()).encode("utf-8")).hexdigest()[:8]

    @property
    def output_dir(self) -> Path:
        return Path(self.profile.output_dir) if self.profile.output_dir else self.source.parent

    def output(self, suffix: str) -> Path:
        """Путь результата рядом с исходником или в заданной папке."""
        return self.output_dir / f"{self.stem}{suffix}"

    def beside(self, suffix: str) -> Path:
        """То же, но с оглядкой на исходник.

        Если исходник сам звуковой и лежит там, куда мы собрались писать,
        имя совпадёт — и результат затрёт оригинал. Тогда добавляем пометку.
        """
        target = self.output(suffix)
        return self.output("-audio" + suffix) if target == self.source else target
