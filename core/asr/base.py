"""Граница движка распознавания.

Решение D-2: второй движок мы не строим — на маке работает тот же
faster-whisper, только на процессоре. Но граница здесь узкая нарочно:
если однажды понадобится whisper.cpp с Metal, менять придётся один файл,
а не половину конвейера.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol

from core.profile import Profile


@dataclass(frozen=True)
class Segment:
    """Кусок речи с тайм-кодами — единица выдачи движка.

    Два последних поля не нужны человеку, но нужны нам: по ним ловятся
    залипания модели ещё до того, как они попали в документ.
    """

    start: float
    end: float
    text: str
    no_speech_prob: float = 0.0
    avg_logprob: float = 0.0


@dataclass(frozen=True)
class TranscriptionInfo:
    language: str
    language_probability: float
    duration: float


class AsrBackend(Protocol):
    """Что обязан уметь движок распознавания."""

    def load(self, model: str, device: str, compute: str, cpu_threads: int = 0) -> None:
        """Приготовить модель. Повторный вызов с теми же значениями — бесплатный."""

    def downloaded(self, model: str) -> bool:
        """Лежит ли модель на диске.

        От этого зависит, полезет ли движок в сеть. Спрашивает стадия —
        чтобы сказать человеку, что сейчас будет качаться пара гигабайт.
        """

    def transcribe(self, audio: Path, profile: Profile) -> tuple[TranscriptionInfo, Iterator[Segment]]:
        """Отдать сведения о записи и поток сегментов.

        Поток ленивый: сегменты приходят по мере счёта, и стадия успевает
        писать их на диск. Поэтому обрыв на 70-й минуте не теряет 70 минут
        работы (решение D-7).
        """

    def unload(self) -> None:
        """Освободить память. Стадия уборки зовёт это в конце очереди."""
