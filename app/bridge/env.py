"""Состояние машины: ffmpeg, модели, видеокарта, место на диске.

Из этого собирается блок «Готово к работе» и списки на главном экране.
Опрос не бесплатный — спрашиваем драйвер видеокарты и запускаем ffmpeg, —
поэтому он делается по требованию, а не на каждое обращение к свойству.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.bridge.settings import SettingsBridge
from core import platform
from core.env import languages, models
from core.events import CoreError
from core.export import SUPPORTED as EXPORT_FORMATS
from core.media import ensure_tools, version


class EnvBridge(QObject):
    changed = Signal()

    def __init__(self, settings: SettingsBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._data: dict = {}
        self.refresh()
        settings.changed.connect(self.refresh)

    @Slot()
    def refresh(self) -> None:
        raw = self._settings.raw
        models_dir = raw.resolve_models_dir()

        ffmpeg_path, ffmpeg_version = "", ""
        try:
            tools = ensure_tools(raw.extra_tool_dirs())
            ffmpeg_path = str(tools.ffmpeg)
            ffmpeg_version = version(tools.ffmpeg)
        except CoreError:
            pass       # не найден — так и скажем свойством ffmpegOk

        devices = [{"id": d.id, "available": d.available, "reason": d.reason or ""}
                   for d in platform.devices()]
        gpu = next((d for d in devices if d["id"] == "cuda"), {})

        self._data = {
            "ffmpegPath": ffmpeg_path,
            "ffmpegVersion": ffmpeg_version,
            "gpuName": platform.gpu_name(),
            "gpuAvailable": bool(gpu.get("available")),
            "gpuReason": gpu.get("reason", ""),
            "freeBytes": float(platform.free_bytes(models_dir)),
            "devices": devices,
            "languages": languages.codes(),
            "models": [dict(m.as_data(), downloaded=models.is_downloaded(m.id, models_dir))
                       for m in models.CATALOG],
            "formats": sorted(EXPORT_FORMATS),
        }
        self.changed.emit()

    def _get(self, key, default=None):
        return self._data.get(key, default)

    @Property(str, notify=changed)
    def ffmpegPath(self) -> str:
        return self._get("ffmpegPath", "")

    @Property(str, notify=changed)
    def ffmpegVersion(self) -> str:
        return self._get("ffmpegVersion", "")

    @Property(bool, notify=changed)
    def ffmpegOk(self) -> bool:
        return bool(self._get("ffmpegPath"))

    @Property(str, notify=changed)
    def gpuName(self) -> str:
        return self._get("gpuName", "")

    @Property(bool, notify=changed)
    def gpuAvailable(self) -> bool:
        return bool(self._get("gpuAvailable"))

    @Property(str, notify=changed)
    def gpuReason(self) -> str:
        return self._get("gpuReason", "")

    @Property(float, notify=changed)
    def freeBytes(self) -> float:
        return float(self._get("freeBytes", 0.0))

    @Property("QVariantList", notify=changed)
    def devices(self) -> list:
        return self._get("devices", [])

    @Property("QVariantList", notify=changed)
    def languages(self) -> list:
        return self._get("languages", [])

    @Property("QVariantList", notify=changed)
    def models(self) -> list:
        return self._get("models", [])

    @Property("QVariantList", notify=changed)
    def formats(self) -> list:
        """Форматы, которые ядро действительно умеет собрать прямо сейчас."""
        return self._get("formats", [])

    @Slot(str, result=bool)
    def modelDownloaded(self, model_id: str) -> bool:
        return any(m["id"] == model_id and m["downloaded"] for m in self._get("models", []))
