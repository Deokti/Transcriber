"""Стадия 6: уборка. Видимая, а не молчаливая (требование FR-30)."""
from __future__ import annotations

import shutil

from core.context import RunContext
from core.events import Code, Kind, Stage
from core.formats import WRITERS
from core.formats import segments as segments_file
from core.job import Job, JobState
from core.profile import TEMP_DELETE, TEMP_MOVE


def run(job: Job, ctx: RunContext) -> None:
    # Сегменты — только после удачной работы: при ошибке и отмене (сюда
    # заходят и оттуда) они последнее, что осталось от счёта.
    if job.state is JobState.RUNNING:
        retire_segments(job, ctx)

    temp = job.artifacts.get("temp_wav")
    if not temp or not temp.exists():
        return

    action = job.profile.temp_action
    size = temp.stat().st_size

    if action == TEMP_DELETE:
        try:
            temp.unlink()
            job.artifacts.pop("temp_wav", None)
            ctx.event(Kind.INFO, Stage.CLEANUP, Code.TEMP_DELETED, size=size)
        except OSError as e:
            ctx.event(Kind.WARNING, Stage.CLEANUP, Code.TEMP_KEPT,
                      path=str(temp), reason=repr(e))
        return

    if action == TEMP_MOVE:
        target = job.source.parent / temp.name
        if target.exists():
            ctx.event(Kind.WARNING, Stage.CLEANUP, Code.TEMP_MOVE_FAILED,
                      path=str(target), reason="exists")
            return
        try:
            shutil.move(str(temp), str(target))
            job.artifacts["temp_wav"] = target
            ctx.event(Kind.INFO, Stage.CLEANUP, Code.TEMP_MOVED, path=str(target), size=size)
        except OSError as e:
            ctx.event(Kind.WARNING, Stage.CLEANUP, Code.TEMP_MOVE_FAILED,
                      path=str(target), reason=repr(e))
        return

    ctx.event(Kind.INFO, Stage.CLEANUP, Code.TEMP_KEPT, path=str(temp), size=size)


def retire_segments(job: Job, ctx: RunContext) -> None:
    """Убирает файл сегментов, если его не просили оставить (решение D-17)."""
    path = job.artifacts.get("segments")
    if job.profile.keep_segments or not path:
        return
    documents = [job.artifacts[name] for name in WRITERS if name in job.artifacts]
    try:
        freed = segments_file.retire(path, documents)
    except OSError as e:
        ctx.event(Kind.WARNING, Stage.CLEANUP, Code.TEMP_MOVE_FAILED,
                  path=str(path), reason=repr(e))
        return
    if freed:
        job.artifacts.pop("segments", None)
        ctx.event(Kind.INFO, Stage.CLEANUP, Code.SEGMENTS_DELETED, size=freed)
