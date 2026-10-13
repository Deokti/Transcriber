"""Каталоги переводов целы и совпадают друг с другом и с разметкой.

Ошибка: при очередном пополнении каталогов en.json сломался на кавычке и
перестал быть JSON. Окно этого не показывает: битый каталог читается как
пустой, и всё, чего нет, добирается из русского. Человек с английским
интерфейсом видел бы русские надписи и не понимал почему, а разработчик —
ничего, пока не переключит язык. Тем же путём молча расходятся каталоги,
когда ключи добавляются десятками в два файла руками.

Проверяем: оба каталога читаются; ключи одинаковые; у каждой строки одни
и те же подстановки %1, %2 и одинаковое число форм через «|»; каждый ключ,
который разметка называет прямо, есть в обоих каталогах.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGS = ROOT / "app" / "i18n"
QML = ROOT / "app" / "qml"

# Иначе русский вывод рассыпается: консоль Windows отдаёт свою кодировку
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

#: Ключ, названный в разметке целиком: I18n.strings["…"] или Fmt.tr("…", …).
#: Ключи, собранные из приставки и кода («notice.» + code), сюда не попадают —
#: их набор задаёт ядро, а не разметка.
STATIC = re.compile(r'(?:I18n\.strings\[|\btr\()\s*"([A-Za-z0-9_.-]+)"\s*[\],]')


def main() -> int:
    problems: list[str] = []
    catalogs: dict[str, dict] = {}
    for path in sorted(CATALOGS.glob("*.json")):
        try:
            catalogs[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            problems.append(f"{path.name} не читается: {error}")
    if len(catalogs) < 2:
        problems.append(f"каталогов прочитано: {len(catalogs)}, а ждали хотя бы два")

    names = sorted(catalogs)
    for other in names[1:]:
        first = names[0]
        only_first = sorted(set(catalogs[first]) - set(catalogs[other]))
        only_other = sorted(set(catalogs[other]) - set(catalogs[first]))
        if only_first:
            problems.append(f"есть в {first}, нет в {other}: {', '.join(only_first[:10])}")
        if only_other:
            problems.append(f"есть в {other}, нет в {first}: {', '.join(only_other[:10])}")
        for key in sorted(set(catalogs[first]) & set(catalogs[other])):
            a, b = str(catalogs[first][key]), str(catalogs[other][key])
            if sorted(set(re.findall(r"%\d", a))) != sorted(set(re.findall(r"%\d", b))):
                problems.append(f"{key}: подстановки не совпадают ({first} и {other})")
            if a.count("|") != b.count("|"):
                problems.append(f"{key}: разное число форм через «|» ({first} и {other})")

    used: dict[str, str] = {}
    for path in QML.rglob("*.qml"):
        for match in STATIC.finditer(path.read_text(encoding="utf-8")):
            used.setdefault(match.group(1), path.name)
    for key, where in sorted(used.items()):
        absent = [code for code in names if key not in catalogs[code]]
        if absent:
            problems.append(f"{where} просит «{key}», а в {', '.join(absent)} его нет")

    if problems:
        print("ПРОВАЛ: каталоги переводов разошлись")
        for line in problems[:30]:
            print("   ", line)
        return 1
    print(f"УСПЕХ: каталогов {len(names)}, в каждом {len(catalogs[names[0]])} строк, "
          f"разметка называет {len(used)} ключей — все на месте")
    return 0


if __name__ == "__main__":
    sys.exit(main())
