"""Стадия 2: ffmpeg вытаскивает и чистит звук."""
from __future__ import annotations

import time
from pathlib import Path

from core.context import RunContext
from core.events import Code, Kind, Stage
from core.job import Job
from core.media import build_filters, extract_audio


def run(job: Job, ctx: RunContext) -> Path:
    """Возвращает путь к звуку, который пойдёт в распознавание."""
    if job.profile.skip_prepare:
        return job.source

    duration = job.media.duration if job.media else 0.0
    filters = build_filters(job.profile.loudnorm, job.profile.denoise)
    ctx.event(Kind.INFO, Stage.PREPARE, Code.FILTERS_APPLIED,
              filters=filters, loudnorm=job.profile.loudnorm, denoise=job.profile.denoise,
              track=job.profile.track)

    target = ctx.paths.temp / f"{job.stem}_16k.wav"
    step = max(job.profile.progress_step_min, 1.0) * 60
    last = {"at": -step}
    started = time.monotonic()

    def on_progress(current: float, total: float) -> None:
        if current - last["at"] < step:
            return
        last["at"] = current
        ctx.event(Kind.PROGRESS, Stage.PREPARE,
                  done=current / total if total else 0.0, position=current, total=total)

    extract_audio(
        ctx.tools.ffmpeg, job.source, target,
        track=job.profile.track,
        loudnorm=job.profile.loudnorm,
        denoise=job.profile.denoise,
        start=job.profile.start,
        end=job.profile.end,
        duration=duration,
        on_progress=on_progress,
        should_cancel=ctx.should_cancel,
    )

    job.artifacts["temp_wav"] = target
    ctx.event(Kind.INFO, Stage.PREPARE, Code.AUDIO_READY,
              path=str(target), size=target.stat().st_size,
              seconds=round(time.monotonic() - started, 1))
    return target
