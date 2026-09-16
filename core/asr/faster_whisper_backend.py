"""Движок распознавания на faster-whisper.

Имя файла не `faster_whisper.py` нарочно: одноимённый модуль рядом с
импортом того же имени — классический способ импортировать самого себя.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Iterator

from core.asr.base import Segment, TranscriptionInfo
from core.events import Code, CoreError
from core.profile import Profile


class FasterWhisperBackend:
    """Обёртка над faster-whisper, хранящая загруженную модель.

    Модель держится в памяти между задачами: на large-v3 её загрузка стоит
    около 70 секунд, и платить их за каждый файл в очереди незачем.
    """

    def __init__(self, models_dir: Path | None = None) -> None:
        self._models_dir = models_dir
        self._model = None
        self._key: tuple[str, str, str] | None = None

    @property
    def loaded(self) -> tuple[str, str, str] | None:
        return self._key

    def load(self, model: str, device: str, compute: str) -> float:
        """Готовит модель, возвращает потраченные секунды (0 — была готова)."""
        key = (model, device, compute)
        if self._key == key and self._model is not None:
            return 0.0

        from faster_whisper import WhisperModel

        started = time.monotonic()
        try:
            self._model = WhisperModel(
                model,
                device=device,
                compute_type=compute,
                download_root=str(self._models_dir) if self._models_dir else None,
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

        raw_segments, raw_info = self._model.transcribe(
            str(audio),
            language=None if profile.language in (None, "", "auto") else profile.language,
            vad_filter=profile.vad,
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
