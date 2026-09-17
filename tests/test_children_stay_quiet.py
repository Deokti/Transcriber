"""Дочерние процессы не открывают чёрных окон.

Настоящая ошибка: в установленной программе при подготовке звука рядом с
окном выскакивала консоль «D:\\ffmpeg\\bin\\ffmpeg.exe». У собранной программы
своей консоли нет, поэтому Windows заводит новую на каждый дочерний процесс.
Лечится ключом запуска, но его легко забыть: скрытие стояло у одного вызова
из пяти.

Поэтому проверяем не поведение одного места, а все вызовы в ядре сразу:
каждый запуск дочернего процесса должен идти с `**platform.quiet_child()`.

Исключение одно и осознанное — `open_file` и `reveal_file`: они как раз
должны показать человеку окно, проводник или просмотрщик.
"""
from __future__ import annotations

import ast
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

CORE = Path(__file__).resolve().parent.parent / "core"

#: Где окно дочернего процесса — это цель, а не помеха.
ALLOWED = {"open_file", "reveal_file"}


def spawns(tree: ast.AST):
    """Вызовы subprocess.run и subprocess.Popen вместе с именем функции."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr in ("run", "Popen")
                    and isinstance(inner.func.value, ast.Name)
                    and inner.func.value.id == "subprocess"):
                yield node.name, inner


def quiet(call: ast.Call) -> bool:
    """Передан ли `**platform.quiet_child()` среди именованных аргументов."""
    for keyword in call.keywords:
        if keyword.arg is not None:
            continue                      # обычный аргумент, не распаковка
        value = keyword.value
        if not isinstance(value, ast.Call):
            continue
        # Внутри самого platform.py зовут просто quiet_child(), снаружи — с именем модуля
        name = getattr(value.func, "attr", None) or getattr(value.func, "id", None)
        if name == "quiet_child":
            return True
    return False


def main() -> int:
    loud = []
    total = 0
    for path in sorted(CORE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for where, call in spawns(tree):
            total += 1
            mark = "тихо" if quiet(call) else "С ОКНОМ"
            if where in ALLOWED:
                mark = "показывает нарочно"
            elif not quiet(call):
                loud.append(f"{path.relative_to(CORE.parent)}:{call.lineno} ({where})")
            print(f"  {path.name}:{call.lineno} {where} — {mark}")

    print(f"всего запусков: {total}")
    if not total:
        print("ОШИБКА: не нашли ни одного запуска — тест перестал что-либо проверять")
        return 1
    if loud:
        print("ОШИБКА: эти вызовы откроют чёрное окно в собранной программе:")
        for line in loud:
            print("   ", line)
        return 1

    print("УСПЕХ: ни один вызов не открывает окно сам по себе")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
