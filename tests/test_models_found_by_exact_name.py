"""Модель ищется по точному имени, а не по хвосту папки.

Ошибка: в кеше HuggingFace папка модели называется по её хранилищу —
`models--Systran--faster-whisper-large-v3`. Мы искали её по хвосту имени,
и «large-v3» совпадал заодно с `faster-distil-whisper-large-v3`. Скачана
только distil — программа считала скачанной large-v3 и открывала вместо неё
другую модель. А саму distil-large-v3 не находила никогда: в имени её папки
написано «distil-whisper», а не «-distil-large-v3».

Для экрана «Хранилище» это особенно важно: удаление идёт по той же папке.

Папки поддельные, с файлами нужных имён — содержимое значения не имеет.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core.env import models


def fake(root: Path, repo: str) -> None:
    """Гнездо кеша HuggingFace с полным слепком."""
    snapshot = root / ("models--" + repo.replace("/", "--")) / "snapshots" / "abc"
    snapshot.mkdir(parents=True)
    for part in models.NEEDED:
        (snapshot / part).write_bytes(b"{}")


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="transcriber-names-"))
    fake(root, models.repo("distil-large-v3"))        # скачана только distil

    distil = models.is_downloaded("distil-large-v3", root)
    large = models.is_downloaded("large-v3", root)
    print("скачана только distil-large-v3")
    print("  distil-large-v3 найдена:", distil)
    print("  large-v3 найдена:       ", large)

    problems = []
    if large:
        problems.append("large-v3 принята за скачанную — откроется distil вместо неё")
    if not distil:
        problems.append("distil-large-v3 не найдена, хотя лежит на диске")
    if models.nest("large-v3", root) is not None:
        problems.append("гнездо large-v3 указывает на чужую папку — удаление снесёт distil")

    if problems:
        print("ПРОВАЛ:", "; ".join(problems))
        return 1
    print("УСПЕХ: каждая модель находит ровно свою папку")
    return 0


if __name__ == "__main__":
    sys.exit(main())
