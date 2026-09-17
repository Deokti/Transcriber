"""Дозированные отчёты о ходе работы и оценка оставшегося времени.

Одна и та же арифметика жила в четырёх местах — подготовка звука, второй
проход за звуком, распознавание, скачивание модели — и в каждом со своим
словарём `last = {"at": ...}`. Здесь она в одном, с именем.
"""
from __future__ import annotations

import time


class Pace:
    """Отчитываться не чаще, чем раз в `step` единиц позиции.

    Позиция — то, в чём меряется работа: секунды звука, байты, секунды
    ожидания. Первый отчёт проходит всегда.
    """

    #: Доля сделанного, ниже которой оценка остатка — гадание, а не оценка.
    FLOOR = 0.02

    def __init__(self, step: float) -> None:
        self.step = step
        self.started = time.monotonic()
        self._last = float("-inf")

    def due(self, position: float) -> bool:
        """Пора ли: позиция ушла от прошлого отчёта хотя бы на шаг."""
        if position - self._last < self.step:
            return False
        self._last = position
        return True

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def eta(self, done: float) -> float:
        """Сколько ещё ждать при доле сделанного `done` от 0 до 1."""
        if done <= self.FLOOR:
            return 0.0
        return self.elapsed() / done * (1 - done)
