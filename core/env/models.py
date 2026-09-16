"""Каталог моделей распознавания.

Нужен ради одной вещи: модель, которая не знает языка записи, не должна быть
выбираемой. Иначе человек выберет английскую модель под русскую лекцию и
получит правдоподобную бессмыслицу, не поняв, почему.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.events import Cancelled, Code, CoreError

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

#: Из чего состоит модель. Ровно то, что берёт движок: лишнего не качаем.
FILES = ["config.json", "preprocessor_config.json", "model.bin",
         "tokenizer.json", "vocabulary.*"]


def repo(model_id: str) -> str:
    """Откуда качать. Карту держит сам движок, мы только спрашиваем."""
    try:
        from faster_whisper.utils import _MODELS

        known = _MODELS.get(model_id)
        if known:
            return known
    except Exception:
        pass
    return f"Systran/faster-whisper-{model_id}"


class _Silence:
    """Счётчику нужен файл для вывода, а консоли у нас нет."""

    def write(self, *args) -> None:
        pass

    def flush(self) -> None:
        pass


def _reporter(on_progress, should_cancel, expected: int):
    """Счётчик прогресса в том виде, в каком его ждёт huggingface_hub.

    Считать приходится аккуратно: библиотека заводит по счётчику на файл, а
    в новой схеме хранения — ещё и второй на «сборку» уже скачанного. Сложить
    всё подряд значит удвоить размер. Поэтому берём счётчики самой загрузки,
    а если их нет (старая схема) — складываем файловые.

    Знаменатель подпираем размером из каталога: в начале известен размер
    только первого файла, и без этого проценты прыгали бы от ста к десяти.
    """
    from tqdm import tqdm as _tqdm

    bars: dict = {}

    class Reporter(_tqdm):
        def __init__(self, *args, **kwargs):
            kwargs["file"] = _Silence()
            kwargs["leave"] = False
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            if should_cancel is not None and should_cancel():
                raise Cancelled(stage="download")
            result = super().update(n)
            if self.unit != "B":
                return result       # «Fetching 4 files» считает штуки, не байты
            bars[self] = ((self.desc or "").lower(), self.n, self.total or 0)
            if on_progress is not None:
                done, total = _sum(bars)
                on_progress(done, max(total, expected))
            return result

    return Reporter


def _sum(bars: dict) -> tuple[int, int]:
    rows = [row for row in bars.values() if "download" in row[0]] or list(bars.values())
    return sum(row[1] for row in rows), sum(row[2] for row in rows)


def download(model_id: str, models_dir, *, on_progress=None, should_cancel=None) -> str:
    """Качает модель и возвращает путь к ней.

    Отмена работает, но скачанное пока пропадает: обрыв не оставляет
    куска, с которого можно продолжить. Для полутора гигабайт это
    обидно, и докачка — задача этапа M4 вместе со своим загрузчиком.
    """
    import os
    from pathlib import Path

    import huggingface_hub

    entry = get(model_id)
    expected = int((entry.size_mb if entry else 0) * 1024 * 1024)

    # Новая схема хранения HuggingFace качает в своих потоках, и отмена до
    # них не доходит: закачка идёт дальше, как будто её не просили встать.
    # Старый путь встаёт честно — поэтому просим именно его.
    previous = os.environ.get("HF_HUB_DISABLE_XET")
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    try:
        return huggingface_hub.snapshot_download(
            repo(model_id),
            cache_dir=str(Path(models_dir)),
            allow_patterns=FILES,
            tqdm_class=_reporter(on_progress, should_cancel, expected),
            max_workers=4,
        )
    except Cancelled:
        raise
    except Exception as e:
        # Отмена может вернуться завёрнутой: библиотека качает в потоках.
        if _cancelled_inside(e):
            raise Cancelled(stage="download") from e
        raise CoreError(Code.DOWNLOAD_FAILED, model=model_id, reason=repr(e)) from e
    finally:
        if previous is None:
            os.environ.pop("HF_HUB_DISABLE_XET", None)
        else:
            os.environ["HF_HUB_DISABLE_XET"] = previous


def _cancelled_inside(error: BaseException) -> bool:
    seen = 0
    while error is not None and seen < 10:
        if isinstance(error, Cancelled):
            return True
        error = error.__cause__ or error.__context__
        seen += 1
    return False

