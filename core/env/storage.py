"""Что программа держит на диске и сколько это весит (FR-25, решение D-5).

Отвечает экрану «Хранилище»: что скачано, сколько занимает, что можно
удалить. Удалять умеет только своё: модели из каталога, ffmpeg из своей
папки, временные файлы и журналы. Папка моделей бывает общей — кешем
HuggingFace, где лежат модели других программ, — и чужое мы не трогаем
никогда: удаление идёт по точному имени гнезда модели из каталога.

Человеческих слов здесь нет: ядро отдаёт виды, коды и байты (принцип П-1).
"""
from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path

from core.env import models
from core.platform import Paths

#: Состояния модели на диске.
ABSENT = "absent"        # нет вовсе
READY = "ready"          # лежит целиком, движок откроет
PARTIAL = "partial"      # загрузка оборвалась: место занято, открыть нельзя


@dataclass(frozen=True)
class ModelOnDisk:
    id: str
    state: str
    bytes: int           # сколько занимает на диске сейчас
    path: str            # гнездо модели, "" — если её нет


def size_of(path: Path) -> int:
    """Сколько файлы под path занимают на диске.

    Ссылки не считаем: в кеше HuggingFace слепок модели — это ссылки на
    блобы, и через ссылки тот же гигабайт посчитался бы дважды.
    """
    if not path.exists():
        return 0
    if path.is_file():
        return 0 if path.is_symlink() else path.stat().st_size
    total = 0
    for root, _dirs, files in os.walk(path):     # по ссылкам на папки walk не ходит
        for name in files:
            full = Path(root) / name
            try:
                if not full.is_symlink():
                    total += full.stat().st_size
            except OSError:
                pass     # файл исчез между обходом и замером — не наш вопрос
    return total


def models_on_disk(models_dir) -> list[ModelOnDisk]:
    """Каждая модель каталога: есть ли, целиком ли и сколько весит."""
    result = []
    for entry in models.CATALOG:
        home = models.nest(entry.id, models_dir)
        if home is None:
            result.append(ModelOnDisk(entry.id, ABSENT, 0, ""))
            continue
        state = READY if models.local_dir(entry.id, models_dir) is not None else PARTIAL
        result.append(ModelOnDisk(entry.id, state, size_of(home), str(home)))
    return result


def foreign_models(models_dir) -> int:
    """Сколько в папке моделей чужих гнёзд — значит, папка общая."""
    root = Path(models_dir)
    if not root.is_dir():
        return 0
    ours = {f"models--{models.repo(m.id).replace('/', '--')}" for m in models.CATALOG}
    return sum(1 for child in root.iterdir()
               if child.is_dir() and child.name.startswith("models--") and child.name not in ours)


def remove_model(model_id: str, models_dir) -> int:
    """Удаляет модель целиком, вместе с блобами. Возвращает освобождённые байты.

    Только гнездо модели из каталога и только внутри папки моделей: путь
    проверяется ещё раз прямо перед удалением, хотя строится он сам.
    """
    if models.get(model_id) is None:
        raise ValueError(f"модели {model_id!r} нет в каталоге")
    home = models.nest(model_id, models_dir)
    if home is None:
        return 0
    root = Path(models_dir).resolve()
    if root not in home.resolve().parents:
        raise ValueError(f"{home} лежит вне папки моделей")
    freed = size_of(home)
    _rmtree(home)
    return freed


def clear(folder: Path, paths: Paths) -> int:
    """Очищает свою служебную папку — временные файлы, журналы, ffmpeg.

    Саму папку оставляем: программа рассчитывает, что она есть. Чистить
    разрешено только папки из Paths — чтобы ошибка в вызове не обернулась
    удалением чего-нибудь большего.
    """
    allowed = {paths.temp.resolve(), paths.logs.resolve(), paths.bin.resolve()}
    if folder.resolve() not in allowed:
        raise ValueError(f"{folder} — не служебная папка программы")
    freed = size_of(folder)
    for child in folder.iterdir():
        if child.is_dir() and not child.is_symlink():
            _rmtree(child)
        else:
            child.unlink(missing_ok=True)
    return freed


def _rmtree(path: Path) -> None:
    """rmtree, который не спотыкается о файлы «только для чтения» на Windows."""
    def retry(func, target, _info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onexc=retry)
