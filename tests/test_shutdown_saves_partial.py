"""Закрытие программы посреди работы не теряет посчитанное.

Ошибка из ревью ядра: рабочий поток очереди — daemon. Закрыл окно на
середине трёхчасовой записи — процесс вышел, поток оборвался где попало:
посреди экспорта документа или уборки временного WAV. Ни документа из
посчитанной половины, ни чистой папки temp.

Теперь перед выходом ядро просят остановиться и ждут: отмена запускает
спасение посчитанного (решение D-7), и только когда поток закончил, процесс
имеет право выйти.

Движок подставной: отдаёт сегмент за сегментом, пока его не остановят.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core import platform
from core.asr.base import Segment, TranscriptionInfo
from core.formats import segments as segments_file
from core.job import Job, JobState
from core.media import ensure_tools
from core.profile import TARGET_TEXT, TEMP_DELETE, Profile
from core.runner import JobRunner


class EndlessBackend:
    """Сегменты идут, пока конвейер сам не скажет «хватит»."""

    def load(self, *args, **kwargs) -> float:
        return 0.0

    def downloaded(self, model: str) -> bool:
        return True

    def download(self, model: str, **kwargs) -> None:
        raise AssertionError("качать модель в этом тесте не должны")

    def transcribe(self, audio: Path, profile):
        info = TranscriptionInfo(language="ru", language_probability=1.0, duration=3600.0)

        def stream():
            second = 0
            while True:                      # остановит только отмена между сегментами
                yield Segment(start=second, end=second + 1, text=f"секунда {second}")
                second += 1
                time.sleep(0.02)

        return info, stream()

    def unload(self) -> None:
        pass


def main() -> int:
    tools = ensure_tools([])
    folder = Path(tempfile.mkdtemp(prefix="transcriber-shutdown-"))
    source = folder / "лекция.mp4"
    subprocess.run([str(tools.ffmpeg), "-y", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=2",
                    "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=2",
                    "-map", "1:v", "-map", "0:a", "-c:v", "libx264",
                    "-preset", "ultrafast", "-shortest", str(source)],
                   capture_output=True)

    profile = Profile.defaults()
    profile.target = TARGET_TEXT
    profile.temp_action = TEMP_DELETE
    profile.output_dir = str(folder / "готовое")
    profile.loudnorm = False
    job = Job(source=source, profile=profile)

    paths = platform.paths().ensure()
    runner = JobRunner(paths=paths, tools=tools, backend=EndlessBackend(),
                       emit=lambda event: None)
    runner.add(job)
    runner.start()

    # Даём работе дойти до распознавания: нужно что-то, что стоит спасать
    for _ in range(300):
        if len(job.segments) >= 5:
            break
        time.sleep(0.05)
    print("сегментов посчитано к моменту закрытия:", len(job.segments))
    if len(job.segments) < 5:
        print("ОШИБКА: распознавание так и не началось — тест не о том")
        return 1

    started = time.monotonic()
    finished = runner.shutdown(timeout=15)
    spent = time.monotonic() - started
    document = Path(profile.output_dir) / "лекция.txt"
    head = segments_file.meta(Path(profile.output_dir) / "лекция.segments.jsonl")
    leftovers = sorted(p.name for p in paths.temp.iterdir() if "лекция" in p.name)

    print(f"выход дождался потока: {finished} за {spent:.1f} с | поток жив: {runner.busy}")
    print("состояние задачи:", job.state.value, "| документ:", document.exists(),
          "| пометка об обрыве:", head.get("partial"))
    print("остатки в temp:", leftovers)

    if not finished or runner.busy:
        print("ОШИБКА: выход не дождался сохранения — поток оборвётся где попало")
        return 1
    if job.state is not JobState.CANCELLED:
        print("ОШИБКА: закрытие должно быть отменой, а не чем-то ещё")
        return 1
    if not document.exists() or not head.get("partial"):
        print("ОШИБКА: посчитанное не спасли перед выходом")
        return 1
    if leftovers:
        print("ОШИБКА: уборка не успела — временный звук остался")
        return 1

    print("УСПЕХ: закрытие окна спасает посчитанное и убирает за собой")
    return 0


if __name__ == "__main__":
    sys.exit(main())
