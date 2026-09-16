"""Стадия 5: документы собираются из сегментов.

Каждый формат — чистая функция от сегментов. Поэтому переэкспорт в другой
вид стоит секунду, а не 80 минут повторного счёта (принцип П-3).
"""
from __future__ import annotations

from core.context import RunContext
from core.events import Code, Kind, Stage
from core.export import SUPPORTED
from core.export import text as text_export
from core.job import Job
from core.profile import LAYOUT_PLAIN


def run(job: Job, ctx: RunContext) -> None:
    header = _header(job)
    for fmt in job.profile.formats:
        ctx.check_cancel()
        if fmt not in SUPPORTED:
            continue
        path = job.output(f".{fmt}")
        if job.profile.layout == LAYOUT_PLAIN:
            text_export.write_plain(path, job.segments, header)
        else:
            text_export.write_timecoded(path, job.segments, header)
        job.artifacts[fmt] = path
        ctx.event(Kind.INFO, Stage.EXPORT, Code.EXPORT_DONE,
                  format=fmt, path=str(path), size=path.stat().st_size)


def _header(job: Job) -> str:
    """Строка происхождения в начале файла: чем и как это было сделано."""
    p = job.profile
    parts = [job.source.name, p.model,
             f"lang={job.stats.get('language', p.language)}",
             f"vad={p.vad}",
             f"condition_on_previous_text={p.condition_on_previous_text}"]
    if job.stats.get("partial"):
        # Пометка машинная, не фраза: словами её назовёт интерфейс (принцип П-1)
        parts.append("partial=true")
    return " | ".join(parts)
