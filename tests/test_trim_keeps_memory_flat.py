"""Обрезка тишины по краям не разворачивает всю запись в памяти.

Ошибка из ревью ядра. Тишину в конце срезал тот же фильтр, что и в начале,
только на развёрнутом звуке: два areverse. Разворот держит всю запись в
памяти — на часовой лекции ffmpeg брал 340 МБ, на трёхчасовой брал бы под
гигабайт, и всё это ради трёх секунд тишины в конце.

Теперь отдельный проход только слушает, где тишина, а обрезка делается
диапазоном при извлечении — потоком, с плоской памятью.

Проверяем на записи в двадцать минут с тишиной по краям: результат должен
стать короче ровно на края, а пик памяти ffmpeg — остаться маленьким.
Пик памяти читается через WinAPI по описателю процесса, который Popen
держит открытым; на других системах эта часть пропускается.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core import media
from core.media import ensure_tools, extract_audio

MINUTES = 20
LEAD, TAIL = 2.0, 3.0            # тишина по краям, секунды
PEAK_LIMIT_MB = 60               # старый приём брал здесь больше ста


def peak_mb(proc: subprocess.Popen) -> float | None:
    if sys.platform != "win32":
        return None
    import ctypes
    import ctypes.wintypes as wt

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(int(proc._handle),
                                                  ctypes.byref(counters), counters.cb)
    return counters.PeakWorkingSetSize / 1024 / 1024 if ok else None


def main() -> int:
    tools = ensure_tools([])
    folder = Path(tempfile.mkdtemp(prefix="transcriber-trim-"))
    source = folder / "лекция.wav"
    speech = MINUTES * 60 - LEAD - TAIL
    subprocess.run([str(tools.ffmpeg), "-v", "quiet", "-y", "-f", "lavfi", "-i",
                    f"aevalsrc=0:d={LEAD}[a];sine=frequency=300:duration={speech}[b];"
                    f"aevalsrc=0:d={TAIL}[c];[a][b][c]concat=n=3:v=0:a=1",
                    "-ar", "16000", "-ac", "1", str(source)], check=True)

    children: list[subprocess.Popen] = []
    real = media.subprocess.Popen

    def spy(*args, **kwargs):
        proc = real(*args, **kwargs)
        children.append(proc)
        return proc

    media.subprocess.Popen = spy
    out = folder / "готово.wav"
    started = time.monotonic()
    try:
        extract_audio(tools.ffmpeg, source, out, trim_silence=True, loudnorm=False,
                      duration=MINUTES * 60)
    finally:
        media.subprocess.Popen = real
    spent = time.monotonic() - started

    probe = subprocess.run([str(tools.ffprobe), "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True)
    got = float(probe.stdout or 0)
    peaks = [peak_mb(proc) for proc in children]
    worst = max((p for p in peaks if p is not None), default=None)
    print(f"длительность: было {MINUTES * 60:.0f} с, стало {got:.1f} с (речь {speech:.0f} с)")
    print(f"процессов ffmpeg: {len(children)} | время: {spent:.1f} с | "
          f"пик памяти: {worst if worst is None else round(worst)} МБ")

    if abs(got - speech) > 0.5:
        print("ОШИБКА: края обрезаны не там, где тишина")
        return 1
    if worst is not None and worst > PEAK_LIMIT_MB:
        print(f"ОШИБКА: ffmpeg держит запись в памяти — {worst:.0f} МБ на {MINUTES} минут")
        return 1

    print("УСПЕХ: края срезаны, память плоская")
    return 0


if __name__ == "__main__":
    sys.exit(main())
