"""Profile — все настройки задачи одним объектом.

Зачем так: когда настроек два десятка, они начинают протекать в сигнатуры
функций и в интерфейс по одной. Собранные вместе, они передаются насквозь,
сохраняются в файл как пресет и сравниваются целиком.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from core import platform

#: Что нужно получить на выходе.
TARGET_TEXT = "text"
TARGET_AUDIO = "audio"

#: Как оформлять текст в документе.
LAYOUT_TIMECODES = "timecodes"
LAYOUT_PLAIN = "plain"

#: Чувствительность к речи. Выше — в текст попадёт больше тихой речи,
#: ниже — меньше шума и случайных фраз на паузах.
SENSITIVITY_LOW = "low"
SENSITIVITY_MEDIUM = "medium"
SENSITIVITY_HIGH = "high"

#: Что делать с промежуточным WAV (FR-29). Выбирается до запуска.
TEMP_DELETE = "delete"
TEMP_KEEP = "keep"
TEMP_MOVE = "move"


@dataclass
class Profile:
    """Настройки одной задачи. Значения по умолчанию — из `Profile.defaults()`."""

    # что делаем
    target: str = TARGET_TEXT

    # подготовка звука
    loudnorm: bool = True
    denoise: bool = False
    trim_silence: bool = False       # обрезать тишину по краям записи
    track: int = 0
    skip_prepare: bool = False       # отдать исходник движку как есть

    # распознавание
    language: str = "ru"             # язык выбирает пользователь (решение D-4)
    model: str = "large-v3"
    device: str = "cuda"
    compute: str = "float16"
    beam: int = 5
    vad: bool = True
    condition_on_previous_text: bool = False   # главный предохранитель от залипаний
    initial_prompt: str = ""
    sensitivity: str = SENSITIVITY_MEDIUM      # порог VAD
    chunk_length: int = 30                     # длина фрагмента, секунды
    cpu_threads: int = 0                       # 0 — на усмотрение движка

    # выдача
    formats: list[str] = field(default_factory=lambda: ["txt"])
    layout: str = LAYOUT_TIMECODES
    output_dir: str | None = None
    force: bool = False              # перезаписывать готовое

    # уборка
    temp_action: str = TEMP_DELETE

    # как часто отчитываться о прогрессе, в минутах аудио
    progress_step_min: float = 5.0

    @classmethod
    def defaults(cls) -> "Profile":
        """Умолчания под конкретную машину: устройство, точность, модель."""
        device = platform.default_device()
        return cls(
            device=device,
            compute=platform.default_compute(device),
            model=platform.default_model(device),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Profile":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "Profile":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
