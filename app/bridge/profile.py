"""Настройки задачи: что сделать с этой записью.

Отличие от SettingsBridge: там устройство машины и вкусы, здесь — обработка
конкретных файлов. Профиль уходит в очередь копией, чтобы задача не менялась
под руками, пока человек крутит списки дальше.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.bridge.paths import clean
from app.bridge.settings import SettingsBridge
from core import platform, presets
from core.env import models
from core.profile import TARGET_AUDIO, TARGET_BOTH, TARGET_TEXT, Profile


class ProfileBridge(QObject):
    changed = Signal()

    def __init__(self, settings: SettingsBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._profile = Profile.defaults()
        self._profile.output_dir = settings.outputDir
        self._preset = ""                 # какой пресет выбран последним
        self._preset_values: dict = {}    # каким он был в момент выбора
        self._presets = presets.names(self._folder())

    def snapshot(self) -> Profile:
        """Копия для очереди."""
        return replace(self._profile)

    def _set(self, name: str, value) -> None:
        if getattr(self._profile, name) == value:
            return
        setattr(self._profile, name, value)
        self.changed.emit()

    # --- что нужно на выходе (FR-8, FR-37) ------------------------------
    @Property(str, notify=changed)
    def target(self) -> str:
        """text · audio · both — как их зовёт ядро."""
        return self._profile.target

    @Slot(str)
    def setTarget(self, value: str) -> None:
        self._set("target", value)

    @Property(str, notify=changed)
    def audioFormat(self) -> str:
        return self._profile.audio_format

    @Slot(str)
    def setAudioFormat(self, value: str) -> None:
        self._set("audio_format", value)

    @Property(bool, notify=changed)
    def needsText(self) -> bool:
        """Будет ли распознавание. Нет — значит модель и язык ни при чём."""
        return self._profile.target in (TARGET_TEXT, TARGET_BOTH)

    @Property(bool, notify=changed)
    def needsAudio(self) -> bool:
        return self._profile.target in (TARGET_AUDIO, TARGET_BOTH)

    # --- распознавание -------------------------------------------------
    @Property(str, notify=changed)
    def language(self) -> str:
        return self._profile.language

    @Slot(str)
    def setLanguage(self, value: str) -> None:
        self._set("language", value)

    @Property(str, notify=changed)
    def model(self) -> str:
        return self._profile.model

    @Slot(str)
    def setModel(self, value: str) -> None:
        self._set("model", value)

    @Property(str, notify=changed)
    def device(self) -> str:
        return self._profile.device

    @Slot(str)
    def setDevice(self, value: str) -> None:
        self._set("device", value)
        self._set("compute", platform.default_compute(value))

    # --- звук -----------------------------------------------------------
    @Property(str, notify=changed)
    def denoise(self) -> str:
        return self._profile.denoise

    @Slot(str)
    def setDenoise(self, value: str) -> None:
        self._set("denoise", value)

    @Property(bool, notify=changed)
    def loudnorm(self) -> bool:
        return self._profile.loudnorm

    @Slot(bool)
    def setLoudnorm(self, value: bool) -> None:
        self._set("loudnorm", value)

    @Property(bool, notify=changed)
    def trimSilence(self) -> bool:
        return self._profile.trim_silence

    @Slot(bool)
    def setTrimSilence(self, value: bool) -> None:
        self._set("trim_silence", value)

    # --- результат ------------------------------------------------------
    @Property(str, notify=changed)
    def format(self) -> str:
        return self._profile.formats[0] if self._profile.formats else ""

    @Slot(str)
    def setFormat(self, value: str) -> None:
        self._set("formats", [value])

    @Property(str, notify=changed)
    def layout(self) -> str:
        return self._profile.layout

    @Slot(str)
    def setLayout(self, value: str) -> None:
        self._set("layout", value)

    @Property(str, notify=changed)
    def outputDir(self) -> str:
        return self._profile.output_dir or ""

    @Slot(str)
    def setOutputDir(self, value: str) -> None:
        self._set("output_dir", clean(value))

    # --- дополнительно --------------------------------------------------
    @Property(bool, notify=changed)
    def force(self) -> bool:
        """Считать заново, даже если документ уже готов (FR-38)."""
        return self._profile.force

    @Slot(bool)
    def setForce(self, value: bool) -> None:
        self._set("force", value)

    @Property(str, notify=changed)
    def tempAction(self) -> str:
        return self._profile.temp_action

    @Slot(str)
    def setTempAction(self, value: str) -> None:
        self._set("temp_action", value)

    @Property(str, notify=changed)
    def sensitivity(self) -> str:
        return self._profile.sensitivity

    @Slot(str)
    def setSensitivity(self, value: str) -> None:
        self._set("sensitivity", value)

    @Property(int, notify=changed)
    def chunkLength(self) -> int:
        return self._profile.chunk_length

    @Slot(int)
    def setChunkLength(self, value: int) -> None:
        self._set("chunk_length", value)

    @Property(int, notify=changed)
    def cpuThreads(self) -> int:
        return self._profile.cpu_threads

    @Slot(int)
    def setCpuThreads(self, value: int) -> None:
        self._set("cpu_threads", value)

    # --- пресеты --------------------------------------------------------
    def _folder(self) -> Path:
        return platform.paths().profiles

    def _reload(self) -> None:
        self._presets = presets.names(self._folder())

    @Property("QVariantList", notify=changed)
    def presets(self) -> list:
        """Имена сохранённых пресетов по алфавиту."""
        return self._presets

    @Property(str, notify=changed)
    def preset(self) -> str:
        """Какой пресет выбран последним; пусто — никакой."""
        return self._preset

    @Property(bool, notify=changed)
    def presetModified(self) -> bool:
        """Настройки уже разошлись с выбранным пресетом — стоит сказать."""
        return bool(self._preset) and presets.values(self._profile) != self._preset_values

    @Slot(str, result=bool)
    def presetExists(self, name: str) -> bool:
        return presets.exists(name, self._folder())

    @Slot(str)
    def applyPreset(self, name: str) -> None:
        try:
            loaded = presets.load(name, self._folder())
        except (OSError, ValueError):
            self._reload()            # файл удалили мимо программы — список отстал
            self.changed.emit()
            return
        # Пресет мог приехать с другой машины: видеокарты, на которой он
        # сохранён, здесь может не быть, а модели — не оказаться в каталоге.
        # Тогда оставляем свои значения, а не ломаем запуск.
        if loaded.get("device") and platform.usable_device(loaded["device"])[1]:
            loaded.pop("device")
            loaded.pop("compute", None)
        if "model" in loaded and models.get(loaded["model"]) is None:
            loaded.pop("model")
        for key, value in loaded.items():
            setattr(self._profile, key, value)
        self._preset = presets.clean_name(name)
        self._preset_values = presets.values(self._profile)
        self.changed.emit()

    @Slot(str, result=bool)
    def savePreset(self, name: str) -> bool:
        name = presets.clean_name(name)
        try:
            presets.save(self._profile, name, self._folder())
        except (OSError, ValueError):
            return False
        self._preset = name
        self._preset_values = presets.values(self._profile)
        self._reload()
        self.changed.emit()
        return True

    @Slot(str)
    def removePreset(self, name: str) -> None:
        try:
            presets.remove(name, self._folder())
        except (OSError, ValueError):
            pass
        if presets.clean_name(name) == self._preset:
            self._preset = ""
        self._reload()
        self.changed.emit()

    @Slot()
    def clearPreset(self) -> None:
        """«Без пресета»: настройки остаются, пропадает только имя."""
        self._preset = ""
        self.changed.emit()
