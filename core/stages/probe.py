"""Стадия 1: что за файл, какие в нём дорожки."""
from __future__ import annotations

from core.context import RunContext
from core.events import Code, CoreError, Kind, Stage
from core.job import Job
from core.media import describe_tracks, probe


def run(job: Job, ctx: RunContext) -> None:
    info = probe(ctx.tools.ffprobe, job.source)
    job.media = info

    ctx.event(Kind.INFO, Stage.PROBE, Code.SOURCE_INFO,
              name=job.source.name, duration=info.duration, has_video=info.has_video,
              size=job.source.stat().st_size, container=info.container)

    if not info.audio:
        raise CoreError(Code.NO_AUDIO_TRACK, name=job.source.name)

    ctx.event(Kind.INFO, Stage.PROBE, Code.TRACKS_FOUND, tracks=describe_tracks(info.audio))

    if job.profile.track >= len(info.audio):
        ctx.event(Kind.WARNING, Stage.PROBE, Code.TRACK_FALLBACK,
                  asked=job.profile.track, used=0, available=len(info.audio))
        job.profile.track = 0
