"""Отмена скачивания модели: новый путь HuggingFace выключен вовремя.

Ошибка из ревью ядра. Новая схема скачивания HuggingFace (Xet) качает в
своих потоках, и наша отмена до них не доходит — закачка идёт дальше, как
будто её не просили встать. Мы её выключали переменной окружения, но
ставили её внутри download(), уже после import huggingface_hub. А
библиотека читает переменную ровно один раз — при импорте — и потом
смотрит только в свою константу. Переменная стояла, а Xet работал.

Проверить это можно только в свежем процессе: важен порядок импортов.
Импортируем наш пакет core.env, потом huggingface_hub — и спрашиваем у
библиотеки, что она решила.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent

PROBE = """
import sys
sys.path.insert(0, %r)
import core.env                       # первым — как в окне и в командной строке
from huggingface_hub import constants
from huggingface_hub.utils._runtime import is_xet_available
print(constants.HF_HUB_DISABLE_XET, is_xet_available())
""" % str(ROOT)


def main() -> int:
    done = subprocess.run([sys.executable, "-c", PROBE], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        print("ОШИБКА: проба не запустилась")
        print(done.stderr[-800:])
        return 1
    disabled, available = done.stdout.split()
    print("библиотека считает Xet выключенным:", disabled)
    print("библиотека готова качать через Xet:", available)

    if disabled != "True" or available != "False":
        print("ОШИБКА: Xet остался включён — отмена скачивания до него не доходит")
        return 1

    print("УСПЕХ: переменная встаёт раньше импорта, и библиотека её видит")
    return 0


if __name__ == "__main__":
    sys.exit(main())
