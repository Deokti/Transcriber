"""Стадия 5: документы собираются из сегментов.

Каждый формат — чистая функция от сегментов. Поэтому переэкспорт в другой
вид стоит секунду, а не 80 минут повторного счёта (принцип П-3).
"""
from __future__ import annotations

from core import formats
from core.context import RunContext
from core.events import Code, Kind, Stage
from core.job import Job


def run(job: Job, ctx: RunContext) -> None:
    meta = _meta(job)
    for fmt in job.profile.formats:
        ctx.check_cancel()
        if fmt not in formats.SUPPORTED:
            continue
        path = formats.write(fmt, job.output(f".{fmt}"), job.segments,
                             layout=job.profile.layout, title=job.source.name, meta=meta)
        job.artifacts[fmt] = path
        ctx.event(Kind.INFO, Stage.EXPORT, Code.EXPORT_DONE,
                  format=fmt, path=str(path), size=path.stat().st_size)


def _meta(job: Job) -> str:
    """Строка происхождения под заголовком: чем и как это было сделано.

    Машинная, а не фраза: словами её назовёт тот, кто читает (принцип П-1).
    """
    p = job.profile
    parts = [p.model,
             f"lang={job.stats.get('language', p.language)}",
             f"vad={p.vad}",
             f"condition_on_previous_text={p.condition_on_previous_text}"]
    if job.stats.get("partial"):
        parts.append("partial=true")
    return " | ".join(parts)
