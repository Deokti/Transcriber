"""Нарисованные значки должны перекрашиваться вместе с темой.

Меряем не абсолютную яркость — она зависит от фона, — а отношение галочки
к заливке флажка: в тёмной теме галочка темнее заливки, в светлой светлее.
Так тест не развалится, если поменяются сами цвета.
"""
import sys

from PySide6.QtCore import QTimer

from harness import done, luminance, start

#: Где-то здесь флажок «Выровнять громкость» на главном экране.
AREA = (20, 320, 60, 360)

app, window, settings, i18n = start(theme="dark", language="ru")


def measure(tag: str) -> tuple[float, float]:
    """Находит заливку флажка по цвету и сравнивает с ней цвет галочки."""
    image = window.grabWindow()
    x0, y0, x1, y1 = AREA
    points = [(x, y, image.pixelColor(x, y))
              for x in range(x0, x1) for y in range(y0, y1)]

    # Заливка — насыщенный оранжевый: красного заметно больше синего.
    # Ни фон, ни текст такого не дают.
    fill = [(x, y, c) for x, y, c in points if c.red() - c.blue() > 40]
    assert fill, f"{tag}: флажок не найден, проверьте координаты"
    fill_lum = sum(luminance(c) for _, _, c in fill) / len(fill)

    xs = [x for x, _, _ in fill]
    ys = [y for _, y, _ in fill]
    inside = [c for x, y, c in points
              if min(xs) + 2 <= x <= max(xs) - 2 and min(ys) + 2 <= y <= max(ys) - 2]
    mark = [c for c in inside if abs(luminance(c) - fill_lum) > 25]
    assert mark, f"{tag}: галочка внутри флажка не найдена"
    mark_lum = sum(luminance(c) for c in mark) / len(mark)

    print(f"{tag}: заливка {fill_lum:.0f}, галочка {mark_lum:.0f} — "
          f"{'светлее' if mark_lum > fill_lum else 'темнее'}")
    return fill_lum, mark_lum


def on_dark():
    dark = measure("тёмная тема ")
    settings.setTheme("light")
    QTimer.singleShot(400, lambda: on_light(dark))


def on_light(dark: tuple[float, float]):
    light = measure("светлая тема")
    if dark[1] >= dark[0]:
        done(app, False, "в тёмной теме галочка не темнее заливки")
    elif light[1] <= light[0]:
        done(app, False, "в светлой теме галочка не светлее заливки")
    else:
        done(app, True, "значки следуют за темой")


QTimer.singleShot(700, on_dark)
sys.exit(app.exec())
