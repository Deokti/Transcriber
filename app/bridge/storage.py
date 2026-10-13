"""Хранилище: что программа держит на диске, сколько весит, что удалить.

Подсчёт быстрый — в гнезде модели десяток файлов, — поэтому делается прямо
в потоке окна, по требованию. Скачивание модели долгое и идёт в рабочем
потоке, ответ приходит сигналом: те же грабли, что и с ffmpeg.

Удалять модель, пока идёт работа, нельзя: движок держит её открытой, и
работа упала бы на полуслове. Мост проверяет это сам, не полагаясь на то,
что окно выключит кнопку.

Слов здесь нет: наружу уходят коды и числа (принцип П-1).
"""
from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QRunnable, QThreadPool, Signal, Slot

from app.bridge.env import EnvBridge
from app.bridge.settings import SettingsBridge
from core import platform
from core.env import models, storage
from core.events import Cancelled, Code, CoreError
from core.media import find_tool


class _Signals(QObject):
    progress = Signal(float, float)
    done = Signal(object)          # None или CoreError


class _Download(QRunnable):
    def __init__(self, model_id: str, models_dir, signals: _Signals, cancelled) -> None:
        super().__init__()
        self._model_id = model_id
        self._models_dir = models_dir
        self._signals = signals
        self._cancelled = cancelled

    def run(self) -> None:
        try:
            models.download(self._model_id, self._models_dir,
                            on_progress=self._say, should_cancel=self._cancelled)
            self._finish(None)
        except Cancelled:
            self._finish(CoreError(Code.CANCELLED))
        except CoreError as error:
            self._finish(error)
        except Exception as error:      # диск, права — всё сюда
            self._finish(CoreError(Code.DOWNLOAD_FAILED, reason=repr(error)))

    def _say(self, done: int, total: int) -> None:
        try:
            self._signals.progress.emit(float(done), float(total))
        except RuntimeError:
            pass

    def _finish(self, result) -> None:
        try:
            self._signals.done.emit(result)
        except RuntimeError:
            pass    # окно закрыли, слушать некому


def _date(path: str | Path) -> str:
    """Когда файл появился на диске — для строки «скачана 12 сентября»."""
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime).isoformat()
    except OSError:
        return ""


class StorageBridge(QObject):
    changed = Signal()

    def __init__(self, settings: SettingsBridge, env: EnvBridge,
                 working: Callable[[], bool] = lambda: False,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._env = env
        self._working = working          # идёт ли сейчас работа — тогда не удаляем
        self._data: dict = {}
        self._downloading = ""
        self._done = 0.0
        self._total = 0.0
        self._speed = 0.0
        self._mark = (0.0, 0.0)          # момент и байты прошлого замера скорости
        self._error: dict = {}
        self._stop = False
        self._drop = False               # «Отменить» — обрывок не нужен, в отличие от паузы
        self._signals = _Signals()       # без родителя: переживает мост
        self._signals.progress.connect(self._on_progress)
        self._signals.done.connect(self._on_done)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

    # --- опрос -----------------------------------------------------------
    @Slot()
    def refresh(self) -> None:
        raw = self._settings.raw
        paths = platform.paths().ensure()
        models_dir = raw.resolve_models_dir()

        catalog = {m.id: m for m in models.CATALOG}
        rows = []
        for item in storage.models_on_disk(models_dir):
            info = catalog[item.id]
            rows.append({"id": item.id, "state": item.state, "bytes": float(item.bytes),
                         "sizeMb": info.size_mb, "multilingual": info.multilingual,
                         "date": _date(item.path) if item.path else "",
                         # откуда качать — чтобы подсказать адрес для ручной загрузки
                         "repo": models.repo(item.id),
                         "home": str(Path(models_dir) / item.id)})

        # ffmpeg считаем своим, только если он лежит в нашей папке: системный
        # ставил человек, и удалять его не нам.
        tool = find_tool("ffmpeg", extra_dirs=raw.extra_tool_dirs())
        ours = bool(tool) and paths.bin.resolve() in tool.resolve().parents
        ffmpeg = {"found": bool(tool), "ours": ours, "path": str(tool or ""),
                  "bytes": float(storage.size_of(paths.bin)) if ours else 0.0,
                  "date": _date(tool) if ours else ""}

        temp_files = [p for p in paths.temp.iterdir() if p.is_file()] if paths.temp.is_dir() else []
        self._data = {
            "dataDir": str(paths.root),
            "modelsDir": str(models_dir),
            "foreign": storage.foreign_models(models_dir),
            "freeBytes": float(platform.free_bytes(models_dir)),
            "models": rows,
            "ffmpeg": ffmpeg,
            "tempBytes": float(storage.size_of(paths.temp)),
            "tempCount": len(temp_files),
        }
        self.changed.emit()

    def _get(self, key, default=None):
        if not self._data:
            self.refresh()
        return self._data.get(key, default)

    # --- что видно окну ----------------------------------------------------
    @Property(str, notify=changed)
    def dataDir(self) -> str:
        return self._get("dataDir", "")

    @Property(str, notify=changed)
    def modelsDir(self) -> str:
        return self._get("modelsDir", "")

    @Property(int, notify=changed)
    def foreign(self) -> int:
        """Чужих моделей в папке: больше нуля — папка общая, это стоит сказать."""
        return int(self._get("foreign", 0))

    @Property(float, notify=changed)
    def freeBytes(self) -> float:
        return float(self._get("freeBytes", 0.0))

    @Property("QVariantList", notify=changed)
    def models(self) -> list:
        return self._get("models", [])

    @Property("QVariantMap", notify=changed)
    def ffmpeg(self) -> dict:
        return self._get("ffmpeg", {})

    @Property(float, notify=changed)
    def tempBytes(self) -> float:
        return float(self._get("tempBytes", 0.0))

    @Property(int, notify=changed)
    def tempCount(self) -> int:
        return int(self._get("tempCount", 0))

    @Property(float, notify=changed)
    def downloadedBytes(self) -> float:
        """«Скачано N»: модели и свой ffmpeg — то, что программа принесла сама."""
        return (sum(row["bytes"] for row in self.models if row["state"] != storage.ABSENT)
                + float(self.ffmpeg.get("bytes", 0.0)))

    @Property(str, notify=changed)
    def downloading(self) -> str:
        """Какая модель качается сейчас, или пусто."""
        return self._downloading

    @Property(float, notify=changed)
    def bytesDone(self) -> float:
        return self._done

    @Property(float, notify=changed)
    def bytesTotal(self) -> float:
        return self._total

    @Property(float, notify=changed)
    def speed(self) -> float:
        """Байт в секунду, сглаженно: мгновенная скорость скачет и раздражает."""
        return self._speed

    @Property("QVariantMap", notify=changed)
    def error(self) -> dict:
        """Чем кончилась последняя загрузка, если неудачей: код, модель, докуда дошли."""
        return self._error

    @Property(bool, notify=changed)
    def locked(self) -> bool:
        """Идёт работа — удалять нельзя, движок держит модель открытой."""
        return bool(self._working())

    # --- действия -----------------------------------------------------------
    @Slot(str)
    def removeModel(self, model_id: str) -> None:
        """Удалить модель — или «Убрать» оборванную загрузку: это та же папка."""
        if self._working() or model_id == self._downloading:
            return
        storage.remove_model(model_id, self._settings.raw.resolve_models_dir())
        if self._error.get("model") == model_id:
            self._error = {}
        self._after_change()

    @Slot(str)
    def downloadModel(self, model_id: str) -> None:
        """Скачать — или докачать: загрузчик сам продолжит с места обрыва."""
        if self._downloading or models.get(model_id) is None:
            return
        entry = models.get(model_id)
        self._downloading = model_id
        self._stop = False
        self._drop = False
        self._error = {}
        self._done = 0.0
        self._total = float(entry.size_mb) * 1024 * 1024
        self._speed = 0.0
        self._mark = (time.monotonic(), 0.0)
        self.changed.emit()
        self._pool.start(_Download(model_id, self._settings.raw.resolve_models_dir(),
                                   self._signals, lambda: self._stop))

    @Slot()
    def pause(self) -> None:
        """Приостановить: скачанное остаётся, «Скачать» потом продолжит с места."""
        self._stop = True

    @Slot()
    def cancel(self) -> None:
        """Отменить: скачанное не нужно — обрывок убираем, когда поток встанет."""
        self._stop = True
        self._drop = True

    @Slot()
    def clearTemp(self) -> None:
        if self._working():
            return          # во временной папке как раз лежит звук текущей работы
        paths = platform.paths().ensure()
        storage.clear(paths.temp, paths)
        self._after_change()

    @Slot()
    def removeFfmpeg(self) -> None:
        if self._working() or not self.ffmpeg.get("ours"):
            return
        paths = platform.paths().ensure()
        storage.clear(paths.bin, paths)
        self._after_change()

    def shutdown(self) -> None:
        """Перед выходом: остановить скачивание и дождаться потока."""
        self._stop = True
        self._pool.waitForDone(5000)

    # --- внутреннее -------------------------------------------------------
    def _after_change(self) -> None:
        self.refresh()
        self._env.refresh()      # блок «Готово к работе» должен увидеть перемену

    def _on_progress(self, done: float, total: float) -> None:
        now = time.monotonic()
        then, before = self._mark
        if now - then >= 1.0:
            current = (done - before) / (now - then)
            # Сглаживаем: скорость по одной секунде прыгает вдвое туда-сюда
            self._speed = current if self._speed == 0 else self._speed * 0.7 + current * 0.3
            self._mark = (now, done)
        self._done = done
        self._total = max(total, done)
        self.changed.emit()

    def _on_done(self, result) -> None:
        model_id = self._downloading
        reached = self._done
        self._downloading = ""
        self._speed = 0.0
        if isinstance(result, CoreError) and result.code == Code.CANCELLED:
            self._error = {}
            if self._drop:
                storage.remove_model(model_id, self._settings.raw.resolve_models_dir())
        elif isinstance(result, CoreError):
            self._error = {"code": result.code, "model": model_id, "bytes": reached,
                           **{k: str(v) for k, v in result.data.items()}}
        else:
            self._error = {}
        self._after_change()
