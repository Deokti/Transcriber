"""Три режима выхода дают ровно то, что заказали (FR-8, FR-37).

Текст — документ и ни одного лишнего файла рядом. Только звук — звуковой
файл и никакого распознавания. Оба — и документ, и звук, причём звук
переживает уборку: для неё он не промежуточный, а результат.

Движок здесь подставной: проверяем набор стадий и судьбу файлов, а не
качество распознавания.
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
from core.job import Job, JobState
from core.media import ensure_tools
from core.pipeline import run_job
from core.profile import (AUDIO_MP3, TARGET_AUDIO, TARGET_BOTH, TARGET_TEXT, TEMP_DELETE,
                          Profile)


class FakeBackend:
    """Отдаёт один сегмент, не трогая ни модели, ни видеокарту."""

    def load(self, *args, **kwargs) -> float:
        return 0.0

    def downloaded(self, model: str) -> bool:
        return True

    def download(self, model: str, **kwargs) -> None:
        raise AssertionError("качать модель в этом тесте не должны")

    def transcribe(self, audio: Path, profile):
        info = TranscriptionInfo(language="ru", language_probability=1.0, duration=2.0)
        return info, iter([Segment(start=0.0, end=2.0, text="проверка связи")])

    def unload(self) -> None:
        pass


def make_source(tools, folder: Path) -> Path:
    source = folder / "запись.mp4"
    subprocess.run([str(tools.ffmpeg), "-y", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=2",
                    "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=2",
                    "-map", "1:v", "-map", "0:a", "-c:v", "libx264",
                    "-preset", "ultrafast", "-shortest", str(source)],
                   capture_output=True)
    return source


def run_target(tools, target: str, audio_format: str = AUDIO_MP3) -> list[str]:
    folder = Path(tempfile.mkdtemp(prefix="transcriber-target-"))
    source = make_source(tools, folder)

    profile = Profile.defaults()
    profile.target = target
    profile.audio_format = audio_format
    profile.temp_action = TEMP_DELETE     # умолчание: промежуточное убирается
    profile.output_dir = str(folder / "готовое")
    profile.loudnorm = False

    job = Job(source=source, profile=profile)
    ctx = RunContext(paths=platform.paths().ensure(), tools=tools,
                     backend=FakeBackend(), emit=lambda event: None)
    run_job(job, ctx)
    assert job.state is JobState.DONE, f"{target}: задача не дошла до конца"

    out = Path(profile.output_dir)
    return sorted(p.suffix for p in out.iterdir()) if out.is_dir() else []


def main() -> int:
    tools = ensure_tools([])
    problems = []

    made = run_target(tools, TARGET_TEXT)
    print("текст          ->", made)
    if made != [".jsonl", ".txt"]:
        problems.append(f"текст: {made}")

    made = run_target(tools, TARGET_AUDIO)
    print("только звук    ->", made)
    if made != [".mp3"]:
        problems.append(f"только звук: {made}")

    made = run_target(tools, TARGET_BOTH)
    print("текст и звук   ->", made)
    if made != [".jsonl", ".mp3", ".txt"]:
        problems.append(f"текст и звук: {made}")

    if problems:
        print("ПРОВАЛ: получилось не то — " + "; ".join(problems))
        return 1
    print("УСПЕХ: каждый режим отдаёт ровно заказанное")
    return 0


if __name__ == "__main__":
    sys.exit(main())
