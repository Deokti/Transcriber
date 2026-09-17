"""Проверка транскрипта на залипания модели.

Whisper на тишине или шуме умеет зациклиться и повторять одну фразу часами —
это болезнь, ради которой и затевался проект. Здесь она ловится числами,
без чтения текста целиком.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from core.asr.base import Segment
from core.events import Code

#: Серия одинаковых строк, начиная с которой это уже не речь.
RUN_THRESHOLD = 3
#: Сколько секунд повторов делают вердикт плохим.
STUCK_SECONDS = 60
#: Серия такой длины — залипание независимо от времени.
STUCK_RUN = 10
#: Тишина длиннее этого считается дырой в таймлайне.
GAP_SECONDS = 120
#: Окно для поиска циклов вида ABAB.
NEAR_WINDOW = 5

_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Строки сравниваем без знаков и регистра: «Да!» и «да» — одно и то же."""
    return _SPACES.sub(" ", _PUNCT.sub("", text.strip().lower()))


@dataclass
class Run:
    count: int
    start: float
    end: float
    text: str

    @property
    def seconds(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class Report:
    """Результат проверки. Вердикт — код, а не фраза (принцип П-1)."""

    lines: int = 0
    end: float = 0.0
    speech: float = 0.0
    empty: int = 0
    max_run: int = 0
    bad_runs: list[Run] = field(default_factory=list)
    repeat_seconds: float = 0.0
    repeat_share: float = 0.0
    near_repeats: int = 0
    gaps: list[tuple[float, float]] = field(default_factory=list)
    top: list[tuple[str, int]] = field(default_factory=list)
    verdict: str = Code.QUALITY_CLEAN

    def as_data(self) -> dict:
        """Машинное представление для события."""
        return {
            "lines": self.lines,
            "end": round(self.end, 2),
            "speech": round(self.speech, 2),
            "empty": self.empty,
            "max_run": self.max_run,
            "bad_runs": [{"count": r.count, "start": round(r.start, 1),
                          "end": round(r.end, 1), "text": r.text[:80]}
                         for r in self.bad_runs[:5]],
            "repeat_seconds": round(self.repeat_seconds, 1),
            "repeat_share": round(self.repeat_share, 1),
            "near_repeats": self.near_repeats,
            "gaps": [(round(a, 1), round(b, 1)) for a, b in self.gaps[:5]],
            "gaps_total": len(self.gaps),
            "top": self.top,
        }


def analyze(segments: list[Segment]) -> Report | None:
    """Считает метрики и выносит вердикт. None — если считать нечего."""
    if not segments:
        return None

    report = Report(lines=len(segments), end=segments[-1].end)
    report.speech = sum(s.end - s.start for s in segments)
    report.empty = sum(1 for s in segments if len(s.text.strip()) < 2)
    keys = [normalize(s.text) for s in segments]   # один раз, а не в каждом цикле

    # серии подряд идущих одинаковых строк
    runs: list[Run] = []
    i = 0
    while i < len(segments):
        j = i
        while j + 1 < len(segments) and keys[j + 1] == keys[i]:
            j += 1
        runs.append(Run(j - i + 1, segments[i].start, segments[j].end, segments[i].text))
        i = j + 1

    report.max_run = max(r.count for r in runs)
    report.bad_runs = sorted((r for r in runs if r.count >= RUN_THRESHOLD),
                             key=lambda r: -r.seconds)
    report.repeat_seconds = sum(r.seconds for r in report.bad_runs)
    report.repeat_share = 100 * report.repeat_seconds / max(report.end, 1)

    # повтор строки в окне из нескольких предыдущих — ловит циклы вида ABAB
    window: list[str] = []
    for key in keys:
        if key and key in window:
            report.near_repeats += 1
        window = [*window, key][-NEAR_WINDOW:]

    report.gaps = [(segments[i].end, segments[i + 1].start)
                   for i in range(len(segments) - 1)
                   if segments[i + 1].start - segments[i].end > GAP_SECONDS]

    report.top = Counter(key for key in keys if key).most_common(5)

    if report.repeat_seconds > STUCK_SECONDS or report.max_run >= STUCK_RUN:
        report.verdict = Code.QUALITY_STUCK
    elif report.bad_runs or report.near_repeats:
        report.verdict = Code.QUALITY_MINOR
    else:
        report.verdict = Code.QUALITY_CLEAN
    return report
