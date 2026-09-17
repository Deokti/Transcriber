"""Очередь: какие записи поставлены на распознавание.

Разбор файла — это запуск ffprobe, десятки миллисекунд на штуку, а папку
кладут целиком. Поэтому список пополняется сразу, а длительность и дорожки
приезжают следом из рабочих потоков: строка сначала показывает имя и
пометку «читаю», потом обрастает данными (NFR-4 — окно не замирает).

Порядок в очереди — тот, в котором файлы положили: человек знает, что
поставил первым, и переставлять это за него не нужно.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, QRunnable, QThreadPool, Signal, Slot

from app.bridge.paths import clean
from app.bridge.settings import SettingsBridge
from core.events import Code, CoreError
from core.media import MEDIA_EXT, ensure_tools, probe

#: Состояние строки очереди. Человеческие слова к ним подбирает окно.
STATE_PROBING = "probing"
STATE_READY = "ready"
STATE_FAILED = "failed"


class _ProbeSignals(QObject):
    """Обратная связь из рабочего потока.

    Сигналы объявлены на отдельном объекте, потому что QRunnable — не QObject
    и своих сигналов иметь не может. Объект живёт в главном потоке, значит
    Qt сам переложит вызов туда, и список меняется только в одном потоке.
    """

    done = Signal(str, object)
    failed = Signal(str, str)


class _ProbeTask(QRunnable):
    """Разбор одного файла: длительность, картинка, звуковые дорожки."""

    def __init__(self, path: Path, ffprobe: Path, signals: _ProbeSignals) -> None:
        super().__init__()
        self._path = path
        self._ffprobe = ffprobe
        self._signals = signals

    def run(self) -> None:
        try:
            info = probe(self._ffprobe, self._path)
        except CoreError as error:
            self._say(self._signals.failed, str(self._path), error.code)
            return
        except Exception:
            # Неожиданное — тоже ответ: строка покажет, что файл не прочитан,
            # а очередь продолжит жить (FR-3: ошибка на одном не роняет остальные).
            self._say(self._signals.failed, str(self._path), Code.FFPROBE_FAILED)
            return

        if not info.audio:
            self._say(self._signals.failed, str(self._path), Code.NO_AUDIO_TRACK)
            return

        self._say(self._signals.done, str(self._path), {
            "duration": float(info.duration),
            "video": bool(info.has_video),
            "container": info.container,
            "tracks": [{"index": t.index, "codec": t.codec, "channels": t.channels,
                        "lang": t.lang, "title": t.title, "default": t.default}
                       for t in info.audio],
        })

    @staticmethod
    def _say(signal, *args) -> None:
        """Отвечает, если есть кому.

        Окно могли закрыть, пока мы читали файл. Тогда получателя уже нет,
        и попытка ответить роняет рабочий поток — без всякой пользы.
        """
        try:
            signal.emit(*args)
        except RuntimeError:
            pass


class QueueBridge(QObject):
    changed = Signal()

    def __init__(self, settings: SettingsBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._items: list[dict] = []
        # Без родителя нарочно: объект должен пережить сам мост. Иначе
        # поток, дочитывающий файл после закрытия окна, придёт с ответом
        # к удалённому объекту и уронит RuntimeError. Связи с этим мостом
        # Qt разорвёт сам, когда мост исчезнет, и ответ просто пропадёт.
        self._signals = _ProbeSignals()
        self._signals.done.connect(self._probed)
        self._signals.failed.connect(self._broke)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(4)   # ffprobe упирается в диск, не в счёт

    def shutdown(self) -> None:
        """Перед выходом: дать разборам файлов закончиться, а не обрывать их."""
        self._pool.waitForDone(3000)

    # --- что видно окну -------------------------------------------------
    @Property("QVariantList", notify=changed)
    def files(self) -> list:
        return self._items

    @Property(int, notify=changed)
    def count(self) -> int:
        return len(self._items)

    @Property(float, notify=changed)
    def totalDuration(self) -> float:
        return float(sum(item["duration"] for item in self._items))

    @Property(float, notify=changed)
    def totalSize(self) -> float:
        return float(sum(item["size"] for item in self._items))

    @Property(int, notify=changed)
    def readyCount(self) -> int:
        """Сколько файлов прочитано и годится в работу."""
        return sum(1 for item in self._items if item["state"] == STATE_READY)

    @Property(bool, notify=changed)
    def reading(self) -> bool:
        """Хоть один файл ещё разбирается — запускать рано."""
        return any(item["state"] == STATE_PROBING for item in self._items)

    @Property("QVariantList", constant=True)
    def extensions(self) -> list:
        """Расширения для фильтра в файловом диалоге."""
        return sorted(MEDIA_EXT)

    # --- изменения ------------------------------------------------------
    @Slot("QVariantList")
    def add(self, items) -> None:
        """Добавляет файлы: из диалога, из перетаскивания, папками.

        Расширение здесь не проверяется: человек выбрал файл явно, и решать,
        медиа это или нет, будет ffprobe по содержимому (FR-1). А вот папку
        разворачиваем по расширениям — иначе пришлось бы читать каждый
        текстовый файл рядом с записями.
        """
        paths: list[Path] = []
        for item in items:
            path = Path(clean(item))
            if not path.name:
                continue
            if path.is_dir():
                paths += _media_in(path)
            elif path.is_file():
                paths.append(path)
        self._put(paths)

    @Slot(str)
    def addFolder(self, url: str) -> None:
        folder = Path(clean(url))
        if folder.is_dir():
            self._put(_media_in(folder))

    @Slot(int)
    def remove(self, index: int) -> None:
        if 0 <= index < len(self._items):
            del self._items[index]
            self.changed.emit()

    @Slot()
    def clear(self) -> None:
        if self._items:
            self._items.clear()
            self.changed.emit()

    @Slot(int, int)
    def setTrack(self, index: int, track: int) -> None:
        """Какую звуковую дорожку распознавать в этом файле (FR-2)."""
        if 0 <= index < len(self._items):
            self._items[index]["track"] = int(track)
            self.changed.emit()

    # --- внутреннее -----------------------------------------------------
    def _put(self, paths: list[Path]) -> None:
        known = {item["path"] for item in self._items}
        added = []
        for path in paths:
            key = str(path)
            if key in known:
                continue        # тот же файл дважды в очереди не нужен
            known.add(key)
            added.append({
                "path": key,
                "name": path.name,
                "size": float(path.stat().st_size) if path.exists() else 0.0,
                "state": STATE_PROBING,
                "code": "",
                "duration": 0.0,
                "video": False,
                "container": "",
                "tracks": [],
                "track": 0,
            })
        if not added:
            return
        self._items += added
        self.changed.emit()

        try:
            tools = ensure_tools(self._settings.raw.extra_tool_dirs())
        except CoreError as error:
            for item in added:
                item["state"] = STATE_FAILED
                item["code"] = error.code
            self.changed.emit()
            return

        for item in added:
            self._pool.start(_ProbeTask(Path(item["path"]), tools.ffprobe, self._signals))

    def _find(self, path: str) -> dict | None:
        return next((item for item in self._items if item["path"] == path), None)

    def _probed(self, path: str, data: dict) -> None:
        item = self._find(path)
        if item is None:
            return              # успели убрать из очереди, пока читали
        item.update(data)
        item["state"] = STATE_READY
        default = next((t["index"] for t in item["tracks"] if t["default"]), 0)
        item["track"] = default
        self.changed.emit()

    def _broke(self, path: str, code: str) -> None:
        item = self._find(path)
        if item is None:
            return
        item["state"] = STATE_FAILED
        item["code"] = code
        self.changed.emit()


def _media_in(folder: Path) -> list[Path]:
    """Медиафайлы прямо в папке, по алфавиту. Вложенные папки не трогаем.

    Вглубь не идём нарочно: у людей рядом с записями лежат архивы прошлых
    лет, и «выбрал папку — получил двести файлов» пугает сильнее, чем
    «выбрал папку — получил то, что в ней видно».
    """
    try:
        children = sorted(folder.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return []
    return [p for p in children if p.is_file() and p.suffix.lower() in MEDIA_EXT]
