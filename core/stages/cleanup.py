"""Стадия 6: уборка. Видимая, а не молчаливая (требование FR-30)."""
from __future__ import annotations

import shutil

from core.context import RunContext
from core.events import Code, Kind, Stage
from core.job import Job
from core.profile import TEMP_DELETE, TEMP_MOVE


def run(job: Job, ctx: RunContext) -> None:
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
