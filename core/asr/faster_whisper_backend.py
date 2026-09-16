"""Движок распознавания на faster-whisper.

Имя файла не `faster_whisper.py` нарочно: одноимённый модуль рядом с
импортом того же имени — классический способ импортировать самого себя.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Iterator

from core.asr.base import Segment, TranscriptionInfo
from core.env import models as catalog
from core.events import Code, CoreError
from core.profile import (SENSITIVITY_HIGH, SENSITIVITY_LOW, SENSITIVITY_MEDIUM,
                          Profile)

#: Порог VAD — вероятность, при которой звук считается речью.
#: Чем ниже порог, тем охотнее движок признаёт речью тихое место,
#: то есть тем выше чувствительность.
SENSITIVITY_THRESHOLD = {
    SENSITIVITY_LOW: 0.65,
    SENSITIVITY_MEDIUM: 0.5,
    SENSITIVITY_HIGH: 0.35,
}


class FasterWhisperBackend:
    """Обёртка над faster-whisper, хранящая загруженную модель.

    Модель держится в памяти между задачами: на large-v3 её загрузка стоит
    около 70 секунд, и платить их за каждый файл в очереди незачем.
    """

    def __init__(self, models_dir: Path | None = None) -> None:
        self._models_dir = models_dir
        self._model = None
        self._key: tuple[str, str, str, int] | None = None

    @property
    def loaded(self) -> tuple[str, str, str, int] | None:
        return self._key

    def downloaded(self, model: str) -> bool:
        return bool(self._models_dir) and catalog.is_downloaded(model, self._models_dir)

    def load(self, model: str, device: str, compute: str, cpu_threads: int = 0) -> float:
        """Готовит модель, возвращает потраченные секунды (0 — была готова)."""
        key = (model, device, compute, cpu_threads)
        if self._key == key and self._model is not None:
            return 0.0

        from faster_whisper import WhisperModel

        # Модель уже на диске — в сеть не ходим. Иначе движок на каждом
        # запуске спрашивает HuggingFace, не появилась ли новая версия: в
        # плохой сети этот запрос висит минутами, а окно в это время молчит
        # и выглядит зависшим. Заодно это требование NFR-2: без нужды в
        # сеть не ходим.
        local_only = self.downloaded(model)

        started = time.monotonic()
        try:
            self._model = WhisperModel(
                model,
                device=device,
                compute_type=compute,
                cpu_threads=cpu_threads,   # 0 — на усмотрение движка
                download_root=str(self._models_dir) if self._models_dir else None,
                local_files_only=local_only,
            )
        except Exception as e:
            self._model = None
            self._key = None
            raise CoreError(Code.MODEL_LOAD_FAILED, model=model, device=device,
                            compute=compute, reason=repr(e)) from e
        self._key = key
        return time.monotonic() - started

    def transcribe(self, audio: Path, profile: Profile) -> tuple[TranscriptionInfo, Iterator[Segment]]:
        if self._model is None:
            raise CoreError(Code.MODEL_LOAD_FAILED, reason="model_not_loaded")

        from faster_whisper.vad import VadOptions

        threshold = SENSITIVITY_THRESHOLD.get(profile.sensitivity,
                                              SENSITIVITY_THRESHOLD[SENSITIVITY_MEDIUM])
        raw_segments, raw_info = self._model.transcribe(
            str(audio),
            language=None if profile.language in (None, "", "auto") else profile.language,
            vad_filter=profile.vad,
            vad_parameters=VadOptions(threshold=threshold),
            chunk_length=profile.chunk_length or None,
            condition_on_previous_text=profile.condition_on_previous_text,
            beam_size=profile.beam,
            initial_prompt=profile.initial_prompt or None,
        )

        info = TranscriptionInfo(
            language=raw_info.language or "",
            language_probability=float(raw_info.language_probability or 0.0),
            duration=float(raw_info.duration or 0.0),
        )

        def stream() -> Iterator[Segment]:
            for s in raw_segments:
                yield Segment(
                    start=float(s.start),
                    end=float(s.end),
                    text=s.text.strip(),
                    no_speech_prob=float(getattr(s, "no_speech_prob", 0.0) or 0.0),
                    avg_logprob=float(getattr(s, "avg_logprob", 0.0) or 0.0),
                )

        return info, stream()

    def unload(self) -> None:
        self._model = None
        self._key = None
