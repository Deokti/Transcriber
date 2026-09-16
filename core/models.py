"""Каталог моделей распознавания.

Нужен ради одной вещи: модель, которая не знает языка записи, не должна быть
выбираемой. Иначе человек выберет английскую модель под русскую лекцию и
получит правдоподобную бессмыслицу, не поняв, почему.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Модель понимает все 99 языков Whisper.
MULTILINGUAL = "multi"
#: Модель понимает только английский.
ENGLISH_ONLY = "en"


@dataclass(frozen=True)
class ModelInfo:
    id: str            # то, что уходит в движок
    size_mb: int       # примерный размер загрузки
    languages: str     # MULTILINGUAL | ENGLISH_ONLY
    speed: float       # во сколько раз быстрее large-v3, грубо
    quality: int       # 1 худшее … 5 лучшее

    @property
    def multilingual(self) -> bool:
        return self.languages == MULTILINGUAL

    def supports(self, language: str) -> bool:
        if self.multilingual:
            return True
        return (language or "").lower() in ("en", "english", "auto", "")

    def as_data(self) -> dict:
        return {"id": self.id, "size_mb": self.size_mb, "languages": self.languages,
                "speed": self.speed, "quality": self.quality}


CATALOG: tuple[ModelInfo, ...] = (
    ModelInfo("tiny", 75, MULTILINGUAL, 30.0, 1),
    ModelInfo("base", 145, MULTILINGUAL, 16.0, 2),
    ModelInfo("small", 484, MULTILINGUAL, 6.0, 3),
    ModelInfo("medium", 1530, MULTILINGUAL, 2.5, 4),
    ModelInfo("large-v3", 3090, MULTILINGUAL, 1.0, 5),
    ModelInfo("large-v3-turbo", 1620, MULTILINGUAL, 4.0, 4),
    ModelInfo("distil-large-v3", 1510, ENGLISH_ONLY, 5.0, 4),
)

_BY_ID = {m.id: m for m in CATALOG}


def get(model_id: str) -> ModelInfo | None:
    """Сведения о модели или None, если это свой путь или неизвестное имя."""
    return _BY_ID.get(model_id)


def supports(model_id: str, language: str) -> bool:
    """Незнакомые модели считаем пригодными: человек указал путь сам."""
    info = get(model_id)
    return True if info is None else info.supports(language)


def for_language(language: str) -> list[ModelInfo]:
    return [m for m in CATALOG if m.supports(language)]


def is_downloaded(model_id: str, models_dir) -> bool:
    """Лежит ли модель на диске.

    Ищем и свою папку, и кеш HuggingFace — папку моделей можно указать
    на уже скачанные (решение про models_dir в настройках).
    """
    from pathlib import Path

    root = Path(models_dir)
    if not root.is_dir():
        return False
    if (root / model_id).is_dir():
        return True
    needle = model_id.lower()
    for child in root.iterdir():
        name = child.name.lower()
        if not child.is_dir() or not name.startswith("models--"):
            continue
        # models--Systran--faster-whisper-large-v3 -> large-v3
        if name.endswith("--" + needle) or name.endswith("-" + needle):
            return any(child.rglob("model.bin"))
    return False


def as_data() -> list[dict]:
    """Каталог целиком — для интерфейса, который сам решит, что показать."""
    return [m.as_data() for m in CATALOG]
