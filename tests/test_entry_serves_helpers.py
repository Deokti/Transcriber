"""Собранная программа должна узнавать свои служебные запуски.

Настоящая ошибка: на маке после работы открывалась вторая копия программы.
Виноват служебный процесс multiprocessing — сторож ресурсов. Python заводит
его командой «интерпретатор, выполни вот этот код», но в собранном виде
вместо интерпретатора запускается сама программа: ключ -c она не понимает и
просто открывает окно. Замок, из-за которого сторож появляется, создаёт tqdm.

PyInstaller умеет разобрать такой запуск, но только если программа позвала
multiprocessing.freeze_support() — сам по себе его перехват лежит без дела.

Проверяем точку входа: вызов есть и стоит раньше, чем подтягивается окно.
Иначе служебный процесс сперва поднимет Qt со всеми мостами — а это секунды
и сотни мегабайт на процесс, который должен только сторожить.
"""
from __future__ import annotations

from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

ENTRY = Path(__file__).resolve().parent.parent / "tools" / "entry.py"


def main() -> int:
    lines = ENTRY.read_text(encoding="utf-8").splitlines()

    call = next((i for i, line in enumerate(lines)
                 if "freeze_support()" in line and not line.strip().startswith("#")), None)
    window = next((i for i, line in enumerate(lines)
                   if "from app.main import" in line), None)

    print("вызов freeze_support в строке:", call)
    print("окно подтягивается в строке:", window)

    if call is None:
        print("ОШИБКА: точка входа не разбирает служебные запуски — "
              "в собранном виде откроется второе окно")
        return 1
    if window is None:
        print("ОШИБКА: точка входа вообще не поднимает окно — тест устарел")
        return 1
    if call > window:
        print("ОШИБКА: сначала поднимается окно, потом разбор запуска — "
              "служебный процесс успеет загрузить Qt")
        return 1

    print("УСПЕХ: служебные запуски разбираются до всего остального")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
