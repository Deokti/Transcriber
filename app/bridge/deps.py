"""Чужие инструменты: принести ffmpeg, если его нет.

Скачивание идёт в рабочем потоке — те же грабли, что и с разбором файлов:
окно не должно замирать на сотне мегабайт. Ответ приходит сигналом, всё
состояние меняется в потоке окна.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, QRunnable, QThreadPool, Signal, Slot

from app.bridge.env import EnvBridge
from core import platform
from core.deps import fetch
from core.events import Cancelled, Code, CoreError


class _Signals(QObject):
    progress = Signal(float, float)
    done = Signal(object)          # список путей или CoreError


class _Task(QRunnable):
    def __init__(self, bin_dir, key: str, signals: _Signals, cancelled) -> None:
        super().__init__()
        self._bin_dir = bin_dir
        self._key = key
        self._signals = signals
        self._cancelled = cancelled

    def run(self) -> None:
        try:
            made = fetch.get_ffmpeg(self._bin_dir, self._key,
                                    on_progress=lambda d, t: self._say(d, t),
                                    should_cancel=self._cancelled)
            self._finish(made)
        except Cancelled:
            self._finish(CoreError(Code.CANCELLED))
        except CoreError as error:
            self._finish(error)
        except Exception as error:      # сеть, диск, архив — всё сюда
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


class DepsBridge(QObject):
    changed = Signal()

    def __init__(self, env: EnvBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._env = env
        self._busy = False
        self._done = 0.0
        self._total = 0.0
        self._error: dict = {}
        self._stop = False
        self._signals = _Signals()      # без родителя: переживает мост
        self._signals.progress.connect(self._on_progress)
        self._signals.done.connect(self._on_done)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

    # --- что видно окну -------------------------------------------------
    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(float, notify=changed)
    def percent(self) -> float:
        return (self._done / self._total) if self._total else 0.0

    @Property(float, notify=changed)
    def bytesDone(self) -> float:
        return self._done

    @Property(float, notify=changed)
    def bytesTotal(self) -> float:
        return self._total

    @Property("QVariantMap", notify=changed)
    def error(self) -> dict:
        return self._error

    @Property("QVariantMap", constant=True)
    def ffmpegBuild(self) -> dict:
        """Что и откуда будем качать — чтобы кнопка могла назвать размер."""
        try:
            build = fetch.build_for(platform.target())
        except CoreError:
            return {}
        return {"source": build.source, "license": build.license,
                "sizeMb": build.size_mb, "note": build.note}

    # --- команды --------------------------------------------------------
    @Slot()
    def getFfmpeg(self) -> None:
        if self._busy:
            return
        build = self.ffmpegBuild
        if not build:
            self._error = {"code": Code.DOWNLOAD_FAILED, "reason": "no_build_for_platform"}
            self.changed.emit()
            return

        self._busy = True
        self._stop = False
        self._error = {}
        self._done = 0.0
        self._total = float(build.get("sizeMb", 0)) * 1024 * 1024
        self.changed.emit()

        self._pool.start(_Task(platform.paths().ensure().bin, platform.target(),
                               self._signals, lambda: self._stop))

    @Slot()
    def cancel(self) -> None:
        self._stop = True

    def shutdown(self) -> None:
        """Перед выходом: остановить скачивание и дождаться потока."""
        self._stop = True
        self._pool.waitForDone(5000)

    # --- ответы из потока -----------------------------------------------
    def _on_progress(self, done: float, total: float) -> None:
        self._done = done
        self._total = max(total, done)
        self.changed.emit()

    def _on_done(self, result) -> None:
        self._busy = False
        if isinstance(result, CoreError):
            self._error = {"code": result.code, **{k: str(v) for k, v in result.data.items()}}
        else:
            self._error = {}
            self._env.refresh()     # ffmpeg появился — блок готовности это увидит
        self.changed.emit()
