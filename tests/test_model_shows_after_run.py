"""Модель скачалась во время работы — окно должно это заметить.

Настоящая ошибка: модель скачивалась внутри работы, работа заканчивалась,
человек возвращался на главный экран — а там по-прежнему «модель medium не
скачана». Запустишь снова — она не качается, потому что ядро видит её на
диске. То есть врал именно блок «Готово к работе».

Причина в том, что опрос машины недешёвый и делается по требованию: спросили
один раз при запуске, и больше никто не просил. Теперь конец работы будит
опрос заново.

Проверяем без настоящего распознавания: важно не то, кто скачал модель, а то,
что окно перестаёт держаться за старый ответ.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from PySide6.QtGui import QGuiApplication

from app.bridge import (EnvBridge, ProfileBridge, QueueBridge, RunBridge,
                        SettingsBridge)
from app.i18n import I18n
from app.main import connect_bridges

MODEL = "tiny"


def main() -> int:
    app = QGuiApplication(sys.argv)          # мостам нужен цикл событий  # noqa: F841

    with tempfile.TemporaryDirectory() as folder:
        models = Path(folder)

        settings = SettingsBridge()
        settings.setModelsDir(str(models))   # пустая папка: моделей нет
        env = EnvBridge(settings)
        profile = ProfileBridge(settings)
        queue = QueueBridge(settings)
        run = RunBridge(settings, queue, profile)
        connect_bridges(settings, env, run, I18n("ru"))

        before = env.modelDownloaded(MODEL)
        print(f"до работы: модель {MODEL} на диске — {before}")
        if before:
            print("ОШИБКА: в пустой папке не может быть модели")
            return 1

        # Так выглядит скачанная модель для ядра: своя папка с файлами движка.
        # Одного model.bin мало — по обрывку прерванной загрузки модель не
        # откроется, и ядро такую папку моделью не считает.
        (models / MODEL).mkdir()
        for part in ("model.bin", "config.json", "tokenizer.json"):
            (models / MODEL / part).write_bytes(b"{}")

        stale = env.modelDownloaded(MODEL)
        print(f"файл появился, но работа ещё идёт: {stale} (ответ старый, это норма)")

        run.finished.emit()                  # работа кончилась
        after = env.modelDownloaded(MODEL)
        print(f"после работы: {after}")

        if not after:
            print("ОШИБКА: окно так и считает, что модели нет")
            return 1

    print("УСПЕХ: конец работы обновляет блок «Готово к работе»")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
