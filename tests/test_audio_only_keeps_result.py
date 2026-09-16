"""Сценарий «нужен только звук» отдаёт файл, а не пустую папку (FR-8).

Ошибка: для конвейера извлечённый WAV всегда был промежуточным файлом, а
уборка по умолчанию промежуточные удаляет. Поэтому запуск с «только звук»
честно вытаскивал дорожку, писал «готово» — и удалял единственный
результат. Папка оставалась пустой, и никто об этом не сообщал.

Модель здесь не нужна: распознавание в этом сценарии не запускается.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core import platform
from core.context import RunContext
from core.events import Event
from core.job import Job, JobState
from core.media import ensure_tools
from core.pipeline import run_job
from core.profile import TARGET_AUDIO, TEMP_DELETE, Profile


class NoBackend:
    """Движка в этом сценарии не бывает: до распознавания дело не доходит."""

    def load(self, *args, **kwargs):
        raise AssertionError("распознавание не должно запускаться")

    def downloaded(self, model: str) -> bool:
        return True

    def transcribe(self, *args, **kwargs):
        raise AssertionError("распознавание не должно запускаться")

    def unload(self) -> None:
        pass


def main() -> int:
    tools = ensure_tools([])
    folder = Path(tempfile.mkdtemp(prefix="transcriber-audio-"))
    source = folder / "запись.mp4"
    subprocess.run([str(tools.ffmpeg), "-y", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=2",
                    "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=2",
                    "-map", "1:v", "-map", "0:a", "-c:v", "libx264",
                    "-preset", "ultrafast", "-shortest", str(source)],
                   capture_output=True)

    out = folder / "готовое"
    profile = Profile.defaults()
    profile.target = TARGET_AUDIO
    profile.temp_action = TEMP_DELETE      # умолчание, на котором всё и терялось
    profile.output_dir = str(out)
    profile.loudnorm = False

    job = Job(source=source, profile=profile)
    ctx = RunContext(paths=platform.paths().ensure(), tools=tools,
                     backend=NoBackend(), emit=lambda event: None)
    run_job(job, ctx)

    made = sorted(p.name for p in out.iterdir()) if out.is_dir() else []
    print("состояние задачи:", job.state.value, "| в папке результата:", made or "пусто")

    ok = job.state is JobState.DONE and any(name.endswith(".wav") for name in made)
    print(("УСПЕХ: " if ok else "ПРОВАЛ: ")
          + ("звук остался там, где его ждут" if ok
             else "звук извлечён и потерян — папка результата пуста"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
