"""Скачанная модель загружается без единого похода в сеть.

Ошибка из настоящего запуска: движок на каждом старте спрашивал
HuggingFace, не появилась ли новая версия модели. Запрос уходит в сеть
даже тогда, когда модель давно лежит на диске, и в плохой сети висит
минутами. Окно в это время показывало пустую стадию, кнопка «Отменить
всё» ничего не меняла — и выглядело это как зависшая программа.

Вторая ошибка, оттуда же: просить модель по имени хранилища недостаточно.
HuggingFace считает скачанным только полный слепок — вместе с README и
.gitattributes, — а мы качаем ровно то, что нужно движку. Свой же слепок он
называет неполным и без сети открывать отказывается:

    IncompleteSnapshotError: ... is incomplete: 2 file(s) are missing
    (.gitattributes, README.md)

Поэтому модель отдаём папкой, а не именем. И заодно следим, чтобы следы
прерванной загрузки не считались моделью: раньше хватало одного model.bin,
и окно бодро сообщало «скачана» о том, что открыть нельзя.

Настоящую модель для этого грузить не надо — подменяем сам класс
faster-whisper и смотрим, с чем его позвали.
"""
import sys
import tempfile
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

import faster_whisper

from core.asr.faster_whisper_backend import FasterWhisperBackend

MODEL = "large-v3"

#: Что кладёт наша загрузка: ровно то, что открывает движок, без README.
PARTS = ("model.bin", "config.json", "tokenizer.json")


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
    cached = root / f"models--Systran--faster-whisper-{MODEL}" / "snapshots" / "abc"

    # Папка, в которой модели нет: качать разрешено.
    empty = load_with(root)

    # Обрывок: один model.bin без остального — открыть такое нельзя.
    cached.mkdir(parents=True)
    (cached / "model.bin").write_bytes(b"not a real model")
    partial = load_with(root)

    # Полный набор в раскладке HuggingFace: в сеть ходить незачем.
    for name in PARTS:
        (cached / name).write_bytes(b"{}")
    ready = load_with(root)

    print("модели нет        -> просим:", empty["model"],
          "| только из файлов:", empty.get("local_files_only"))
    print("один model.bin    -> просим:", partial["model"],
          "| только из файлов:", partial.get("local_files_only"))
    print("полный набор      -> просим:", Path(ready["model"]).name,
          "| только из файлов:", ready.get("local_files_only"))

    if empty.get("local_files_only") is not False or empty["model"] != MODEL:
        print("ОШИБКА: модели нет на диске, а движку не дали её скачать")
        return 1
    if partial.get("local_files_only") is not False:
        print("ОШИБКА: обрывок загрузки принят за модель — "
              "движок откроет его и упадёт уже в работе")
        return 1
    if ready.get("local_files_only") is not True:
        print("ОШИБКА: движок лезет в сеть за моделью, которая уже на диске")
        return 1
    if Path(ready["model"]) != cached:
        print("ОШИБКА: модель просят по имени хранилища, а не папкой — "
              "HuggingFace назовёт свой слепок неполным и откажет")
        return 1

    print("УСПЕХ: скачанная модель открывается папкой и без сети")
    return 0


if __name__ == "__main__":
    sys.exit(main())
