"""Конвейер: какие стадии и в каком порядке проходит задача.

Сценарии из требований получаются не развилками внутри кода, а разным
набором включённых стадий — см. раздел 4 в architecture.md.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from core.context import RunContext
from core.events import Cancelled, Code, CoreError, Kind, Stage
from core.export import segments as segments_file
from core.job import Job, JobState
from core.profile import TARGET_AUDIO
from core.stages import check, cleanup, export, prepare, probe, transcribe


def plan(profile) -> list[Stage]:
    """Список стадий для этой задачи — им же рисуется ход работы в окне."""
    if profile.target == TARGET_AUDIO:
        return [Stage.PROBE, Stage.PREPARE, Stage.CLEANUP]
    stages = [Stage.PROBE]
    if not profile.skip_prepare:
        stages.append(Stage.PREPARE)
    stages += [Stage.TRANSCRIBE, Stage.CHECK, Stage.EXPORT, Stage.CLEANUP]
    return stages


@contextmanager
def _stage(ctx: RunContext, stage: Stage, index: int, total: int) -> Iterator[None]:
    ctx.check_cancel()
    ctx.event(Kind.STAGE_STARTED, stage, number=index, of=total)
    started = time.monotonic()
    yield
    ctx.event(Kind.STAGE_DONE, stage, number=index, of=total,
              seconds=round(time.monotonic() - started, 1))


def run_job(job: Job, ctx: RunContext) -> Job:
    """Проводит задачу по конвейеру. Исключения наружу не выпускает.

    Ошибка одного файла не должна ронять очередь, поэтому здесь она
    превращается в событие и в состояние задачи.
    """
    stages = plan(job.profile)
    job.state = JobState.RUNNING
    ctx.event(Kind.JOB_STARTED, None, name=job.source.name,
              stages=[s.value for s in stages], target=job.profile.target)

    try:
        if _already_done(job, ctx):
            job.state = JobState.DONE
            job.stats["skipped"] = True
            return job

        total = len(stages)
        audio = job.source

        for number, stage in enumerate(stages, 1):
            if stage is Stage.PROBE:
                with _stage(ctx, stage, number, total):
                    probe.run(job, ctx)
            elif stage is Stage.PREPARE:
                with _stage(ctx, stage, number, total):
                    audio = prepare.run(job, ctx)
            elif stage is Stage.TRANSCRIBE:
                with _stage(ctx, stage, number, total):
                    transcribe.run(job, ctx, audio)
            elif stage is Stage.CHECK:
                with _stage(ctx, stage, number, total):
                    check.run(job, ctx)
            elif stage is Stage.EXPORT:
                with _stage(ctx, stage, number, total):
                    export.run(job, ctx)
            elif stage is Stage.CLEANUP:
                with _stage(ctx, stage, number, total):
                    cleanup.run(job, ctx)

    except Cancelled:
        job.state = JobState.CANCELLED
        job.error_code = Code.CANCELLED
        ctx.event(Kind.FAILED, None, Code.CANCELLED, name=job.source.name)
        return job
    except CoreError as e:
        job.state = JobState.FAILED
        job.error_code = e.code
        job.error_data = e.data
        ctx.event(Kind.FAILED, None, e.code, name=job.source.name, **e.data)
        return job
    except Exception as e:  # чужая ошибка не должна уронить очередь
        job.state = JobState.FAILED
        job.error_code = Code.UNEXPECTED
        job.error_data = {"reason": repr(e)}
        ctx.event(Kind.FAILED, None, Code.UNEXPECTED, name=job.source.name, reason=repr(e))
        return job

    job.state = JobState.DONE
    ctx.event(Kind.JOB_DONE, None, name=job.source.name,
              artifacts={k: str(v) for k, v in job.artifacts.items()}, **job.stats)
    return job


def _already_done(job: Job, ctx: RunContext) -> bool:
    """Готовое не пересчитываем: 80 минут счёта стоят проверки одной строкой."""
    if job.profile.force or job.profile.target == TARGET_AUDIO:
        return False
    existing = [f for f in job.profile.formats if job.output(f".{f}").exists()]
    if not existing:
        return False
    ctx.event(Kind.WARNING, None, Code.OUTPUT_EXISTS,
              name=job.source.name, formats=existing,
              segments=str(job.output(segments_file.SUFFIX)))
    return True
