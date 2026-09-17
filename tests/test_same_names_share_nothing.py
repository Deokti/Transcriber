"""Одноимённые записи из разных папок не делят один результат.

Ошибка из ревью ядра. У курсов файлы называются одинаково: «Урок 1.mp4»
лежит в каждом модуле. Пока результат кладётся рядом с исходником, спорить
не с кем. Но стоит указать общую папку результата — и второй «Урок 1»
либо молча пропускается как «уже посчитанный» (там же лежит документ!),
либо затирает документ первого.

Теперь в заголовке сегментов записано, чей это файл. Чужой — берём имя с
папкой: «Урок 1 (Модуль 2).txt». Первый документ остаётся нетронутым.

Заодно временный WAV: раньше он звался по имени исходника, и две
одноимённые записи — или два экземпляра программы разом — писали бы в один
файл. Теперь в имени метка пути.

Движок подставной: смотрим на имена файлов, а не на распознавание.
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
from core.formats import segments as segments_file
from core.job import Job, JobState
from core.media import ensure_tools
from core.pipeline import run_job
from core.profile import TARGET_TEXT, TEMP_DELETE, Profile
from core.stages.prepare import _destination


class FakeBackend:
    """Отдаёт текст с именем папки: по документу видно, чья это запись."""

    def load(self, *args, **kwargs) -> float:
        return 0.0

    def downloaded(self, model: str) -> bool:
        return True

    def download(self, model: str, **kwargs) -> None:
        raise AssertionError("качать модель в этом тесте не должны")

    def transcribe(self, audio: Path, profile):
        info = TranscriptionInfo(language="ru", language_probability=1.0, duration=2.0)
        return info, iter([Segment(start=0.0, end=2.0, text=f"запись из {audio.name}")])

    def unload(self) -> None:
        pass


def make_source(tools, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / "Урок 1.mp4"
    subprocess.run([str(tools.ffmpeg), "-y", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=2",
                    "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=2",
                    "-map", "1:v", "-map", "0:a", "-c:v", "libx264",
                    "-preset", "ultrafast", "-shortest", str(source)],
                   capture_output=True)
    return source


def main() -> int:
    tools = ensure_tools([])
    root = Path(tempfile.mkdtemp(prefix="transcriber-names-"))
    shared = root / "готовое"

    profile = Profile.defaults()
    profile.target = TARGET_TEXT
    profile.temp_action = TEMP_DELETE
    profile.output_dir = str(shared)
    profile.loudnorm = False

    ctx = RunContext(paths=platform.paths().ensure(), tools=tools,
                     backend=FakeBackend(), emit=lambda event: None)
    first = Job(source=make_source(tools, root / "Модуль 1"), profile=profile)
    second = Job(source=make_source(tools, root / "Модуль 2"), profile=profile)

    temps = {_destination(first, ctx).name, _destination(second, ctx).name}
    print("временные файлы:", sorted(temps))
    if len(temps) != 2:
        print("ОШИБКА: две записи делят один временный WAV")
        return 1

    run_job(first, ctx)
    run_job(second, ctx)
    documents = sorted(p.name for p in shared.glob("*.txt"))
    print("документы в общей папке:", documents)
    print("второй файл: состояние", second.state.value,
          "| пропущен:", bool(second.stats.get("skipped")))

    if second.stats.get("skipped"):
        print("ОШИБКА: вторую запись пропустили, приняв чужой документ за её")
        return 1
    if second.state is not JobState.DONE or len(documents) != 2:
        print("ОШИБКА: у двух записей должно быть два документа")
        return 1
    if "Урок 1.txt" not in documents or "Урок 1 (Модуль 2).txt" not in documents:
        print("ОШИБКА: второй документ должен получить имя с папкой")
        return 1

    owner = segments_file.meta(shared / "Урок 1.segments.jsonl").get("source_path")
    print("первый документ по-прежнему принадлежит:", Path(owner or "").parent.name)
    if owner != str(first.source):
        print("ОШИБКА: документ первой записи затёрт второй")
        return 1

    print("УСПЕХ: одноимённые записи получают разные имена, первая не пострадала")
    return 0


if __name__ == "__main__":
    sys.exit(main())
