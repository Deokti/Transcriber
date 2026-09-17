"""События и коды, которыми ядро разговаривает с внешним миром.

Ядро не печатает текст и не знает, на каком языке говорит пользователь
(принцип П-1, решение D-4). Наружу уходят код и данные, а фразу к ним
подбирает интерфейс — командная строка или окно.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class Kind(str, Enum):
    """Род события. Определяет, как интерфейс его показывает."""

    QUEUE_STARTED = "queue_started"
    QUEUE_DONE = "queue_done"
    JOB_STARTED = "job_started"
    STAGE_STARTED = "stage_started"
    PROGRESS = "progress"
    STAGE_DONE = "stage_done"
    INFO = "info"
    WARNING = "warning"
    FAILED = "failed"
    JOB_DONE = "job_done"


class Stage(str, Enum):
    """Стадии конвейера в порядке прохождения."""

    DOWNLOAD = "download"      # нужной модели нет на диске — качаем
    PROBE = "probe"
    PREPARE = "prepare"
    AUDIO = "audio"            # сохранить звуковой файл, если его просили
    TRANSCRIBE = "transcribe"
    CHECK = "check"
    EXPORT = "export"
    CLEANUP = "cleanup"


class Code:
    """Коды событий и ошибок.

    Строки, а не перечисление: коды уходят в json, в логи и в каталоги
    перевода, и им полезно оставаться читаемыми по дороге.
    """

    # окружение
    FFMPEG_MISSING = "FFMPEG_MISSING"
    FFPROBE_FAILED = "FFPROBE_FAILED"
    FFMPEG_FAILED = "FFMPEG_FAILED"
    CUDA_READY = "CUDA_READY"
    CUDA_UNAVAILABLE = "CUDA_UNAVAILABLE"
    DEVICE_FALLBACK = "DEVICE_FALLBACK"
    DISK_FULL = "DISK_FULL"

    # исходный файл
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    UNSUPPORTED_FILE = "UNSUPPORTED_FILE"
    SOURCE_INFO = "SOURCE_INFO"
    TRACKS_FOUND = "TRACKS_FOUND"
    NO_AUDIO_TRACK = "NO_AUDIO_TRACK"
    TRACK_FALLBACK = "TRACK_FALLBACK"

    # подготовка звука
    FILTERS_APPLIED = "FILTERS_APPLIED"
    AUDIO_READY = "AUDIO_READY"
    AUDIO_SAVED = "AUDIO_SAVED"        # звуковой файл лёг туда, где его ждут

    # модель и распознавание
    MODEL_MISSING = "MODEL_MISSING"
    MODEL_LOADING = "MODEL_LOADING"
    MODEL_READY = "MODEL_READY"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    LANGUAGE_DETECTED = "LANGUAGE_DETECTED"
    TRANSCRIBE_DONE = "TRANSCRIBE_DONE"

    # проверка качества
    QUALITY_CLEAN = "QUALITY_CLEAN"
    QUALITY_MINOR = "QUALITY_MINOR"
    QUALITY_STUCK = "QUALITY_STUCK"
    GAPS_FOUND = "GAPS_FOUND"

    # выдача и уборка
    OUTPUT_EXISTS = "OUTPUT_EXISTS"
    EXPORT_DONE = "EXPORT_DONE"
    TEMP_KEPT = "TEMP_KEPT"
    TEMP_DELETED = "TEMP_DELETED"
    TEMP_MOVED = "TEMP_MOVED"
    TEMP_MOVE_FAILED = "TEMP_MOVE_FAILED"

    # очередь и отмена
    STOP_REQUESTED = "STOP_REQUESTED"          # остановиться после текущего файла
    CANCEL_REQUESTED = "CANCEL_REQUESTED"      # бросить всё немедленно
    STOP_UNDONE = "STOP_UNDONE"                # передумали, работаем дальше
    PARTIAL_SAVED = "PARTIAL_SAVED"            # сохранено то, что успели посчитать
    JOB_ABORTED = "JOB_ABORTED"                # работа оборвалась не по нашей воле
    DOWNLOAD_STARTED = "DOWNLOAD_STARTED"      # началось скачивание модели
    DOWNLOAD_DONE = "DOWNLOAD_DONE"
    MODEL_LANGUAGE_MISMATCH = "MODEL_LANGUAGE_MISMATCH"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"

    # общее
    CANCELLED = "CANCELLED"
    UNEXPECTED = "UNEXPECTED"


@dataclass(frozen=True)
class Event:
    """Одно сообщение из ядра наружу.

    `data` — машинные значения (секунды, доли, пути, числа), из которых
    интерфейс собирает фразу. Готовых предложений здесь не бывает.
    """

    kind: Kind
    stage: Stage | None = None
    code: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


#: Куда ядро отдаёт события. Командная строка печатает, окно обновляет свойства.
Emit = Callable[[Event], None]


class CoreError(Exception):
    """Ошибка ядра: несёт код и данные, но не готовый текст."""

    def __init__(self, code: str, **data: Any) -> None:
        super().__init__(code)
        self.code = code
        self.data = data


class Cancelled(CoreError):
    """Работа прервана по просьбе пользователя."""

    def __init__(self, **data: Any) -> None:
        super().__init__(Code.CANCELLED, **data)
