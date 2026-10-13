"""Окно открывается без петель привязок.

Ошибка: мост «Хранилища» опрашивал диск лениво — при первом чтении любого
свойства — и тут же объявлял «всё изменилось». Первое чтение случается
посреди вычисления привязки в разметке, и привязка оказывалась зависимой
от самой себя: Qt писал «Binding loop detected» и оставлял строку
состояния с тем значением, какое успел посчитать. Заметили только в
собранной под Linux программе, где предупреждения видно в терминале.

Проверяем на всех экранах: ни одного предупреждения о петле привязки.
"""
import sys

from PySide6.QtCore import QTimer, qInstallMessageHandler

import harness

loops: list[str] = []


def listen(_kind, _context, message: str) -> None:
    if "Binding loop" in message:
        loops.append(message.strip())


qInstallMessageHandler(listen)

SCREENS = ["main", "setup", "storage", "diagnostics", "settings", "result", "progress"]
app, window, settings, i18n = harness.start(theme="light", screen="main")
state = {"i": 0}


def visit() -> None:
    if state["i"] >= len(SCREENS):
        if loops:
            harness.done(app, False, f"петель привязок: {len(loops)}, первая: {loops[0]}")
        else:
            harness.done(app, True, f"экранов пройдено {len(SCREENS)}, петель привязок нет")
        return
    window.setProperty("screen", SCREENS[state["i"]])
    window.grabWindow()          # без кадра привязки не досчитываются
    state["i"] += 1
    QTimer.singleShot(400, visit)


QTimer.singleShot(200, visit)
QTimer.singleShot(20000, lambda: harness.done(app, False, "тест не уложился в 20 секунд"))
code = app.exec()
for name in ("diagnostics", "storage", "deps", "queue", "run"):
    harness.bridges[name].shutdown()
sys.exit(code)
