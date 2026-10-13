"""Секунды в человеческий вид. Используется и ядром, и интерфейсом."""
from __future__ import annotations


def stamp(seconds: float, comma: bool = False) -> str:
    """ЧЧ:ММ:СС.ммм — как в транскрипте. С запятой — как в субтитрах SRT.

    Считаем в целых миллисекундах: через дробные секунды 59.9996 округлялось
    в «00:00:60.000», а такую строку проигрыватель субтитров не примет.
    """
    total = max(0, round(float(seconds) * 1000))
    hours, rest = divmod(total, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{',' if comma else '.'}{millis:03d}"


def hms(seconds: float) -> str:
    """ЧЧ:ММ:СС — для длительностей."""
    seconds = max(0.0, float(seconds))
    return f"{int(seconds // 3600):02d}:{int(seconds % 3600 // 60):02d}:{int(seconds % 60):02d}"
