"""Путь с квадратными скобками командная строка берёт, а не молчит.

Ошибка из настоящего запуска: папка курса называется
«5. System Design [Balun.Courses]», а для маски квадратные скобки — набор
символов. Существующий файл принимался за шаблон, шаблон ничего не
находил, и программа отвечала «нечего обрабатывать» — на файл, который
лежит на месте.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from cli.main import expand


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="transcriber-paths-"))
    folder = root / "5. System Design [Balun.Courses]"
    folder.mkdir()
    lesson = folder / "1.2. Балансировка нагрузки .mp4"
    lesson.write_bytes(b"not really video")

    problems = []

    found = expand([str(lesson)])
    print("файл в скобочной папке:", [p.name for p in found] or "не найден")
    if [p.name for p in found] != [lesson.name]:
        problems.append("файл со скобками в пути не найден")

    found = expand([str(folder)])
    print("папка целиком:", [p.name for p in found] or "пусто")
    if [p.name for p in found] != [lesson.name]:
        problems.append("папка со скобками не раскрыта")

    # Маска обязана продолжать работать: скобки не должны её сломать.
    found = expand([str(folder / "*.mp4")])
    print("маска внутри папки:", [p.name for p in found] or "пусто")
    if [p.name for p in found] != [lesson.name]:
        problems.append("маска в скобочной папке перестала работать")

    lesson.unlink()
    folder.rmdir()
    root.rmdir()

    if problems:
        print("ПРОВАЛ: " + "; ".join(problems))
        return 1
    print("УСПЕХ: скобки в пути больше не мешают")
    return 0


if __name__ == "__main__":
    sys.exit(main())
