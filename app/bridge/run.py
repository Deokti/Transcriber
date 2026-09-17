"""Ход работы: очередь уходит в ядро, события возвращаются в окно.

Счёт живёт в своём потоке (решение D-8), и события приходят оттуда же.
Их нельзя трогать напрямую: свойства читает поток окна, и одновременная
правка списка кончилась бы редкой, неуловимой поломкой. Поэтому событие
переезжает через сигнал — Qt сам перекладывает его в поток получателя,
и всё состояние меняется в одном месте.

Слов здесь нет: наружу уходят коды и числа, фразу к ним подбирает окно
(принцип П-1).
"""
from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.bridge.profile import ProfileBridge
from app.bridge.queue import STATE_READY, QueueBridge
from app.bridge.settings import SettingsBridge
from core import platform
from core.asr.faster_whisper_backend import FasterWhisperBackend
from core.events import Code, CoreError, Event, Kind, Stage
from core.job import Job
from core.media import ensure_tools
from core.runner import JobRunner

#: Стадии, которые человек видит. Разбор файла мгновенный и в список не идёт.
VISIBLE_STAGES = (Stage.PREPARE.value, Stage.TRANSCRIBE.value,
                  Stage.CHECK.value, Stage.EXPORT.value, Stage.CLEANUP.value)

#: Скачивания в плане стадий нет — оно случается, только если модели нет на
#: диске. Поэтому строка списка заводится по ходу дела, а не заранее.
DOWNLOAD = Stage.DOWNLOAD.value

WAITING = "waiting"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"

#: Коды вердикта проверки текста. Их место — в карточке файла, а не в ленте
#: сообщений: это итог работы, а не замечание по ходу.
VERDICTS = (Code.QUALITY_CLEAN, Code.QUALITY_MINOR, Code.QUALITY_STUCK)

#: Сколько сообщений держим на экране. Журнал целиком пишется в файл ядром.
NOTICE_LIMIT = 40

#: Как часто ядро отчитывается о ходе распознавания, минуты звука.
#: В командной строке шаг крупный — там это строки в журнале, и пять минут
#: разумно. Здесь полоса и оценка времени, которые не должны замирать.
PROGRESS_STEP_MIN = 0.25


class _Sink(QObject):
    """Мостик между рабочим потоком и окном: одно событие — один сигнал."""

    event = Signal(object)


class RunBridge(QObject):
    changed = Signal()
    started = Signal()        # окно переключает экран
    finished = Signal()       # очередь закончена, можно показывать итог

    def __init__(self, settings: SettingsBridge, queue: QueueBridge,
                 profile: ProfileBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._queue = queue
        self._profile = profile
        self._runner: JobRunner | None = None
        # Без родителя нарочно: пережить мост, чтобы запоздалое событие
        # из рабочего потока не пришло к удалённому объекту.
        self._sink = _Sink()
        self._sink.event.connect(self._on_event)
        self._reset()

    def _reset(self) -> None:
        self._files: list[dict] = []
        self._stages: list[dict] = []
        self._notices: list[dict] = []
        self._results: list[dict] = []
        self._index = -1
        self._stage = ""
        self._percent = 0.0
        self._has_percent = False
        self._eta = 0.0
        self._loading = ""
        self._bytes = 0.0
        self._bytesTotal = 0.0
        self._nested = ""
        self._card: dict = {}
        self._summary: dict = {}
        self._failure: dict = {}

    # --- что видно окну -------------------------------------------------
    @Property(bool, notify=changed)
    def running(self) -> bool:
        return bool(self._runner and self._runner.busy)

    @Property(str, notify=changed)
    def state(self) -> str:
        """idle · running · stopping · cancelling — как их зовёт ядро."""
        return self._runner.state.value if self._runner else "idle"

    @Property("QVariantList", notify=changed)
    def files(self) -> list:
        return self._files

    @Property("QVariantList", notify=changed)
    def stages(self) -> list:
        """Стадии текущего файла с их состоянием."""
        return self._stages

    @Property(str, notify=changed)
    def fileName(self) -> str:
        return self._files[self._index]["name"] if 0 <= self._index < len(self._files) else ""

    @Property(int, notify=changed)
    def fileNumber(self) -> int:
        return self._index + 1

    @Property(int, notify=changed)
    def fileTotal(self) -> int:
        return len(self._files)

    @Property(str, notify=changed)
    def stage(self) -> str:
        return self._stage

    @Property(float, notify=changed)
    def percent(self) -> float:
        return self._percent

    @Property(bool, notify=changed)
    def hasPercent(self) -> bool:
        """Не всякая стадия умеет считать проценты: уборка просто идёт."""
        return self._has_percent

    @Property(float, notify=changed)
    def eta(self) -> float:
        """Секунды до конца текущего файла. Ноль — ещё не посчитано."""
        return self._eta

    @Property(float, notify=changed)
    def bytesDone(self) -> float:
        """Сколько уже скачано. Ноль — сейчас ничего не качается."""
        return self._bytes

    @Property(float, notify=changed)
    def bytesTotal(self) -> float:
        return self._bytesTotal

    @Property(str, notify=changed)
    def loadingModel(self) -> str:
        """Какая модель сейчас грузится. Пусто — не грузится.

        Загрузка large-v3 занимает около минуты, а первая — ещё и
        скачивание в несколько гигабайт. Без этого свойства окно в это
        время показывает пустую стадию и выглядит зависшим.
        """
        return self._loading

    @Property("QVariantList", notify=changed)
    def notices(self) -> list:
        return self._notices

    @Property("QVariantList", notify=changed)
    def results(self) -> list:
        return self._results

    @Property("QVariantMap", notify=changed)
    def summary(self) -> dict:
        """Итог очереди: сколько готово, пропущено, сорвалось, отменено."""
        return self._summary

    @Property("QVariantMap", notify=changed)
    def failure(self) -> dict:
        """Почему не удалось даже начать: код и данные, без слов."""
        return self._failure

    # --- команды --------------------------------------------------------
    @Slot()
    def start(self) -> None:
        """Забирает очередь и профиль и отдаёт их ядру."""
        if self.running:
            return

        items = [item for item in self._queue.files if item["state"] == STATE_READY]
        if not items:
            return

        self._reset()
        self._failure = {}
        profile = self._profile.snapshot()
        profile.progress_step_min = PROGRESS_STEP_MIN

        # Просим то, что есть: недоступная видеокарта — не повод падать (FR-11).
        device, reason = platform.usable_device(profile.device)
        if reason:
            profile.device = device
            profile.compute = platform.default_compute(device)
            self._notice(Kind.WARNING, Code.DEVICE_FALLBACK, {"reason": reason})

        try:
            tools = ensure_tools(self._settings.raw.extra_tool_dirs())
        except CoreError as error:
            self._failure = {"code": error.code, "data": _plain(error.data)}
            self.changed.emit()
            return

        paths = platform.paths().ensure()
        models_dir = self._settings.raw.resolve_models_dir()

        self._files = [{"name": Path(item["path"]).name, "path": item["path"],
                        "state": WAITING, "code": ""} for item in items]
        self._runner = JobRunner(paths=paths, tools=tools,
                                 backend=FasterWhisperBackend(models_dir),
                                 emit=self._sink.event.emit)
        self._runner.add(*(Job(source=Path(item["path"]),
                               profile=replace(profile, track=int(item["track"])))
                           for item in items))
        self._runner.start()
        self.changed.emit()
        self.started.emit()

    @Slot()
    def stopAfterCurrent(self) -> None:
        if self._runner:
            self._runner.stop_after_current()
            self.changed.emit()

    @Slot()
    def undoStop(self) -> None:
        if self._runner:
            self._runner.undo_stop()
            self.changed.emit()

    @Slot()
    def cancelAll(self) -> None:
        if self._runner:
            self._runner.cancel_all()
            self.changed.emit()

    @Slot()
    def release(self) -> None:
        """Выгружает модель из памяти — когда работа закончена надолго."""
        if self._runner and not self._runner.busy:
            self._runner.release()

    def shutdown(self) -> bool:
        """Перед выходом: отменить работу и дождаться, пока спасут посчитанное."""
        return self._runner.shutdown() if self._runner else True

    # --- события из ядра ------------------------------------------------
    def _on_event(self, event: Event) -> None:
        kind, stage, code, data = event.kind, event.stage, event.code, event.data

        if kind is Kind.JOB_STARTED:
            self._index += 1
            self._card = {"started": time.monotonic()}
            if 0 <= self._index < len(self._files):
                self._files[self._index]["state"] = RUNNING
            planned = [s for s in data.get("stages", []) if s in VISIBLE_STAGES]
            self._stages = [{"code": s, "state": WAITING} for s in planned]
            self._stage = ""
            self._percent = 0.0
            self._has_percent = False
            self._eta = 0.0

        elif kind is Kind.STAGE_STARTED and stage is not None:
            self._stage = stage.value
            if stage.value == DOWNLOAD:
                if not self._has_stage(DOWNLOAD):
                    self._stages = [{"code": DOWNLOAD, "state": WAITING}] + self._stages
                # Скачивание случается внутри распознавания. Две горящие
                # строки разом читаются как «делаю два дела сразу», поэтому
                # объемлющую стадию возвращаем в ожидание.
                self._nested = next((item["code"] for item in self._stages
                                     if item["state"] == RUNNING and item["code"] != DOWNLOAD), "")
                if self._nested:
                    self._mark_stage(self._nested, WAITING)
            self._mark_stage(stage.value, RUNNING)
            # Процент прошлой стадии к новой отношения не имеет: оставить
            # его — значит показать «100%» в начале распознавания.
            self._percent = 0.0
            self._has_percent = False

        elif kind is Kind.INFO and code == Code.MODEL_LOADING:
            self._loading = str(data.get("model", ""))

        elif kind is Kind.INFO and code == Code.MODEL_READY:
            self._loading = ""

        elif kind is Kind.PROGRESS:
            self._percent = float(data.get("done", 0.0))
            self._has_percent = True
            self._eta = float(data.get("eta", 0.0))
            if stage is not None and stage.value == DOWNLOAD:
                self._bytes = float(data.get("bytes", 0.0))
                self._bytesTotal = float(data.get("total", 0.0))

        elif kind is Kind.STAGE_DONE and stage is not None:
            self._mark_stage(stage.value, DONE)
            if stage.value == Stage.TRANSCRIBE.value:
                self._percent = 1.0     # счёт закончен, пусть так и показывает
            if stage.value == DOWNLOAD:
                # Своего «начала» у объемлющей стадии больше не будет:
                # возвращаем её сами, иначе экран так и будет писать
                # «Скачиваю модель» поверх процента распознавания.
                if self._nested:
                    self._mark_stage(self._nested, RUNNING)
                self._stage = self._nested
                self._nested = ""
                self._bytes = 0.0
                self._bytesTotal = 0.0
                self._percent = 0.0
                self._has_percent = False

        elif kind is Kind.INFO and code == Code.SOURCE_INFO:
            self._card["duration"] = float(data.get("duration", 0.0))
            self._card["video"] = bool(data.get("has_video"))

        elif kind is Kind.INFO and code == Code.AUDIO_SAVED:
            # Имя нарочно не «audio»: так в статистике зовётся длительность
            # звука, и карточка результата принимала число за файл.
            self._card["audioFile"] = {"path": str(data.get("path", "")),
                                       "size": float(data.get("size", 0.0)),
                                       "format": str(data.get("format", ""))}

        elif kind is Kind.INFO and code == Code.PARTIAL_SAVED:
            # Приходит уже после «файл прерван»: ядро сначала сообщает об
            # обрыве, потом спокойно досохраняет посчитанное. Значит правим
            # ту карточку, которая только что закрылась.
            if self._results:
                saved = _plain(data)
                self._results[-1]["partial"] = True
                self._results[-1]["artifacts"] = saved.get("artifacts", {})
                self._results[-1]["segments"] = saved.get("segments", 0)
                self._results[-1]["position"] = saved.get("position", 0.0)

        elif code in VERDICTS:
            self._card["verdict"] = code
            self._card["places"] = len(data.get("bad_runs", []))

        elif kind is Kind.JOB_DONE:
            self._loading = ""
            self._finish_file(DONE, "", data)

        elif kind is Kind.FAILED:
            self._loading = ""
            state = CANCELLED if code == Code.CANCELLED else FAILED
            self._finish_file(state, code or "", data)

        elif kind is Kind.QUEUE_DONE:
            self._summary = _plain(data)
            self._stage = ""
            # Работа кончилась — полоса замирает на доле сделанного, а не
            # бегает туда-сюда, будто что-то ещё происходит.
            total = data.get("total") or 0
            self._percent = (data.get("done", 0) / total) if total else 0.0
            self._has_percent = True
            # До чего не дошли — то и не дойдёт: очередь не должна оставлять
            # файлы в состоянии «ждёт», когда ждать уже нечего.
            for item in self._files:
                if item["state"] in (WAITING, RUNNING):
                    item["state"] = CANCELLED
            self.changed.emit()
            self.finished.emit()
            return

        if kind in (Kind.INFO, Kind.WARNING, Kind.FAILED):
            self._notice(kind, code, data, stage)

        self.changed.emit()

    def _has_stage(self, code: str) -> bool:
        return any(item["code"] == code for item in self._stages)

    def _mark_stage(self, code: str, state: str) -> None:
        for item in self._stages:
            if item["code"] == code:
                item["state"] = state
                return

    def _finish_file(self, state: str, code: str, data: dict) -> None:
        if not (0 <= self._index < len(self._files)):
            return
        current = self._files[self._index]
        current["state"] = state
        current["code"] = code
        # Красим только ту стадию, на которой оборвались. Остальные не
        # начинались — и приписывать им отмену значит врать: после отмены
        # ядро молча доделывает сохранение посчитанного (решение D-7).
        for item in self._stages:
            if item["state"] == RUNNING and state != DONE:
                item["state"] = state
        card = dict(self._card)
        started = card.pop("started", None)
        if started is not None:
            card["spent"] = round(time.monotonic() - started, 1)
        self._results.append({"name": current["name"], "path": current["path"],
                              "state": state, "code": code, **_plain(data), **card})
        self._card = {}

    def _notice(self, kind: Kind, code: str | None, data: dict,
                stage: Stage | None = None) -> None:
        if code is None:
            return
        self._notices = (self._notices + [{
            "kind": kind.value,
            "code": code,
            "stage": stage.value if stage else "",
            "file": self.fileName,
            "data": _plain(data),
        }])[-NOTICE_LIMIT:]


def _plain(data: dict) -> dict:
    """Приводит данные события к тому, что QML умеет прочитать.

    В событиях попадаются пути и вложенные словари; QML принимает строки,
    числа и списки, а остальное молча превращает в пустоту.
    """
    out = {}
    for key, value in data.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        elif isinstance(value, dict):
            out[key] = {k: str(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            out[key] = [v if isinstance(v, (str, int, float, bool)) else str(v) for v in value]
        else:
            out[key] = str(value)
    return out
