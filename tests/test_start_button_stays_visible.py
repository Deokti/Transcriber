"""Кнопка «Запустить» не уезжает за край окна.

Ошибка: рабочая область главного экрана росла как получится, а подвал
с кнопкой шёл следом. При низком окне содержимое переставало помещаться
и выталкивало подвал за край: кнопка, ради которой всё и затевалось,
оказывалась недоступна. Хуже всего, что минимальная высота окна (620 px)
разрешена самой программой — то есть человек мог довести до этого сам,
просто уменьшив окно.

Раскрытая панель «Дополнительно» добавляет к содержимому полторы сотни
точек и делает то же самое даже в обычном окне.

Лечится прокруткой: содержимое прокручивается, подвал остаётся на месте.
Проверяем оба случая числом — нижний край кнопки против высоты окна.
"""
import sys

from PySide6.QtCore import QTimer

from harness import done, start

app, window, settings, i18n = start(theme="light", screen="main")



def walk(item):
    """Обход по видимому дереву: содержимое панелей — не дети по QObject."""
    for child in item.childItems():
        yield child
        yield from walk(child)


def bottom(item) -> float:
    """Нижний край в координатах окна."""
    y, node = 0.0, item
    while node is not None and node != window.contentItem():
        y += node.property("y")
        node = node.parentItem()
    return y + item.property("height")


def find_button():
    """Главная кнопка подвала.

    Ищем по свойству, а не по надписи: та меняется вместе с состоянием
    очереди и языком интерфейса. Главных кнопок на экране две — «Выбрать
    файлы» в пустой области и «Запустить» в подвале; нужна нижняя.
    """
    buttons = [item for item in walk(window.contentItem())
               if item.property("primary") is True]
    return max(buttons, key=bottom) if buttons else None


def find_panel():
    """Панель «Дополнительно» узнаём по её собственному свойству."""
    return next((item for item in walk(window.contentItem())
                 if item.property("open") is not None), None)


def settle() -> None:
    # Без отрисовки раскладки не посчитаны: Qt раскладывает элементы
    # к следующему кадру, а кадра без экрана может и не случиться.
    for _ in range(3):
        window.grabWindow()


def check() -> None:
    settle()
    panel = find_panel()
    if panel is None or find_button() is None:
        done(app, False, "не нашёл кнопку «Запустить» или панель «Дополнительно»")
        return

    problems = []
    for height, open_panel, label in ((720, False, "обычное окно"),
                                      (620, False, "минимальная высота окна"),
                                      (720, True, "обычное окно, панель раскрыта"),
                                      (620, True, "минимум и раскрытая панель")):
        # Меняем высоту области содержимого, а не окна: без экрана система
        # не присылает окну событие изменения размера, и раскладка осталась
        # бы прежней — замер показывал бы выдуманные числа.
        window.contentItem().setProperty("height", height)
        panel.setProperty("open", open_panel)
        settle()
        edge = bottom(find_button())
        room = height - edge
        print(f"{label:34} высота {height} px, "
              f"низ кнопки {edge:.0f} px, запас {room:.0f} px")
        if room < 0:
            problems.append(label)

    done(app, not problems,
         "кнопка «Запустить» уехала за край: " + ", ".join(problems) if problems
         else "кнопка «Запустить» на месте при любой высоте окна")


QTimer.singleShot(700, check)
sys.exit(app.exec())
