"""Настройки приложения — то, что не зависит от конкретной задачи.

Отличие от Profile: профиль описывает, как обработать файл, а настройки —
где живут модели и программы на этой машине. Профилей бывает много,
настройки одни.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from core import platform

FILE_NAME = "settings.json"


@dataclass
class Settings:
    """Пути и общие предпочтения. Пустая строка значит «как обычно»."""

    #: Куда складывать модели. Пусто — папка данных приложения.
    #: Пригождается, когда на системном диске нет места под несколько гигабайт
    #: или когда модели уже скачаны другим инструментом.
    models_dir: str = ""

    #: Где искать ffmpeg, если его нет ни в папке данных, ни в PATH.
    ffmpeg_dir: str = ""

    #: Куда по умолчанию класть готовые документы. Пусто — рядом с исходником.
    output_dir: str = ""

    #: Язык интерфейса. Ядром не используется, хранится здесь ради одного места.
    ui_language: str = "ru"

    #: Тема: system — как в системе, иначе light или dark.
    theme: str = "system"

    @classmethod
    def path(cls) -> Path:
        return platform.data_dir() / FILE_NAME

    @classmethod
    def load(cls) -> "Settings":
        path = cls.path()
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()   # испорченный файл не повод не запуститься
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self) -> Path:
        path = self.path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def resolve_models_dir(self) -> Path:
        return Path(self.models_dir).expanduser() if self.models_dir else platform.paths().models

    def resolve_output_dir(self) -> Path | None:
        """None означает «рядом с исходным файлом»."""
        return Path(self.output_dir).expanduser() if self.output_dir else None

    def extra_tool_dirs(self) -> list[Path]:
        dirs = [platform.paths().bin]
        if self.ffmpeg_dir:
            dirs.insert(0, Path(self.ffmpeg_dir).expanduser())
        return dirs

    def as_data(self) -> dict[str, Any]:
        return asdict(self)
