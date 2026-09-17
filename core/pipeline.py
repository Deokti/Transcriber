"""Конвейер: какие стадии и в каком порядке проходит задача.

Сценарии из требований получаются не развилками внутри кода, а разным
набором включённых стадий — см. раздел 4 в architecture.md.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from core.context import RunContext
from core.events import Cancelled, Code, CoreError, Event, Kind, Stage
from core.formats import segments as segments_file
from core.job import Job, JobState
from core.media import encoding
from core.profile import TARGET_AUDIO, TARGET_BOTH, TARGET_TEXT
from core.stages import audio, check, cleanup, export, prepare, probe, transcribe


def plan(profile) -> list[Stage]:
    """Список стадий для этой задачи — им же рисуется ход работы в окне.

    Набор собирается из заказа, а не из развилок внутри кода: нужен звук —
    добавляется стадия сохранения, нужен текст — распознавание с проверкой
    и выдачей. Уборка идёт только там, где остаётся что убирать: звуковой
    файл — результат, а не промежуточный.
    """
    wants_audio = profile.target in (TARGET_AUDIO, TARGET_BOTH)
    wants_text = profile.target in (TARGET_TEXT, TARGET_BOTH)

    stages = [Stage.PROBE]
    if not profile.skip_prepare:
        stages.append(Stage.PREPARE)
    if wants_audio:
        stages.append(Stage.AUDIO)
    if wants_text:
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
        _claim_name(job, ctx)
        if _already_done(job, ctx):
            job.state = JobState.DONE
            job.stats["skipped"] = True
            # Пропуск — тоже итог, и о нём нужно рассказать тем же событием,
            # что и об обычном конце работы. Иначе экран результата пуст:
            # ни файла, ни готового документа — как будто ничего не было.
            ctx.emit(Event(Kind.JOB_DONE, None, None,
                           {"name": job.source.name,
                            "artifacts": {k: str(v) for k, v in job.artifacts.items()},
                            **job.stats}))
            return job

        total = len(stages)
        # Имя нарочно не «audio»: так зовётся стадия сохранения звука, и
        # переменная её перекрывала — конвейер падал на ровном месте.
        prepared = job.source

        for number, stage in enumerate(stages, 1):
            if stage is Stage.PROBE:
                with _stage(ctx, stage, number, total):
                    probe.run(job, ctx)
            elif stage is Stage.PREPARE:
                with _stage(ctx, stage, number, total):
                    prepared = prepare.run(job, ctx)
            elif stage is Stage.AUDIO:
                with _stage(ctx, stage, number, total):
                    audio.run(job, ctx)
            elif stage is Stage.TRANSCRIBE:
                with _stage(ctx, stage, number, total):
                    transcribe.run(job, ctx, prepared)
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
        _save_partial(job, ctx)
        return job
    except CoreError as e:
        job.state = JobState.FAILED
        job.error_code = e.code
        job.error_data = e.data
        # data отдаём словарём: в нём может оказаться поле с именем
        # аргумента события, и тогда вызов развалится
        ctx.emit(Event(Kind.FAILED, None, e.code, {"name": job.source.name, **e.data}))
        _cleanup_failed(job, ctx)
        return job
    except Exception as e:  # чужая ошибка не должна уронить очередь
        job.state = JobState.FAILED
        job.error_code = Code.UNEXPECTED
        job.error_data = {"reason": repr(e)}
        ctx.emit(Event(Kind.FAILED, None, Code.UNEXPECTED,
                       {"name": job.source.name, "reason": repr(e)}))
        _cleanup_failed(job, ctx)
        return job

    job.state = JobState.DONE
    ctx.emit(Event(Kind.JOB_DONE, None, None,
                   {"name": job.source.name,
                    "artifacts": {k: str(v) for k, v in job.artifacts.items()},
                    **job.stats}))
    return job


def _cleanup_failed(job: Job, ctx: RunContext) -> None:
    """Убирает временный WAV и при ошибке, соблюдая выбранную политику."""
    try:
        cleanup.run(job, ctx.without_cancel())
    except Exception:
        pass   # ошибка уборки не должна заслонять исходную ошибку


def _save_partial(job: Job, ctx: RunContext) -> None:
    """Досохраняет то, что успели посчитать до отмены.

    Отменить — не значит выбросить. Сегменты уже на диске, документ из них
    собирается за секунду, а восемьдесят минут счёта второй раз никто не ждёт
    (решение D-7).
    """
    safe = ctx.without_cancel()   # доделываем до конца, второй отмены не слушаем
    if job.segments:
        job.stats["partial"] = True
        # Пометка в самом файле сегментов, а не только в событии: следующий
        # запуск должен понять, что рядом лежит обрывок, а не готовый текст,
        # — иначе он его пропустит как «уже посчитанное».
        segments_file.mark_partial(job.output(segments_file.SUFFIX))
        total = job.media.duration if job.media else 0.0
        try:
            check.run(job, safe)
            export.run(job, safe)
            safe.event(Kind.INFO, None, Code.PARTIAL_SAVED,
                       segments=len(job.segments),
                       position=job.segments[-1].end, total=total,
                       # Что именно спасли: без этого окно знает, что «часть
                       # сохранена», но не знает, где она лежит.
                       artifacts={k: str(v) for k, v in job.artifacts.items()})
        except Exception as e:
            safe.event(Kind.WARNING, None, Code.UNEXPECTED, reason=repr(e))
    _cleanup_failed(job, safe)


def _claim_name(job: Job, ctx: RunContext) -> None:
    """Даёт результату имя, которое не занято чужим файлом.

    Рядом с исходником одно имя — один файл, спорить не с кем. Но в общей
    папке результата два «Урок 1.mp4» из разных курсов делили бы один
    документ: второй молча пропускался бы как готовый или затирал первый.
    Чей файл — записано в заголовке сегментов; чужой — берём имя с папкой.
    """
    if not job.profile.output_dir:
        return
    for attempt in range(1, 100):
        owner = segments_file.meta(job.output(segments_file.SUFFIX)).get("source_path")
        if owner is None or owner == str(job.source):
            break
        folder = job.source.parent.name or "2"
        job.alias = (f"{job.source.stem} ({folder})" if attempt == 1
                     else f"{job.source.stem} ({folder} {attempt})")
    if job.alias:
        ctx.event(Kind.INFO, None, Code.OUTPUT_RENAMED,
                  name=job.source.name, stem=job.stem)


def _already_done(job: Job, ctx: RunContext) -> bool:
    """Готовое не пересчитываем: 80 минут счёта стоят проверки одной строкой."""
    if job.profile.force or job.profile.target == TARGET_AUDIO:
        return False
    existing = [f for f in job.profile.formats if job.output(f".{f}").exists()]
    if not existing or len(existing) != len(job.profile.formats):
        return False

    audio_path = None
    if job.profile.target == TARGET_BOTH:
        audio_path = job.beside(encoding(job.profile.audio_format).suffix)
        if not audio_path.is_file() or audio_path.stat().st_size == 0:
            return False

    # Документ есть, но посчитан другой моделью — значит лежит не то, что
    # просят сейчас. Модель меняют как раз затем, чтобы получить другой
    # текст, и «пропущено» в ответ выглядит издевательством.
    head = segments_file.meta(job.output(segments_file.SUFFIX))
    if head.get("model") and head["model"] != job.profile.model:
        return False
    # Обрывок после отмены — не результат, а то, что спасли по пути.
    # Человек запускает снова именно затем, чтобы досчитать.
    if head.get("partial"):
        return False

    # Готовое — тоже результат: окну нужно, что именно лежит и где.
    for name in existing:
        job.artifacts[name] = job.output(f".{name}")
    if audio_path is not None:
        job.artifacts["audio"] = audio_path
    ctx.event(Kind.WARNING, None, Code.OUTPUT_EXISTS,
              name=job.source.name, formats=existing,
              segments=str(job.output(segments_file.SUFFIX)))
    return True
