"""Панель хода работы не ниже того, что в ней лежит.

Ошибка: содержимое панели прибито якорями (`anchors.fill`), а якоря
размер родителю не задают. Панель — обычный прямоугольник, своей высоты у
неё нет, и она схлопнулась в ноль: имя файла, процент и полоса оказались
нарисованы поверх соседних панелей.

На глаз это видно сразу — но только если посмотреть, а посмотреть легко
забыть. Проверяем числом: панель не ниже своего содержимого.
"""
import sys

from PySide6.QtCore import QTimer

from harness import done, start

app, window, settings, i18n = start(theme="light", screen="progress")


def walk(item):
    """Обход по видимому дереву: содержимое панелей — не дети по QObject."""
    for child in item.childItems():
        yield child
        yield from walk(child)


def check() -> None:
    # Без отрисовки раскладки не посчитаны: Qt раскладывает элементы к
    # следующему кадру, а кадра без экрана может и не случиться.
    window.grabWindow()

    # Полосу прогресса узнаём по её собственному свойству: заводить
    # объектам имена ради теста — значит тащить тест в рабочий код.
    bar = next((item for item in walk(window.contentItem())
                if item.property("known") is not None), None)
    if bar is None:
        done(app, False, "полоса прогресса не найдена")
        return

    content = bar.parentItem()          # колонка с именем файла, процентом и полосой
    panel = content.parentItem()
    needed = content.property("implicitHeight")
    got = panel.property("height")
    print(f"содержимому нужно {needed:.0f} px, в панели {got:.0f} px")

    ok = got >= needed > 0
    done(app, ok, "панель вмещает содержимое" if ok
         else f"панель ниже содержимого: {got:.0f} < {needed:.0f}")


QTimer.singleShot(400, check)
sys.exit(app.exec())
