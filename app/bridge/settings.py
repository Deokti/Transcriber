"""Настройки приложения: язык интерфейса, тема, папки."""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication

from app.bridge.paths import clean
from core import platform
from core.settings import Settings

THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"


class SettingsBridge(QObject):
    """То, что относится к машине и вкусам, а не к конкретной записи."""

    changed = Signal()
    savedChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = Settings.load()
        self._saved = True
        scheme = QGuiApplication.styleHints().colorSchemeChanged
        scheme.connect(self.changed)   # система переключила тему — пересчитаем

    @property
    def raw(self) -> Settings:
        """Настройки как есть — для мостов, которым нужны пути."""
        return self._settings

    # --- язык ---------------------------------------------------------
    @Property(str, notify=changed)
    def language(self) -> str:
        return self._settings.ui_language

    # --- тема ---------------------------------------------------------
    @Property(str, notify=changed)
    def theme(self) -> str:
        return self._settings.theme

    @Property(bool, notify=changed)
    def isDark(self) -> bool:
        """Тёмная ли тема сейчас — с учётом варианта «как в системе»."""
        if self._settings.theme == THEME_DARK:
            return True
        if self._settings.theme == THEME_LIGHT:
            return False
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark

    # --- папки --------------------------------------------------------
    @Property(str, notify=changed)
    def modelsDir(self) -> str:
        return self._settings.models_dir

    @Property(str, notify=changed)
    def outputDir(self) -> str:
        return self._settings.output_dir

    @Property(str, notify=changed)
    def ffmpegDir(self) -> str:
        return self._settings.ffmpeg_dir

    @Property(str, constant=True)
    def dataDir(self) -> str:
        return str(platform.data_dir())

    @Property(str, constant=True)
    def defaultModelsDir(self) -> str:
        return str(platform.paths().models)

    @Property(bool, notify=savedChanged)
    def saved(self) -> bool:
        """Совпадает ли то, что на экране, с тем, что лежит на диске."""
        return self._saved

    # --- изменения ----------------------------------------------------
    @Slot(str)
    def setLanguage(self, code: str) -> None:
        self._update(ui_language=code)

    @Slot(str)
    def setTheme(self, value: str) -> None:
        if value in (THEME_SYSTEM, THEME_LIGHT, THEME_DARK):
            self._update(theme=value)

    @Slot(str)
    def setModelsDir(self, value: str) -> None:
        self._update(models_dir=clean(value))

    @Slot(str)
    def setOutputDir(self, value: str) -> None:
        self._update(output_dir=clean(value))

    @Slot(str)
    def setFfmpegDir(self, value: str) -> None:
        self._update(ffmpeg_dir=clean(value))

    @Slot()
    def save(self) -> None:
        self._settings.save()
        self._saved = True
        self.savedChanged.emit()

    def _update(self, **fields) -> None:
        for name, value in fields.items():
            if getattr(self._settings, name) == value:
                return
            setattr(self._settings, name, value)
        self._saved = False
        self.savedChanged.emit()
        self.changed.emit()
