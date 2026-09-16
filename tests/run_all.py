"""Прогоняет все тесты интерфейса.

  python tests/run_all.py

Каждый тест — отдельный процесс: приложение Qt в процессе может быть только
одно. Окно рисуется без экрана, так что ничего не мелькает и тесты можно
гонять параллельно с работой.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(HERE))
    tests = sorted(HERE.glob("test_*.py"))
    if not tests:
        print("Тестов не найдено.")
        return 1

    failed = []
    for path in tests:
        print(f"\n=== {path.name} " + "=" * max(0, 60 - len(path.name)))
        result = subprocess.run([sys.executable, str(path)], env=env)
        if result.returncode != 0:
            failed.append(path.name)

    print("\n" + "=" * 66)
    if failed:
        print(f"Провалено {len(failed)} из {len(tests)}: " + ", ".join(failed))
        return 1
    word = "тест прошёл" if len(tests) == 1 else "теста прошли"
    print(f"Все {len(tests)} {word}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
