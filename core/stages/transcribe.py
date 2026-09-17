"""Стадия 3: распознавание. Сегменты пишутся на диск по мере появления."""
from __future__ import annotations

import time
from pathlib import Path

from core.context import RunContext
from core.env import models
from core.events import Code, CoreError, Kind, Stage
from core.formats import segments as segments_file
from core.job import Job


def _fetch(ctx: RunContext, profile) -> None:
    """Приносит модель на диск, отчитываясь о ходе дела."""
    entry = models.get(profile.model)
    ctx.event(Kind.WARNING, Stage.DOWNLOAD, Code.MODEL_MISSING,
              model=profile.model, size_mb=entry.size_mb if entry else 0)
    ctx.event(Kind.STAGE_STARTED, Stage.DOWNLOAD, number=0, of=0)

    started = time.monotonic()
    last = {"at": 0.0}

    def on_progress(done: int, total: int) -> None:
        now = time.monotonic()
        if now - last["at"] < 0.5:      # чаще двух раз в секунду окну не нужно
            return
        last["at"] = now
        share = (done / total) if total else 0.0
        elapsed = now - started
        eta = elapsed / share * (1 - share) if share > 0.02 else 0.0
        ctx.event(Kind.PROGRESS, Stage.DOWNLOAD, done=min(share, 1.0),
                  bytes=done, total=total, eta=round(eta, 1))

    ctx.backend.download(profile.model, on_progress=on_progress,
                         should_cancel=ctx.should_cancel)

    spent = round(time.monotonic() - started, 1)
    ctx.event(Kind.INFO, Stage.DOWNLOAD, Code.DOWNLOAD_DONE,
              model=profile.model, seconds=spent)
    ctx.event(Kind.STAGE_DONE, Stage.DOWNLOAD, number=0, of=0, seconds=spent)


def run(job: Job, ctx: RunContext, audio: Path) -> None:
    profile = job.profile

    # Английская модель под русскую запись выдаст правдоподобную
    # бессмыслицу, и человек не поймёт, почему. Лучше не начинать.
    if not models.supports(profile.model, profile.language):
        info = models.get(profile.model)
        raise CoreError(Code.MODEL_LANGUAGE_MISMATCH, model=profile.model,
                        language=profile.language,
                        model_languages=info.languages if info else None,
                        alternatives=[m.id for m in sorted(
                            models.for_language(profile.language),
                            key=lambda m: -m.quality)])

    # Скачивание модели — это гигабайты и минуты ожидания. Поэтому оно
    # становится отдельным видимым шагом со своим процентом, а не паузой
    # внутри распознавания.
    if not ctx.backend.downloaded(profile.model):
        _fetch(ctx, profile)

    ctx.event(Kind.INFO, Stage.TRANSCRIBE, Code.MODEL_LOADING,
              model=profile.model, device=profile.device, compute=profile.compute)
    spent = ctx.backend.load(profile.model, profile.device, profile.compute,
                             profile.cpu_threads)
    ctx.event(Kind.INFO, Stage.TRANSCRIBE, Code.MODEL_READY,
              model=profile.model, seconds=round(spent, 1), cached=spent == 0.0)

    ctx.check_cancel()
    started = time.monotonic()
    info, stream = ctx.backend.transcribe(audio, profile)
    ctx.event(Kind.INFO, Stage.TRANSCRIBE, Code.LANGUAGE_DETECTED,
              language=info.language, probability=round(info.language_probability, 2),
              duration=info.duration)

    out = job.output(segments_file.SUFFIX)
    meta = {
        "source": job.source.name,
        "source_path": str(job.source),
        "language": info.language,
        "duration": info.duration,
        "model": profile.model,
        "device": profile.device,
        "compute": profile.compute,
        "vad": profile.vad,
        "condition_on_previous_text": profile.condition_on_previous_text,
    }

    step = max(profile.progress_step_min, 0.1) * 60
    reported = 0.0
    total = info.duration or (job.media.duration if job.media else 0.0)
    count = 0

    with segments_file.SegmentWriter(out, meta) as writer:
        for segment in stream:
            ctx.check_cancel()   # между сегментами — безопасное место прерваться
            writer.add(segment)
            job.segments.append(segment)
            count += 1

            if total and segment.end - reported >= step:
                reported = segment.end
                elapsed = time.monotonic() - started
                done = min(segment.end / total, 1.0)
                eta = elapsed / done * (1 - done) if done > 0.01 else 0.0
                ctx.event(Kind.PROGRESS, Stage.TRANSCRIBE,
                          done=done, position=segment.end, total=total,
                          elapsed=round(elapsed, 1), eta=round(eta, 1), segments=count)

    job.artifacts["segments"] = out
    seconds = time.monotonic() - started
    words = sum(len(s.text.split()) for s in job.segments)
    job.stats.update(segments=count, words=words, seconds=seconds, audio=total,
                     language=info.language,
                     speed=(total / seconds) if seconds > 0 else 0.0)
    ctx.event(Kind.INFO, Stage.TRANSCRIBE, Code.TRANSCRIBE_DONE,
              segments=count, words=words, seconds=round(seconds, 1), audio=total,
              speed=round(total / seconds, 1) if seconds > 0 else 0.0, path=str(out))
