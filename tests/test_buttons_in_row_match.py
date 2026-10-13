"""Кнопки, стоящие рядом, одной высоты.

Ошибка: высота кнопки была привязана к её важности — главная 36 точек,
обычная 32. Одна главная кнопка от этого только выигрывает, но в подвале
главного экрана «Сохранить пресет» и «Запустить» стоят бок о бок, и
разница в четыре точки читается как небрежность: низ кнопок не на одной
линии. Заметил человек, а не проверка. То же было у «Выбрать файлы…» и
«Выбрать папку…» и в окне сохранения пресета.

Проверяем: на каждом экране — и в открытом окне сохранения пресета — все
видимые кнопки с общим родителем одной высоты.
"""
import sys

from PySide6.QtCore import QObject, QTimer

import harness

SCREENS = ["main", "storage", "diagnostics", "settings", "result", "progress", "setup", "preset"]
app, window, settings, i18n = harness.start(theme="light", screen="main")
state = {"i": 0}
problems: list[str] = []


def walk(item):
    for child in item.childItems():
        yield child
        yield from walk(child)


def is_button(item) -> bool:
    # Свою кнопку узнаём по её свойствам: у системных их нет
    return item.property("primary") is not None and item.property("flat_") is not None


def label(item) -> str:
    return f"«{item.property('text')}» {round(item.height())}"


def check(name: str) -> None:
    roots = [window.contentItem()]
    # Всплывающее окно живёт в своём слое, а не среди элементов экрана
    roots += [o.property("contentItem") for o in window.findChildren(QObject)
              if o.metaObject().className().startswith("PresetPopup") and o.property("visible")]
    groups: dict = {}
    seen: set = set()
    for root in roots:
        for item in walk(root):
            # Слой всплывающих окон виден и из дерева экрана — не считаем дважды
            if is_button(item) and item.isVisible() and id(item) not in seen:
                seen.add(id(item))
                groups.setdefault(id(item.parentItem()), []).append(item)
    for buttons in groups.values():
        heights = {round(b.height()) for b in buttons}
        if len(buttons) > 1 and len(heights) > 1:
            problems.append(f"{name}: " + ", ".join(label(b) for b in buttons))


def visit() -> None:
    if state["i"] >= len(SCREENS):
        if problems:
            harness.done(app, False, "кнопки в одном ряду разной высоты — " + "; ".join(problems))
        else:
            harness.done(app, True, f"экранов пройдено {len(SCREENS)}, кнопки в рядах ровные")
        return
    name = SCREENS[state["i"]]
    if name == "preset":
        window.setProperty("screen", "main")
        popup = next(o for o in window.findChildren(QObject)
                     if o.metaObject().className().startswith("PresetPopup"))
        popup.setProperty("visible", True)
    else:
        window.setProperty("screen", name)
    for _ in range(3):
        window.grabWindow()      # без кадра раскладка не досчитана
    check(name)
    state["i"] += 1
    QTimer.singleShot(300, visit)


QTimer.singleShot(300, visit)
QTimer.singleShot(20000, lambda: harness.done(app, False, "тест не уложился в 20 секунд"))
code = app.exec()
for bridge in ("diagnostics", "storage", "deps", "queue", "run"):
    harness.bridges[bridge].shutdown()
sys.exit(code)
