"""Пропущенный файл виден, а смена модели пропуском не считается.

Настоящий случай с мака: человек поставил файл в очередь, нажал «Запустить»
— и сразу получил экран результата «Готово · готово 0 · пропущено 1», пустой.
Ни строки о файле, ни ссылки на документ, который уже лежит рядом. Выглядит
как будто программа ничего не сделала и молча сдалась.

Пропуск сам по себе правильный (решение D-7: 80 минут счёта не повторяют
ради того, что уже посчитано), рассказать о нём забыли — событие конца
работы при пропуске не отправлялось вовсе.

Вторая половина того же случая: человек выбрал другую модель, скачал её и
запустил снова — и снова «пропущено». Модель меняют затем, чтобы получить
другой текст, поэтому старый документ, посчитанный другой моделью, поводом
для пропуска быть не может.

Движок здесь подставной: проверяем решения конвейера, а не распознавание.
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
from core.events import Kind
from core.formats import segments as segments_file
from core.job import Job, JobState
from core.media import ensure_tools
from core.pipeline import run_job
from core.profile import TARGET_TEXT, TEMP_DELETE, Profile


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


def run_once(tools, folder: Path, source: Path, model: str) -> tuple[Job, list]:
    profile = Profile.defaults()
    profile.target = TARGET_TEXT
    profile.model = model
    profile.temp_action = TEMP_DELETE
    profile.output_dir = str(folder / "готовое")
    profile.loudnorm = False

    seen: list = []
    job = Job(source=source, profile=profile)
    ctx = RunContext(paths=platform.paths().ensure(), tools=tools,
                     backend=FakeBackend(), emit=seen.append)
    run_job(job, ctx)
    return job, seen


def main() -> int:
    tools = ensure_tools([])
    folder = Path(tempfile.mkdtemp(prefix="transcriber-skip-"))
    source = folder / "лекция.mp4"
    subprocess.run([str(tools.ffmpeg), "-y", "-f", "lavfi",
                    "-i", "sine=frequency=300:duration=2",
                    "-f", "lavfi", "-i", "testsrc=size=160x120:rate=5:duration=2",
                    "-map", "1:v", "-map", "0:a", "-c:v", "libx264",
                    "-preset", "ultrafast", "-shortest", str(source)],
                   capture_output=True)

    # Первый раз считаем по-настоящему
    first, _ = run_once(tools, folder, source, "medium")
    if first.state is not JobState.DONE or first.stats.get("skipped"):
        print("ОШИБКА: первый запуск должен был посчитать документ")
        return 1

    # Второй раз той же моделью: документ на месте, считать нечего
    second, events = run_once(tools, folder, source, "medium")
    done = [e for e in events if e.kind is Kind.JOB_DONE]
    print("второй раз той же моделью -> пропущено:", second.stats.get("skipped"),
          "| событий о конце работы:", len(done))
    if not second.stats.get("skipped"):
        print("ОШИБКА: посчитали заново то, что уже лежит рядом")
        return 1
    if not done:
        print("ОШИБКА: о пропуске никто не сказал — экран результата будет пустым")
        return 1

    made = done[-1].data.get("artifacts", {})
    print("в событии есть документ:", sorted(made))
    if not made:
        print("ОШИБКА: в событии нет готового документа — "
              "кнопке «открыть» нечего открывать")
        return 1

    # Третий раз другой моделью: человек просит другой текст
    third, _ = run_once(tools, folder, source, "large-v3")
    print("третий раз другой моделью -> пропущено:", bool(third.stats.get("skipped")))
    if third.stats.get("skipped"):
        print("ОШИБКА: выбрали другую модель, а получили старый текст")
        return 1

    head = segments_file.meta(Path(third.profile.output_dir) / "лекция.segments.jsonl")
    print("в файле сегментов записана модель:", head.get("model"))

    print("УСПЕХ: пропуск виден, а смена модели заставляет считать заново")
    return 0


if __name__ == "__main__":
    sys.exit(main())
