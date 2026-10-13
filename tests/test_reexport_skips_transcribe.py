"""Другой формат из готовых сегментов — за секунду, без распознавания.

Сценарий 6.3 и FR-19. Посчитал лекцию в txt, потом понадобился docx или
субтитры — раньше программа начинала всё заново: восемьдесят минут ради
того, что уже лежит на диске в файле сегментов.

Теперь в заголовке сегментов записан рецепт — настройки, от которых зависит
сам текст. Совпадает рецепт — документ собирается из готового. Не совпадает
(другая модель, другой язык, другой звук) — честно считаем заново: человек
поменял настройку как раз затем, чтобы получить другой текст.

Работает, когда файл сегментов оставлен: по умолчанию он после работы
убирается (решение D-17), и тогда новый формат считается заново.

Движок подставной и считает, сколько раз его просили распознать.
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
from core.profile import TARGET_TEXT, TEMP_DELETE, Profile


class CountingBackend:
    """Отдаёт два сегмента и запоминает, сколько раз его заставили считать."""

    calls = 0

    def load(self, *args, **kwargs) -> float:
        return 0.0

    def downloaded(self, model: str) -> bool:
        return True

    def download(self, model: str, **kwargs) -> None:
        raise AssertionError("качать модель в этом тесте не должны")

    def transcribe(self, audio: Path, profile):
        CountingBackend.calls += 1
        info = TranscriptionInfo(language="ru", language_probability=1.0, duration=2.0)
        return info, iter([Segment(start=0.0, end=1.0, text="первая фраза."),
                           Segment(start=1.0, end=2.0, text="вторая фраза.")])

    def unload(self) -> None:
        pass


def run(tools, folder: Path, source: Path, fmt: str, model: str = "medium") -> Job:
    profile = Profile.defaults()
    profile.target = TARGET_TEXT
    profile.model = model
    profile.formats = [fmt]
    profile.temp_action = TEMP_DELETE
    profile.keep_segments = True       # из чего собирать новый формат
    profile.output_dir = str(folder / "готовое")
    profile.loudnorm = False
    job = Job(source=source, profile=profile)
    ctx = RunContext(paths=platform.paths().ensure(), tools=tools,
                     backend=CountingBackend(), emit=lambda event: None)
    run_job(job, ctx)
    return job


def main() -> int:
    tools = ensure_tools([])
    folder = Path(tempfile.mkdtemp(prefix="transcriber-reexport-"))
    source = folder / "лекция.mp4"
    subprocess.run([str(tools.ffmpeg), "-y", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=2",
                    "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=2",
                    "-map", "1:v", "-map", "0:a", "-c:v", "libx264",
                    "-preset", "ultrafast", "-shortest", str(source)],
                   capture_output=True, check=True)
    out = folder / "готовое"

    first = run(tools, folder, source, "txt")
    print("первый запуск, txt: распознаваний", CountingBackend.calls)

    second = run(tools, folder, source, "docx")
    print("тот же файл, docx: распознаваний", CountingBackend.calls,
          "| docx есть:", (out / "лекция.docx").exists(),
          "| из готового:", bool(second.stats.get("reused")))

    third = run(tools, folder, source, "srt", model="large-v3")
    print("другая модель, srt: распознаваний", CountingBackend.calls,
          "| из готового:", bool(third.stats.get("reused")))

    if first.state is not JobState.DONE or CountingBackend.calls < 1:
        print("ОШИБКА: первый запуск не распознал запись")
        return 1
    if not second.stats.get("reused") or not (out / "лекция.docx").exists():
        print("ОШИБКА: ради нового формата запись распознана заново — "
              "восемьдесят минут вместо секунды")
        return 1
    if second.state is not JobState.DONE or second.stats.get("segments") != 2:
        print("ОШИБКА: документ из готового собран не из всех сегментов")
        return 1
    if CountingBackend.calls != 2 or third.stats.get("reused"):
        print("ОШИБКА: модель другая, а текст взяли старый")
        return 1

    print("УСПЕХ: новый формат собирается из готового, смена модели считает заново")
    return 0


if __name__ == "__main__":
    sys.exit(main())
