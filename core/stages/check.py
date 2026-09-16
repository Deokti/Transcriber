"""Стадия 4: проверка на залипания — та самая, ради которой всё затевалось."""
from __future__ import annotations

from core import quality
from core.context import RunContext
from core.events import Code, Kind, Stage
from core.job import Job


def run(job: Job, ctx: RunContext) -> None:
    report = quality.analyze(job.segments)
    if report is None:
        return

    job.stats["verdict"] = report.verdict
    kind = Kind.INFO if report.verdict == Code.QUALITY_CLEAN else Kind.WARNING
    ctx.event(kind, Stage.CHECK, report.verdict, **report.as_data())

    if report.gaps:
        ctx.event(Kind.INFO, Stage.CHECK, Code.GAPS_FOUND, count=len(report.gaps))
