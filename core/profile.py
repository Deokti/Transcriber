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

#: Что нужно получить на выходе (FR-8, FR-37).
TARGET_TEXT = "text"        # документ
TARGET_AUDIO = "audio"      # только звуковой файл, распознавания не будет
TARGET_BOTH = "both"        # и документ, и звуковой файл

#: Формат звукового файла. Первый — ровно то, что нужно движку
#: распознавания: если файл несут в другую программу, это самый дешёвый
#: вариант. Остальные — для людей и для монтажа.
AUDIO_WAV16 = "wav16"       # WAV 16 кГц моно
AUDIO_WAV48 = "wav48"       # WAV 48 кГц стерео
AUDIO_MP3 = "mp3"
AUDIO_M4A = "m4a"

#: Как оформлять текст в документе.
LAYOUT_TIMECODES = "timecodes"
LAYOUT_PLAIN = "plain"

#: Шумоподавление. В макете это три ступени, а не галочка: слабая чистка
#: убирает гул, сильная съедает окончания слов — выбор за человеком.
DENOISE_OFF = "off"
DENOISE_MEDIUM = "medium"
DENOISE_STRONG = "strong"

#: Чувствительность к речи. Выше — в текст попадёт больше тихой речи,
#: ниже — меньше шума и случайных фраз на паузах.
SENSITIVITY_LOW = "low"
SENSITIVITY_MEDIUM = "medium"
SENSITIVITY_HIGH = "high"

#: Что делать с промежуточным WAV (FR-29). Выбирается до запуска.
TEMP_DELETE = "delete"
TEMP_KEEP = "keep"
TEMP_MOVE = "move"

#: Настройки, от которых зависит сам текст. Поменял любую — готовые сегменты
#: уже не ответ на вопрос, и запись нужно считать заново. Остальное — формат,
#: оформление, папка, судьба WAV — на текст не влияет, и его можно менять
#: переэкспортом за секунду (сценарий 6.3). Устройство и точность сюда не
#: входят нарочно: разница в тексте между ними на уровне запятой, а пересчёт
#: стоит восемьдесят минут.
RECIPE = ("model", "language", "track", "loudnorm", "denoise", "trim_silence",
          "skip_prepare", "vad", "sensitivity", "chunk_length", "beam",
          "condition_on_previous_text", "initial_prompt")


def recipe(profile: "Profile") -> dict[str, Any]:
    """Рецепт текста: значения настроек из RECIPE."""
    return {name: getattr(profile, name) for name in RECIPE}


@dataclass
class Profile:
    """Настройки одной задачи. Значения по умолчанию — из `Profile.defaults()`."""

    # что делаем
    target: str = TARGET_TEXT
    audio_format: str = AUDIO_WAV16   # каким получится звуковой файл

    # подготовка звука
    loudnorm: bool = True
    denoise: str = DENOISE_OFF
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
    # Файл сегментов рядом с документом. Оставить — значит другой формат
    # потом соберётся за секунду, без повторного распознавания.
    keep_segments: bool = False

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
