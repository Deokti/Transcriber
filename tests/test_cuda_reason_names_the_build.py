"""Почему видеокарта недоступна: у собранной программы причина другая.

Настоящий случай: человек поставил процессорную сборку на машину с RTX 5070
и увидел «не найдены библиотеки CUDA». Звучит как сломанный компьютер —
а на самом деле библиотек нет в самой сборке, и доставить их нельзя:
нужна другая сборка. Из исходников та же строка означает ровно обратное:
поставьте пакеты.

Проверяем обе стороны: собранная программа и запуск из исходников при одной
и той же неготовой CUDA.
"""
from __future__ import annotations

import sys

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core import platform


def reason(packed: bool) -> str:
    """Причина отказа от видеокарты при неготовой CUDA."""
    platform.prepare_cuda = lambda emit=None: (False, {})   # библиотек нет
    platform.system_name = lambda: "windows"                # мак отвечает раньше
    if packed:
        sys.frozen = True
    else:
        if hasattr(sys, "frozen"):
            del sys.frozen
    gpu = next(d for d in platform.devices() if d.id == "cuda")
    return gpu.reason or ""


def main() -> int:
    packed = reason(True)
    source = reason(False)
    print("собранная программа:", packed)
    print("запуск из исходников:", source)

    if packed != platform.NO_CUDA_IN_BUILD:
        print("ОШИБКА: собранная программа валит вину на машину")
        return 1
    if source != platform.NO_CUDA_LIBS:
        print("ОШИБКА: из исходников библиотеки как раз можно доставить")
        return 1

    print("УСПЕХ: причина называет то, что человек может изменить")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
