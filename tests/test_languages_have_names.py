"""У каждого языка записи есть название в обоих каталогах.

Ошибка: названия были только у пятнадцати частых языков, а остальные
восемьдесят пять движок отдаёт кодами — и в списке «Язык записи» после
«Казахского» шли голые «fo», «fi», «et». Человеку код ни о чём не говорит,
и выглядит это как недоделка.

Проверяем: для каждого кода, который знает движок, в каждом каталоге есть
строка lang.<код>.
"""
import json
import sys
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core.env import languages

CATALOGS = Path(__file__).resolve().parent.parent / "app" / "i18n"


def main() -> int:
    codes = languages.codes()
    problems = []
    for path in sorted(CATALOGS.glob("*.json")):
        catalog = json.loads(path.read_text(encoding="utf-8"))
        missing = [c for c in codes if not catalog.get(f"lang.{c}")]
        if missing:
            problems.append(f"{path.name}: нет названий для {', '.join(missing[:12])}"
                            + (f" и ещё {len(missing) - 12}" if len(missing) > 12 else ""))
    if problems:
        print("ПРОВАЛ: языки без названий — " + "; ".join(problems))
        return 1
    print(f"УСПЕХ: у всех {len(codes)} языков есть названия в каждом каталоге")
    return 0


if __name__ == "__main__":
    sys.exit(main())
