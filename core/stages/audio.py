"""Стадия «сохраняю звуковой файл»: результат для тех, кому нужен звук.

Сценарий FR-8 — «нужно только аудио» — и FR-37, когда просят и документ,
и звук. Разница в том, откуда брать файл: если распознавания не будет,
подготовка сразу писала в нужном формате и в нужную папку, и здесь
остаётся объявить результат. Если текст тоже нужен, то подготовка делала
16 кГц моно для движка, а человеку нужен его формат — и тогда звук
извлекается вторым проходом из исходника, а не из уже ужатого WAV.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from core.context import RunContext
from core.events import Code, Kind, Stage
from core.job import Job
from core.media import encoding, extract_audio
from core.profile import AUDIO_WAV16, TARGET_AUDIO
from core.progress import Pace


def run(job: Job, ctx: RunContext) -> None:
    how = encoding(job.profile.audio_format)
    target = job.beside(how.suffix)
    target.parent.mkdir(parents=True, exist_ok=True)

    if job.profile.target == TARGET_AUDIO:
        made = job.artifacts.get("audio")
        if made is None or not made.exists():
            made = _extract(job, ctx, target)
    elif job.profile.audio_format == AUDIO_WAV16 and _prepared(job):
        # Движку нужен ровно такой же файл — второй раз его считать незачем.
        # Копия, а не перенос: распознавание ещё не началось.
        shutil.copy2(job.artifacts["temp_wav"], target)
        made = target
    else:
        made = _extract(job, ctx, target)

    job.artifacts["audio"] = made
    ctx.event(Kind.INFO, Stage.AUDIO, Code.AUDIO_SAVED, path=str(made),
              size=made.stat().st_size, format=job.profile.audio_format)


def _prepared(job: Job) -> bool:
    temp = job.artifacts.get("temp_wav")
    return bool(temp and temp.exists())


def _extract(job: Job, ctx: RunContext, target: Path) -> Path:
    """Второй проход ffmpeg: звук в том виде, в каком его просили."""
    profile = job.profile
    duration = job.media.duration if job.media else 0.0
    pace = Pace(step=max(profile.progress_step_min, 0.1) * 60)

    def on_progress(current: float, total: float) -> None:
        if not pace.due(current):
            return
        done = current / total if total else 0.0
        ctx.event(Kind.PROGRESS, Stage.AUDIO, done=done, position=current,
                  total=total, eta=round(pace.eta(done), 1))

    return extract_audio(
        ctx.tools.ffmpeg, job.source, target,
        track=profile.track,
        loudnorm=profile.loudnorm,
        denoise=profile.denoise,
        trim_silence=profile.trim_silence,
        duration=duration,
        audio_format=profile.audio_format,
        on_progress=on_progress,
        should_cancel=ctx.should_cancel,
    )
