"""Пока идёт работа, «Хранилище» не удаляет модели и временные файлы.

Движок держит модель открытой всё время распознавания, а подготовленный звук
лежит во временной папке. Удали их посреди работы — она упадёт на полуслове,
и посчитанное не спасётся. Окно выключает кнопки, но мост не полагается на
окно: проверка стоит в нём самом, и её мы и проверяем.

Все папки поддельные: и модели, и папка данных программы подменяются на
временные. Иначе тест на сломанном коде очистил бы настоящую временную
папку — ровно то, от чего он защищает.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from PySide6.QtCore import QCoreApplication

from app.bridge import EnvBridge, SettingsBridge, StorageBridge
from core import platform
from core.env import models
from core.platform import Paths


def main() -> int:
    _app = QCoreApplication(sys.argv)
    root = Path(tempfile.mkdtemp(prefix="transcriber-busy-"))
    home = root / "tiny"
    home.mkdir()
    for part in models.NEEDED:
        (home / part).write_bytes(b"{}")

    data = root / "data"
    sandbox = Paths(data, data / "bin", data / "models", data / "temp",
                    data / "logs", data / "profiles")
    platform.paths = lambda: sandbox          # мост спрашивает папки здесь

    settings = SettingsBridge()
    settings.setModelsDir(str(root))
    env = EnvBridge(settings)
    working = {"now": True}
    storage = StorageBridge(settings, env, working=lambda: working["now"])

    temp = platform.paths().ensure().temp / "lecture_16k.wav"
    temp.write_bytes(b"w" * 100)
    storage.removeModel("tiny")
    storage.clearTemp()
    during = (home.exists(), temp.exists(), storage.locked)
    print("во время работы: модель на месте", during[0], "| звук на месте", during[1],
          "| экран знает, что заперто", during[2])

    working["now"] = False
    storage.removeModel("tiny")
    after = home.exists()
    print("после работы: модель удалена", not after)

    if not (during[0] and during[1] and during[2]):
        print("ПРОВАЛ: посреди работы удалено то, что держит движок")
        return 1
    if after:
        print("ПРОВАЛ: после работы модель так и не удалилась")
        return 1
    print("УСПЕХ: удаление ждёт конца работы")
    return 0


if __name__ == "__main__":
    sys.exit(main())
