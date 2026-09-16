"""Скачанная модель загружается без единого похода в сеть.

Ошибка из настоящего запуска: движок на каждом старте спрашивал
HuggingFace, не появилась ли новая версия модели. Запрос уходит в сеть
даже тогда, когда модель давно лежит на диске, и в плохой сети висит
минутами. Окно в это время показывало пустую стадию, кнопка «Отменить
всё» ничего не меняла — и выглядело это как зависшая программа.

Проверяем не сеть, а договор: если модель на диске, движок обязан
попросить «только из файлов». Настоящую модель для этого грузить не надо
— подменяем сам класс faster-whisper и смотрим, с чем его позвали.
"""
import sys
import tempfile
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

import faster_whisper

from core.asr.faster_whisper_backend import FasterWhisperBackend

MODEL = "large-v3"


class Recorder:
    """Подставной движок: запоминает, с чем его создали."""

    calls: list[dict] = []

    def __init__(self, model, **kwargs):
        Recorder.calls.append(dict(model=model, **kwargs))


def load_with(models_dir: Path) -> dict:
    Recorder.calls.clear()
    real, faster_whisper.WhisperModel = faster_whisper.WhisperModel, Recorder
    try:
        FasterWhisperBackend(models_dir).load(MODEL, "cpu", "int8")
    finally:
        faster_whisper.WhisperModel = real
    return Recorder.calls[-1]


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="transcriber-models-"))

    # Папка, в которой модели нет: качать разрешено.
    empty = load_with(root)

    # Папка с моделью в раскладке HuggingFace: в сеть ходить незачем.
    cached = root / f"models--Systran--faster-whisper-{MODEL}" / "snapshots" / "abc"
    cached.mkdir(parents=True)
    (cached / "model.bin").write_bytes(b"not a real model")
    ready = load_with(root)

    print("модели нет на диске  -> local_files_only =", empty.get("local_files_only"))
    print("модель лежит на диске -> local_files_only =", ready.get("local_files_only"))

    ok = ready.get("local_files_only") is True and empty.get("local_files_only") is False
    print(("УСПЕХ: " if ok else "ПРОВАЛ: ")
          + ("скачанная модель грузится без сети" if ok
             else "движок лезет в сеть за моделью, которая уже на диске"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
