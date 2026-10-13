"""Диагностика: пять проверок, которые снимают вопрос «почему не работает» (FR-27).

ffmpeg, видеокарта, модели, временные файлы, место на диске. Каждая
проверка отвечает уровнем и кодом, а слова подбирает интерфейс (принцип П-1):

    ok   — в порядке;
    note — стоит знать, но работе не мешает;
    warn — работать можно, но хуже обычного;
    fail — работать нельзя, пока это не исправить.

Проверки недолгие, но не мгновенные: запустить ffmpeg и спросить драйвер
видеокарты — доли секунды. Окно зовёт их из рабочего потока.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core import platform
from core.env import models, storage
from core.events import CoreError
from core.media import ensure_tools, version
from core.settings import Settings

OK, NOTE, WARN, FAIL = "ok", "note", "warn", "fail"

#: Итог всех проверок разом — для строки под заголовком.
READY = "ready"          # работать можно
SLOW = "slow"            # можно, но медленнее обычного: видеокарта молчит
BLOCKED = "blocked"      # нельзя, пока не исправить

#: Байт в секунду промежуточного WAV: 16 кГц, моно, 16 бит.
WAV_RATE = 16000 * 2
#: Под какую запись считаем место: три часа — длинная лекция или семинар.
LONG_RECORDING = 3 * 3600

MB = 1024 * 1024


@dataclass(frozen=True)
class Check:
    id: str                  # ffmpeg | gpu | models | temp | disk
    level: str
    code: str
    data: dict = field(default_factory=dict)


def run(settings: Settings, model_id: str) -> list[Check]:
    """Все пять проверок по порядку экрана. model_id — модель, выбранная для работы."""
    paths = platform.paths().ensure()
    models_dir = settings.resolve_models_dir()
    return [
        ffmpeg(settings, paths),
        gpu(),
        chosen_models(models_dir, model_id),
        temp(paths),
        disk(paths, models_dir, model_id),
    ]


def verdict(checks: list[Check]) -> str:
    if any(c.level == FAIL for c in checks):
        return BLOCKED
    if any(c.id == "gpu" and c.level == WARN for c in checks):
        return SLOW
    return READY


def ffmpeg(settings: Settings, paths: platform.Paths) -> Check:
    try:
        tools = ensure_tools(settings.extra_tool_dirs())
    except CoreError:
        return Check("ffmpeg", FAIL, "FFMPEG_MISSING")
    ours = paths.bin.resolve() in tools.ffmpeg.resolve().parents
    return Check("ffmpeg", OK, "FFMPEG_FOUND", {
        "path": str(tools.ffmpeg), "version": version(tools.ffmpeg), "ours": ours})


def gpu() -> Check:
    """Видеокарта: считает ли движок на ней, а если нет — почему.

    Нет видеокарты NVIDIA — это не неисправность, а обычный компьютер:
    считать будет процессор, и чинить тут нечего. Тревожно другое: карта
    есть, а движок её не видит. Тогда человек ждёт в разы дольше и не
    знает, что дело в драйвере.
    """
    if platform.system_name() == "macos":
        return Check("gpu", OK, "GPU_MACOS")
    name, driver = platform.gpu_info()
    cuda = next(d for d in platform.devices() if d.id == "cuda")
    data = {"name": name, "driver": driver}
    if cuda.available:
        return Check("gpu", OK, "GPU_READY", data)
    if not name:
        return Check("gpu", OK, "GPU_ABSENT")
    if cuda.reason in (platform.NO_CUDA_IN_BUILD, platform.NO_CUDA_LIBS):
        return Check("gpu", WARN, "GPU_NO_CUDA", {**data, "reason": cuda.reason})
    if platform.driver_too_old(driver):
        floor = platform.CUDA_MIN_DRIVER[platform.system_name()]
        return Check("gpu", WARN, "GPU_OLD_DRIVER",
                     {**data, "required": ".".join(str(part) for part in floor)})
    return Check("gpu", WARN, "GPU_SILENT", data)


def chosen_models(models_dir: Path, model_id: str) -> Check:
    """Что скачано и на месте ли модель, выбранная для работы.

    Нехватка модели — не поломка: при запуске она скачается сама. Но
    сказать об этом заранее стоит — без сети запуск встанет.
    """
    on_disk = storage.models_on_disk(models_dir)
    ready = [m for m in on_disk if m.state == storage.READY]
    entry = models.get(model_id)
    data = {
        "ready": [m.id for m in ready],
        "bytes": sum(m.bytes for m in ready),
        "partial": [m.id for m in on_disk if m.state == storage.PARTIAL],
        "chosen": model_id,
        "chosenBytes": (entry.size_mb if entry else 0) * MB,
    }
    if not ready:
        return Check("models", NOTE, "MODELS_NONE", data)
    if model_id not in data["ready"]:
        return Check("models", NOTE, "MODEL_CHOSEN_MISSING", data)
    return Check("models", OK, "MODELS_READY", data)


def temp(paths: platform.Paths) -> Check:
    files = [p for p in paths.temp.iterdir() if p.is_file()] if paths.temp.is_dir() else []
    if not files:
        return Check("temp", OK, "TEMP_EMPTY")
    return Check("temp", NOTE, "TEMP_PILED",
                 {"count": len(files), "bytes": storage.size_of(paths.temp)})


def disk(paths: platform.Paths, models_dir: Path, model_id: str) -> Check:
    """Хватит ли места на длинную запись: промежуточный WAV плюс модель, если её нет.

    Модель считаем, только если она ляжет на тот же диск, что и звук:
    иначе это вопрос другого диска, и складывать числа было бы неверно.
    """
    free = platform.free_bytes(paths.temp)
    need = WAV_RATE * LONG_RECORDING
    entry = models.get(model_id)
    model_bytes = 0
    if entry and models.local_dir(model_id, models_dir) is None \
            and Path(models_dir).resolve().anchor == paths.temp.resolve().anchor:
        model_bytes = entry.size_mb * MB
    data = {"free": free, "need": need + model_bytes, "hours": LONG_RECORDING // 3600,
            "model": model_bytes}
    if free and free < need + model_bytes:
        return Check("disk", WARN, "DISK_LOW", data)
    return Check("disk", OK, "DISK_OK", data)
