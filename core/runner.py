"""JobRunner — фасад между интерфейсом и конвейером.

Наружу торчат четыре глагола: поставить в очередь, запустить, остановиться
после текущего файла, отменить всё. Внутрь уходит рабочий поток, который
гоняет задачи одну за другой и держит модель загруженной (решение D-8).

Почему именно фасад, а не прямой вызов конвейера: окно разговаривает только
с этим классом. Если однажды счёт переедет в отдельный процесс, поменяется
одна реализация — команды станут строками в трубу, события строками обратно,
а интерфейс об этом не узнает.

События приходят из рабочего потока. Интерфейс обязан перебросить их в свой
поток сам: в Qt это делают сигналы, в командной строке достаточно печати.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from enum import Enum

from core.asr.base import AsrBackend
from core.context import RunContext
from core.events import Code, Emit, Event, Kind
from core.job import Job, JobState
from core.media import Tools
from core.pipeline import run_job
from core.platform import Paths


class RunnerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"        # доработаем текущий файл и встанем
    CANCELLING = "cancelling"    # бросаем немедленно, сохранив посчитанное


class JobRunner:
    def __init__(self, *, paths: Paths, tools: Tools, backend: AsrBackend, emit: Emit) -> None:
        self._emit = emit
        self._queue: deque[Job] = deque()
        self._finished: list[Job] = []
        self._current: Job | None = None
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()
        self._stop = threading.Event()
        self._state = RunnerState.IDLE
        self._backend = backend
        self._ctx = RunContext(paths=paths, tools=tools, backend=backend,
                               emit=emit, should_cancel=self._cancel.is_set)

    # --- состояние ----------------------------------------------------------
    @property
    def state(self) -> RunnerState:
        return self._state

    @property
    def busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def current(self) -> Job | None:
        return self._current

    @property
    def pending(self) -> list[Job]:
        with self._lock:
            return list(self._queue)

    @property
    def finished(self) -> list[Job]:
        with self._lock:
            return list(self._finished)

    # --- команды ------------------------------------------------------------
    def add(self, *jobs: Job) -> None:
        """Ставит задачи в конец очереди. Можно и на ходу."""
        with self._lock:
            self._queue.extend(jobs)

    def start(self) -> None:
        """Запускает рабочий поток. Повторный вызов на ходу ничего не делает."""
        if self.busy:
            return
        self._cancel.clear()
        self._stop.clear()
        self._state = RunnerState.RUNNING
        self._thread = threading.Thread(target=self._work, name="transcriber-runner", daemon=True)
        self._thread.start()

    def stop_after_current(self) -> None:
        """Мягкая остановка: текущий файл дорабатываем, к следующему не переходим."""
        if not self.busy:
            return
        self._stop.set()
        self._state = RunnerState.STOPPING
        self._event(Kind.INFO, Code.STOP_REQUESTED,
                    current=self._current.source.name if self._current else None,
                    pending=len(self.pending))

    def undo_stop(self) -> bool:
        """«Продолжить работу» — пока остановка не случилась, её можно отменить."""
        if self._state is not RunnerState.STOPPING or not self.busy:
            return False
        self._stop.clear()
        self._state = RunnerState.RUNNING
        self._event(Kind.INFO, Code.STOP_UNDONE, pending=len(self.pending))
        return True

    def cancel_all(self) -> None:
        """Жёсткая отмена. Посчитанное сохранится — этим занимается конвейер."""
        if not self.busy:
            return
        self._state = RunnerState.CANCELLING
        self._cancel.set()
        self._event(Kind.INFO, Code.CANCEL_REQUESTED,
                    current=self._current.source.name if self._current else None,
                    pending=len(self.pending))

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def release(self) -> None:
        """Выгружает модель из памяти. Зовут, когда работа надолго закончена."""
        self._backend.unload()

    # --- рабочий поток ------------------------------------------------------
    def _work(self) -> None:
        started = time.monotonic()
        with self._lock:
            total = len(self._queue)
        self._event(Kind.QUEUE_STARTED, None, total=total)

        while not self._cancel.is_set():
            with self._lock:
                job = self._queue.popleft() if self._queue else None
            if job is None:
                break

            self._current = job
            try:
                run_job(job, self._ctx)
            except Exception as e:
                # Конвейер ловит свои ошибки сам. Если что-то пробилось сюда —
                # это наша ошибка, и очередь всё равно не должна умирать.
                job.state = JobState.FAILED
                job.error_code = Code.UNEXPECTED
                job.error_data = {"reason": repr(e)}
                self._event(Kind.FAILED, Code.UNEXPECTED,
                            name=job.source.name, reason=repr(e))
            finally:
                self._current = None
                with self._lock:
                    self._finished.append(job)

            if self._stop.is_set():
                break

        self._drop_rest()
        # Модель переиспользуется внутри очереди. После её завершения
        # следующий запуск GUI всё равно создаёт новый backend.
        self._backend.unload()
        self._state = RunnerState.IDLE
        self._event(Kind.QUEUE_DONE, None, seconds=round(time.monotonic() - started, 1),
                    **self._counts())

    def _drop_rest(self) -> None:
        """Непройденные задачи помечаются отменёнными — очередь не врёт о них."""
        with self._lock:
            rest = list(self._queue)
            self._queue.clear()
        for job in rest:
            job.state = JobState.CANCELLED
            job.error_code = Code.CANCELLED
            with self._lock:
                self._finished.append(job)

    def _counts(self) -> dict:
        jobs = self.finished
        return {
            "total": len(jobs),
            "done": sum(1 for j in jobs if j.state is JobState.DONE and not j.stats.get("skipped")),
            "skipped": sum(1 for j in jobs if j.stats.get("skipped")),
            "failed": sum(1 for j in jobs if j.state is JobState.FAILED),
            "cancelled": sum(1 for j in jobs if j.state is JobState.CANCELLED),
        }

    def _event(self, kind: Kind, code: str | None = None, **data) -> None:
        self._emit(Event(kind=kind, stage=None, code=code, data=data))
