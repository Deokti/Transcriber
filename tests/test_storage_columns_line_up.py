"""Столбец «Размер» в «Хранилище» ровный во всех строках.

Ошибка: колонка кнопок в строке таблицы была раскладкой-строкой, и Qt
сжимал её в ноль, когда кнопок в строке нет. Так бывает у ffmpeg,
поставленного в системе: удалять его не нам, кнопки нет — и размер с
состоянием в этой строке уезжали влево от столбца. Таблица переставала
читаться столбиком, а заметить это можно было только глазами.

Вторая ошибка того же рода: в узком окне раскладка ужимала не только
описание, но и столбцы размера и состояния — в строке с длинным описанием
сильнее, чем в короткой. При минимальной ширине окна столбцы снова шли
лесенкой.

Проверяем числом: левый край ячейки размера одинаков в шапке и во всех
строках — в обычном окне и в самом узком, какое разрешает программа.
ffmpeg подставляем системный — именно у него кнопок нет, — чтобы не
зависеть от того, что стоит на машине.
"""
import sys

from PySide6.QtCore import QPointF, QTimer

from harness import bridges, done, start

app, window, settings, i18n = start(theme="light", screen="storage")
storage = bridges["storage"]


def walk(item):
    for child in item.childItems():
        yield child
        yield from walk(child)


def settle() -> None:
    # Без отрисовки раскладка не посчитана: без экрана кадра может не случиться
    for _ in range(3):
        window.grabWindow()


def check() -> None:
    storage.refresh()
    storage._data["ffmpeg"] = {"found": True, "ours": False, "path": r"C:\ffmpeg\bin\ffmpeg.exe",
                               "bytes": 0.0, "date": ""}
    storage.changed.emit()
    settle()

    root = window.contentItem()
    report = []
    for width in (1080, 900):           # 900 — самое узкое окно (Theme.minWidth)
        # Меняем область содержимого, а не окно: без экрана окну не приходит
        # событие изменения размера
        root.setProperty("width", width)
        settle()
        cells = [item for item in walk(root)
                 if item.objectName() == "sizeCell" and item.isVisible()]
        if len(cells) < 3:
            done(app, False, f"нашёл ячеек размера: {len(cells)} — экран не тот, что ждали")
            return
        lefts = sorted({round(item.mapToItem(root, QPointF(0, 0)).x()) for item in cells})
        if len(lefts) != 1:
            done(app, False, f"окно {width}: столбец размеров разъехался, левые края {lefts}")
            return
        report.append(f"{width}: x={lefts[0]}")
    done(app, True, f"столбец размеров ровный, {len(cells)} ячеек ({'; '.join(report)})")


QTimer.singleShot(300, check)
QTimer.singleShot(15000, lambda: done(app, False, "тест не уложился в 15 секунд"))
code = app.exec()
storage.shutdown()
sys.exit(code)
