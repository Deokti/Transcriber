"""Командная строка поверх ядра.

  python -m cli lecture.mkv
  python -m cli "D:\\Video\\*.mkv" --lang ru --denoise
  python -m cli D:\\Lectures --audio-only --keep-audio

Ядро одно и то же и для окна, и отсюда: здесь только разбор аргументов
и превращение событий в слова.
"""
from __future__ import annotations

import argparse
import glob
import signal
import sys
import time
from pathlib import Path

from cli import messages
from core import platform
from core.asr.faster_whisper_backend import FasterWhisperBackend
from core.events import Code, CoreError, Event, Kind
from core.job import Job, JobState
from core.media import MEDIA_EXT, ensure_tools
from core.runner import JobRunner
from core.settings import Settings
from core.profile import (LAYOUT_PLAIN, LAYOUT_TIMECODES, TARGET_AUDIO, TARGET_TEXT,
                          TEMP_DELETE, TEMP_KEEP, TEMP_MOVE, Profile)
from core.timecode import hms

_runner: "JobRunner | None" = None
_presses = 0


def _on_sigint(_signum, _frame) -> None:
    """Три уровня, те же, что в окне: доработать файл, прервать, выйти."""
    global _presses
    _presses += 1
    if _runner is None or _presses >= 3:
        sys.exit(130)
    if _presses == 1:
        _runner.stop_after_current()
        print("\n[!] доработаю текущий файл и остановлюсь.\n"
              "    ещё раз Ctrl+C — прервать сейчас, посчитанное сохранится")
    else:
        _runner.cancel_all()
        print("\n[!] прерываю. Досохраняю посчитанное, ещё раз Ctrl+C — выйти немедленно")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="transcriber",
        description="Видео или аудио -> текст с тайм-кодами (ffmpeg + faster-whisper)")
    p.add_argument("inputs", nargs="*", help="файлы, папки или маски")
    p.add_argument("-o", "--outdir", help="куда класть результат (по умолчанию рядом с исходником)")
    p.add_argument("-l", "--lang", help="язык записи: ru, en, ... (по умолчанию ru)")
    p.add_argument("-m", "--model", help="tiny | base | small | medium | large-v3 | ...")
    p.add_argument("--device", choices=["cuda", "cpu"])
    p.add_argument("--compute", help="float16 | int8_float16 | int8")
    p.add_argument("--beam", type=int)
    p.add_argument("--initial-prompt", help="подсказка модели: термины, имена, пунктуация")
    p.add_argument("--no-vad", action="store_true", help="не отрезать тишину")
    p.add_argument("--cpt", action="store_true",
                   help="включить condition_on_previous_text (по умолчанию выключен: залипания)")
    p.add_argument("--denoise", action="store_true", help="шумоподавление")
    p.add_argument("--no-loudnorm", action="store_true", help="не выравнивать громкость")
    p.add_argument("--track", type=int, help="номер аудиодорожки")
    p.add_argument("--raw", action="store_true", help="без ffmpeg: отдать исходник как есть")
    p.add_argument("--audio-only", action="store_true", help="только вытащить звук, не распознавать")
    p.add_argument("--layout", choices=[LAYOUT_TIMECODES, LAYOUT_PLAIN])
    p.add_argument("--keep-audio", action="store_true")
    p.add_argument("--delete-audio", action="store_true")
    p.add_argument("--move-audio", action="store_true", help="перенести WAV к исходнику")
    p.add_argument("--force", action="store_true", help="перезаписывать готовое")
    p.add_argument("--report", type=float, help="шаг отчёта о прогрессе, минут аудио")
    p.add_argument("--profile", help="взять настройки из файла")
    p.add_argument("--save-profile", help="сохранить получившиеся настройки в файл")
    p.add_argument("--models-dir", help="где держать модели (по умолчанию — папка данных)")
    p.add_argument("--ffmpeg-dir", help="где искать ffmpeg")
    p.add_argument("--save-settings", action="store_true",
                   help="запомнить --models-dir и --ffmpeg-dir для следующих запусков")
    return p.parse_args(argv)


def build_profile(args: argparse.Namespace) -> Profile:
    profile = Profile.load(Path(args.profile)) if args.profile else Profile.defaults()

    if args.lang:
        profile.language = args.lang
    if args.model:
        profile.model = args.model
    if args.device:
        profile.device = args.device
        profile.compute = args.compute or platform.default_compute(args.device)
    if args.compute:
        profile.compute = args.compute
    if args.beam:
        profile.beam = args.beam
    if args.initial_prompt:
        profile.initial_prompt = args.initial_prompt
    if args.no_vad:
        profile.vad = False
    if args.cpt:
        profile.condition_on_previous_text = True
    if args.denoise:
        profile.denoise = True
    if args.no_loudnorm:
        profile.loudnorm = False
    if args.track is not None:
        profile.track = args.track
    if args.raw:
        profile.skip_prepare = True
    if args.audio_only:
        profile.target = TARGET_AUDIO
    if args.layout:
        profile.layout = args.layout
    if args.outdir:
        profile.output_dir = args.outdir
    if args.force:
        profile.force = True
    if args.report:
        profile.progress_step_min = args.report
    if args.keep_audio:
        profile.temp_action = TEMP_KEEP
    if args.move_audio:
        profile.temp_action = TEMP_MOVE
    if args.delete_audio:
        profile.temp_action = TEMP_DELETE
    return profile


def expand(inputs: list[str]) -> list[Path]:
    """Раскрывает маски и папки: PowerShell маски сам не раскрывает."""
    found: list[Path] = []
    for item in inputs:
        path = Path(item).expanduser()
        if path.is_dir():
            found += [p for p in sorted(path.iterdir())
                      if p.is_file() and p.suffix.lower() in MEDIA_EXT]
        elif any(ch in item for ch in "*?["):
            found += [Path(p) for p in sorted(glob.glob(item))
                      if Path(p).is_file() and Path(p).suffix.lower() in MEDIA_EXT]
        elif path.is_file():
            found.append(path)
        else:
            print(f"[!] не найдено: {item}")

    unique: list[Path] = []
    seen: set[str] = set()
    for p in found:
        key = str(p.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(p.resolve())
    return unique


def resolve_device(profile: Profile, say) -> None:
    """Просит то, что есть: недоступная видеокарта — не повод падать (FR-11)."""
    if profile.device != "cuda":
        return
    for device in platform.devices():
        if device.id == "cuda" and not device.available:
            say(Event(Kind.WARNING, None, Code.DEVICE_FALLBACK, data={"reason": device.reason}))
            profile.device = "cpu"
            profile.compute = platform.default_compute("cpu")
            return


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        # Windows отдаёт консоли кодировку системы, и русский текст рассыпается.
        # Особенно когда вывод перенаправлен в файл или в другую оболочку.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args(argv)
    signal.signal(signal.SIGINT, _on_sigint)

    paths = platform.paths().ensure()
    logfile = (paths.logs / (time.strftime("%Y-%m-%d_%H%M%S") + ".log")).open(
        "w", encoding="utf-8", buffering=1)

    def say(event: Event) -> None:
        line = messages.render(event)
        if line is None:
            return
        stamped = f"[{time.strftime('%H:%M:%S')}] {line}"
        print(stamped, flush=True)
        logfile.write(stamped + "\n")

    settings = Settings.load()
    if args.models_dir:
        settings.models_dir = args.models_dir
    if args.ffmpeg_dir:
        settings.ffmpeg_dir = args.ffmpeg_dir
    if args.save_settings:
        print(f"[i] настройки сохранены: {settings.save()}")

    files = expand(args.inputs)
    if not files:
        print("Нечего обрабатывать: укажите файл, папку или маску.")
        return 2

    profile = build_profile(args)
    resolve_device(profile, say)
    if args.save_profile:
        profile.save(Path(args.save_profile))

    try:
        tools = ensure_tools(settings.extra_tool_dirs())
    except CoreError as e:
        say(Event(Kind.FAILED, None, e.code, data=e.data))
        return 1
    models_dir = settings.resolve_models_dir()
    print(f"[i] ffmpeg: {tools.ffmpeg}")
    print(f"[i] данные: {paths.root}")
    print(f"[i] модели: {models_dir}")

    global _runner
    backend = FasterWhisperBackend(models_dir)
    _runner = JobRunner(paths=paths, tools=tools, backend=backend, emit=say)
    _runner.add(*(Job(source=path, profile=profile) for path in files))

    started = time.monotonic()
    _runner.start()
    while _runner.busy:
        # Ждём короткими отрезками: сплошной join на Windows глушит Ctrl+C
        _runner.join(0.2)

    _summary(_runner.finished, time.monotonic() - started)
    logfile.close()
    return 1 if any(j.state is JobState.FAILED for j in _runner.finished) else 0


def _summary(jobs: list[Job], seconds: float) -> None:
    if not jobs:
        return
    print("=" * 72)
    for job in jobs:
        stats = job.stats
        if job.state is JobState.DONE and stats.get("segments"):
            verdict = messages.VERDICTS.get(stats.get("verdict"), "?")
            print(f"{job.source.name[:36]:<36} {hms(stats.get('audio', 0)):>9} "
                  f"{stats.get('seconds', 0)/60:>6.1f}м {stats.get('segments', 0):>6} сегм.  {verdict}")
        else:
            note = {JobState.FAILED: job.error_code, JobState.CANCELLED: "прервано"}.get(
                job.state, "пропущено" if stats.get("skipped") else job.state.value)
            print(f"{job.source.name[:36]:<36} {note}")
    print(f"Всего: {len(jobs)} файл(ов) за {seconds/60:.1f} мин")


if __name__ == "__main__":
    sys.exit(main())
