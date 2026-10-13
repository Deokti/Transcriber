"""Пресеты: именованные наборы настроек задачи — «Лекция ru», «Интервью».

Ситуация из брифа: «надо то же самое, но для пяти файлов». Человек один
раз настраивает вид работы, сохраняет под именем и дальше выбирает его
одним щелчком, а не прощёлкивает шесть полей заново.

Лежат файлами в папке profiles, по одному на пресет, в том же виде, что
и `Profile.save`: такой файл можно отдать командной строке ключом
`--profile` или перенести на другую машину. Имя пресета хранится внутри
файла — имя файла из него только выводится, и в нём бывают замены.
"""
from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path
from typing import Any

from core.profile import Profile

#: Что в пресет не входит: это свойства конкретного файла или запуска, а не
#: вида работы. Дорожка своя у каждой записи, «считать заново» включают
#: на один раз, а шаг отчёта о ходе работы задаёт сам интерфейс.
PER_RUN = ("track", "force", "progress_step_min")

#: Знаки, которых не бывает в именах файлов на Windows, — и управляющие.
_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
#: Имена устройств Windows: файл «CON.json» не создаётся вовсе.
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
             *(f"lpt{i}" for i in range(1, 10))}

NAME_LIMIT = 80


def clean_name(name: str) -> str:
    """Имя пресета без лишних пробелов. Пустое — не имя."""
    return " ".join(str(name).split())[:NAME_LIMIT]


def file_name(name: str) -> str:
    """Имя файла для пресета: запрещённые знаки заменены, точки по краям убраны."""
    stem = _FORBIDDEN.sub("_", clean_name(name)).strip(" .")
    if not stem:
        raise ValueError("у пресета нет имени")
    if stem.lower() in _RESERVED:
        stem += "_"
    return stem + ".json"


def _read(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None          # битый или чужой файл в папке — просто не пресет
    return raw if isinstance(raw, dict) else None


def names(folder: Path) -> list[str]:
    """Имена пресетов по алфавиту."""
    if not folder.is_dir():
        return []
    found = []
    for path in folder.glob("*.json"):
        raw = _read(path)
        if raw is not None:
            found.append(clean_name(raw.get("name") or path.stem))
    return sorted(set(found), key=str.casefold)


def _path(name: str, folder: Path) -> Path:
    return folder / file_name(name)


def exists(name: str, folder: Path) -> bool:
    try:
        return _path(name, folder).is_file()
    except ValueError:
        return False


def values(profile: Profile) -> dict[str, Any]:
    """Настройки, которые входят в пресет."""
    return {k: v for k, v in profile.to_dict().items() if k not in PER_RUN}


def save(profile: Profile, name: str, folder: Path) -> Path:
    path = _path(name, folder)
    folder.mkdir(parents=True, exist_ok=True)
    data = {"name": clean_name(name), **values(profile)}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load(name: str, folder: Path) -> dict[str, Any]:
    """Настройки пресета — только известные поля и только те, что в него входят.

    Старый пресет мог не знать о поле, появившемся позже: тогда оно просто
    не приходит, и в профиле остаётся текущее значение.
    """
    raw = _read(_path(name, folder))
    if raw is None:
        raise FileNotFoundError(name)
    known = {f.name for f in fields(Profile)} - set(PER_RUN)
    return {k: v for k, v in raw.items() if k in known}


def remove(name: str, folder: Path) -> None:
    _path(name, folder).unlink(missing_ok=True)
