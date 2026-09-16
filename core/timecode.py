"""Секунды в человеческий вид. Используется и ядром, и интерфейсом."""
from __future__ import annotations


def stamp(seconds: float, comma: bool = False) -> str:
    """ЧЧ:ММ:СС.ммм — как в транскрипте. С запятой — как в субтитрах."""
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    out = f"{h:02d}:{m:02d}:{s:06.3f}"
    return out.replace(".", ",") if comma else out


def hms(seconds: float) -> str:
    """ЧЧ:ММ:СС — для длительностей."""
    seconds = max(0.0, float(seconds))
    return f"{int(seconds // 3600):02d}:{int(seconds % 3600 // 60):02d}:{int(seconds % 60):02d}"
