"""Настройки из панели «Дополнительно» доезжают до задачи.

Поля на экране — половина дела: выбранное должно оказаться в профиле,
который уходит в ядро при запуске. Проверяем цепочку целиком, а не
свойства моста: находим поля в окне, дёргаем их тем же сигналом, каким
их дёргает человек мышью, и смотрим, что лежит в снимке профиля — том
самом, который получает очередь.

Пять настроек, которых в окне не было вовсе: чувствительность к речи
(FR-32), длина фрагмента (FR-33), потоки процессора (FR-34), судьба
промежуточного WAV (FR-29) и «считать заново» (FR-38).
"""
import sys

import harness
from PySide6.QtCore import Q_ARG, QMetaObject, QPoint, Qt, QTimer
from PySide6.QtTest import QTest

from harness import done, start

app, window, settings, i18n = start(theme="light", screen="main")

#: Подпись поля, выбираемый код, поле профиля, ожидаемое значение.
#: Значения нарочно не совпадают с умолчаниями — иначе проверять нечего.
CHOICES = [
    ("advanced.sensitivityField", "high", "sensitivity", "high"),
    ("advanced.chunkField", "45", "chunk_length", 45),
    ("advanced.threadsField", "8", "cpu_threads", 8),
    ("advanced.tempField", "keep", "temp_action", "keep"),
]


def walk(item):
    for child in item.childItems():
        yield child
        yield from walk(child)


def settle() -> None:
    for _ in range(3):
        window.grabWindow()


def by_label(label: str):
    """Поле узнаём по подписи: свойство label есть у ComboField."""
    wanted = i18n.strings[label]
    return next((item for item in walk(window.contentItem())
                 if item.property("label") == wanted), None)


def check() -> None:
    settle()
    panel = next((i for i in walk(window.contentItem())
                  if i.property("open") is not None), None)
    if panel is None:
        done(app, False, "панель «Дополнительно» не найдена")
        return

    # Свёрнутая панель полей не показывает — раскрываем, как это делает щелчок.
    # И даём области вырасти: раскрытая панель уходит под нижний край, а по
    # тому, что за краем, не щёлкнешь — ни человек, ни тест.
    window.contentItem().setProperty("height", 1000)
    panel.setProperty("open", True)
    settle()

    task = harness.bridges["task"]
    before = task.snapshot()
    problems = []

    for label, chosen, *_ in CHOICES:
        item = by_label(label)
        if item is None:
            problems.append(f"{i18n.strings[label]}: поля нет в окне")
            continue
        # Ровно тот сигнал, который поле шлёт, когда человек выбирает пункт
        QMetaObject.invokeMethod(item, "chosen", Qt.DirectConnection, Q_ARG(str, chosen))

    force = next((i for i in walk(window.contentItem())
                  if i.property("text") == i18n.strings["advanced.force"]), None)
    if force is None:
        problems.append("переключателя «считать заново» нет в окне")
    else:
        # Галочку жмём по-настоящему: toggle() меняет состояние, но сигнал
        # toggled Qt шлёт только на настоящее нажатие — а весь смысл проверки
        # в том, чтобы пройти путь человека, а не обойти его.
        spot = force.mapToScene(QPoint(int(force.property("width") / 2),
                                       int(force.property("height") / 2))).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, spot)
        settle()

    after = task.snapshot()
    for label, chosen, name, expected in CHOICES:
        got = getattr(after, name)
        print(f"{i18n.strings[label]:26} выбрали {chosen!r:6} → профиль: {got!r}")
        if got != expected:
            problems.append(f"{i18n.strings[label]}: в профиле {got!r}, а не {expected!r}")

    print(f"{i18n.strings['advanced.force']:26} переключили   → профиль: {after.force!r}")
    if after.force == before.force:
        problems.append("«считать заново» не доехало до профиля")

    done(app, not problems,
         "; ".join(problems) if problems
         else "все пять настроек доезжают до профиля, который уходит в ядро")


QTimer.singleShot(700, check)
sys.exit(app.exec())
