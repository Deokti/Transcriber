"""Обрывок после отмены не считается готовым документом.

Ошибка из ревью ядра: отменил длинную работу — программа честно спасла
посчитанное и собрала из него документ (решение D-7). Запустил тот же файл
снова, чтобы досчитать, — а он пропущен: «документ уже был». Пропуск
смотрел только на то, что файл есть, и не отличал половину записи от целой.

Теперь отмена оставляет пометку прямо в файле сегментов, и такой документ
не повод для пропуска. Пометка именно в файле, а не в памяти: между отменой
и повторным запуском программу могли закрыть.

Движок подставной: на первом прогоне отдаёт один сегмент и обрывается, как
при отмене; на втором доходит до конца.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core import platform
from core.asr.base import Segment, TranscriptionInfo
from core.context import RunContext
from core.events import Cancelled
from core.formats import segments as segments_file
from core.job import Job, JobState
from core.media import ensure_tools
from core.pipeline import run_job
from core.profile import TARGET_TEXT, TEMP_DELETE, Profile


class FakeBackend:
    """Первый прогон обрывается после одного сегмента, дальше — до конца."""

    def __init__(self, cancel_after_first: bool) -> None:
        self._cancel = cancel_after_first

    def load(self, *args, **kwargs) -> float:
        return 0.0

    def downloaded(self, model: str) -> bool:
        return True

    def download(self, model: str, **kwargs) -> None:
        raise AssertionError("качать модель в этом тесте не должны")

    def transcribe(self, audio: Path, profile):
        info = TranscriptionInfo(language="ru", language_probability=1.0, duration=2.0)

        def stream():
            yield Segment(start=0.0, end=1.0, text="первая половина")
            if self._cancel:
                raise Cancelled()          # так выглядит «Отменить всё»
            yield Segment(start=1.0, end=2.0, text="вторая половина")

        return info, stream()

    def unload(self) -> None:
        pass


def run_once(tools, folder: Path, source: Path, cancel: bool) -> Job:
    profile = Profile.defaults()
    profile.target = TARGET_TEXT
    profile.temp_action = TEMP_DELETE
    profile.output_dir = str(folder / "готовое")
    profile.loudnorm = False
    job = Job(source=source, profile=profile)
    ctx = RunContext(paths=platform.paths().ensure(), tools=tools,
                     backend=FakeBackend(cancel), emit=lambda event: None)
    run_job(job, ctx)
    return job


def main() -> int:
    tools = ensure_tools([])
    folder = Path(tempfile.mkdtemp(prefix="transcriber-partial-"))
    source = folder / "лекция.mp4"
    subprocess.run([str(tools.ffmpeg), "-y", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=2",
                    "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=2",
                    "-map", "1:v", "-map", "0:a", "-c:v", "libx264",
                    "-preset", "ultrafast", "-shortest", str(source)],
                   capture_output=True)

    first = run_once(tools, folder, source, cancel=True)
    document = Path(first.profile.output_dir) / "лекция.txt"
    head = segments_file.meta(Path(first.profile.output_dir) / "лекция.segments.jsonl")
    print("после отмены: состояние", first.state.value, "| документ есть:", document.exists(),
          "| пометка в сегментах:", head.get("partial"))
    if first.state is not JobState.CANCELLED or not document.exists():
        print("ОШИБКА: отмена должна была спасти посчитанное и собрать документ")
        return 1
    if not head.get("partial"):
        print("ОШИБКА: в файле сегментов нет пометки об обрыве")
        return 1

    second = run_once(tools, folder, source, cancel=False)
    print("повторный запуск: пропущено", bool(second.stats.get("skipped")),
          "| сегментов:", len(second.segments))
    if second.stats.get("skipped"):
        print("ОШИБКА: половину записи приняли за готовый документ")
        return 1
    if second.state is not JobState.DONE or len(second.segments) != 2:
        print("ОШИБКА: повторный запуск не досчитал запись до конца")
        return 1

    head = segments_file.meta(Path(second.profile.output_dir) / "лекция.segments.jsonl")
    print("после досчёта пометка снята:", not head.get("partial"))
    if head.get("partial"):
        print("ОШИБКА: полный документ всё ещё помечен обрывком")
        return 1

    print("УСПЕХ: обрывок не выдаёт себя за готовое и досчитывается")
    return 0


if __name__ == "__main__":
    sys.exit(main())
