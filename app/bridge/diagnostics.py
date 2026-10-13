"""Диагностика: пять проверок и журнал последнего запуска (FR-27).

Проверки запускают ffmpeg и спрашивают драйвер видеокарты — это доли
секунды, но в потоке окна они заметны: экран бы замирал на каждом
«Проверить заново». Поэтому проверки идут в рабочем потоке, а ответ
приходит сигналом.

Слов здесь нет: наружу уходят уровни, коды и числа (принцип П-1).
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Property, QObject, QRunnable, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication

from app.bridge.settings import SettingsBridge
from core import journal, platform
from core.env import checks


class _Signals(QObject):
    done = Signal(object)          # список проверок


class _Check(QRunnable):
    def __init__(self, settings, model_id: str, signals: _Signals) -> None:
        super().__init__()
        self._settings = settings
        self._model_id = model_id
        self._signals = signals

    def run(self) -> None:
        try:
            result = checks.run(self._settings, self._model_id)
        except Exception as error:          # проверка не должна ронять окно
            result = [checks.Check("ffmpeg", checks.FAIL, "CHECK_FAILED",
                                   {"reason": repr(error)})]
        try:
            self._signals.done.emit(result)
        except RuntimeError:
            pass    # окно закрыли, слушать некому


def _plain(value):
    """То, что QML прочитает: строки, числа, списки и словари из них.

    Байты бывают больше 2³¹ — целое QML такое обрежет, поэтому числа
    отдаём дробными. Пути и перечисления — строкой.
    """
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    return str(value)


class DiagnosticsBridge(QObject):
    changed = Signal()

    def __init__(self, settings: SettingsBridge, model: Callable[[], str],
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._model = model                # какая модель выбрана для работы
        self._checks: list[dict] = []
        self._verdict = ""
        self._checked_at = ""
        self._busy = False
        self._log: list[dict] = []
        self._signals = _Signals()         # без родителя: переживает мост
        self._signals.done.connect(self._on_done)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

    # --- что видно окну ----------------------------------------------------
    @Property("QVariantList", notify=changed)
    def checks(self) -> list:
        return self._checks

    @Property(str, notify=changed)
    def verdict(self) -> str:
        """ready | slow | blocked; пусто — ещё не проверяли."""
        return self._verdict

    @Property(str, notify=changed)
    def checkedAt(self) -> str:
        return self._checked_at

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property("QVariantList", notify=changed)
    def log(self) -> list:
        """Строки журнала последнего запуска: время, род, стадия, код, данные."""
        return self._log

    # --- действия -----------------------------------------------------------
    @Slot()
    def refresh(self) -> None:
        self.reloadLog()
        if self._busy:
            return
        self._busy = True
        self.changed.emit()
        self._pool.start(_Check(self._settings.raw, self._model(), self._signals))

    @Slot()
    def reloadLog(self) -> None:
        path = platform.paths().logs / journal.LAST_RUN
        self._log = [_plain(item) for item in journal.read(path)]
        self.changed.emit()

    @Slot(str)
    def copy(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)

    @Slot("QVariant", str, result=bool)
    def save(self, target, text: str) -> bool:
        """Сохраняет журнал словами — тем, что человек видит на экране."""
        path = target.toLocalFile() if isinstance(target, QUrl) else QUrl(str(target)).toLocalFile()
        if not path:
            path = str(target)
        try:
            Path(path).write_text(text, encoding="utf-8")
        except OSError:
            return False
        return True

    def shutdown(self) -> None:
        self._pool.waitForDone(5000)

    # --- внутреннее -------------------------------------------------------
    def _on_done(self, result: list) -> None:
        self._checks = [{"id": c.id, "level": c.level, "code": c.code, "data": _plain(c.data)}
                        for c in result]
        self._verdict = checks.verdict(result)
        self._checked_at = datetime.now().isoformat(timespec="seconds")
        self._busy = False
        self.changed.emit()
