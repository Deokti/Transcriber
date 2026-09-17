"""Стадия 2: ffmpeg вытаскивает и чистит звук."""
from __future__ import annotations

import time
from pathlib import Path

from core.context import RunContext
from core.events import Code, Kind, Stage
from core.job import Job
from core.media import build_filters, extract_audio
from core.media import encoding
from core.profile import AUDIO_WAV16, TARGET_AUDIO


def run(job: Job, ctx: RunContext) -> Path:
    """Возвращает путь к звуку, который пойдёт в распознавание."""
    if job.profile.skip_prepare:
        return job.source

    duration = job.media.duration if job.media else 0.0
    filters = build_filters(job.profile.loudnorm, job.profile.denoise)

    # Распознавания не будет — значит это и есть заказанный файл, и делать
    # его сразу нужно в заказанном формате, а не пережимать потом.
    audio_format = (job.profile.audio_format if job.profile.target == TARGET_AUDIO
                    else AUDIO_WAV16)
    target = _destination(job, ctx)

    ctx.event(Kind.INFO, Stage.PREPARE, Code.FILTERS_APPLIED,
              filters=filters, loudnorm=job.profile.loudnorm, denoise=job.profile.denoise,
              trim_silence=job.profile.trim_silence, track=job.profile.track,
              format=audio_format)
    step = max(job.profile.progress_step_min, 1.0) * 60
    last = {"at": -step}
    started = time.monotonic()

    def on_progress(current: float, total: float) -> None:
        if current - last["at"] < step:
            return
        last["at"] = current
        done = current / total if total else 0.0
        elapsed = time.monotonic() - started
        eta = elapsed / done * (1 - done) if done > 0.02 else 0.0
        ctx.event(Kind.PROGRESS, Stage.PREPARE, done=done, position=current,
                  total=total, eta=round(eta, 1))

    extract_audio(
        ctx.tools.ffmpeg, job.source, target,
        track=job.profile.track,
        loudnorm=job.profile.loudnorm,
        denoise=job.profile.denoise,
        trim_silence=job.profile.trim_silence,
        duration=duration,
        audio_format=audio_format,
        on_progress=on_progress,
        should_cancel=ctx.should_cancel,
    )

    # Промежуточный файл уборка потом уберёт, результат — не тронет.
    job.artifacts["audio" if job.profile.target == TARGET_AUDIO else "temp_wav"] = target
    ctx.event(Kind.INFO, Stage.PREPARE, Code.AUDIO_READY,
              path=str(target), size=target.stat().st_size,
              seconds=round(time.monotonic() - started, 1))
    return target


def _destination(job: Job, ctx: RunContext) -> Path:
    """Куда класть звук.

    Для распознавания это промежуточный файл во временной папке: уборка
    его удалит, и правильно сделает. Но когда человек просил именно звук
    (FR-8), этот файл и есть результат — он ложится рядом с документами и
    уборку переживает. Раньше разницы не было, и сценарий «только звук»
    заканчивался словами «готово» над пустой папкой.
    """
    if job.profile.target != TARGET_AUDIO:
        # Метка пути в имени: одноимённые записи из разных папок — и два
        # экземпляра программы разом — не должны писать в один файл.
        return ctx.paths.temp / f"{job.stem}-{job.fingerprint}_16k.wav"

    job.output_dir.mkdir(parents=True, exist_ok=True)
    return job.beside(encoding(job.profile.audio_format).suffix)
