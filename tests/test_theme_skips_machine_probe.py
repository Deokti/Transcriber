"""Смена темы/языка не должна запускать ffmpeg и опрос GPU в потоке окна."""
import unittest
from unittest.mock import patch

import harness  # noqa: F401

from PySide6.QtCore import QCoreApplication, QObject, Signal

from app.bridge.env import EnvBridge
from core.settings import Settings


class SettingsStub(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.raw = Settings()


class Refresh(unittest.TestCase):
    def test_only_machine_paths_trigger_refresh(self):
        settings = SettingsStub()
        calls = []

        def refresh(bridge):
            calls.append(True)
            bridge._paths_key = (settings.raw.models_dir, settings.raw.ffmpeg_dir)

        with patch.object(EnvBridge, "refresh", refresh):
            bridge = EnvBridge(settings)
            for name, value in (("theme", "dark"), ("ui_language", "en"),
                                ("output_dir", "output")):
                setattr(settings.raw, name, value)
                settings.changed.emit()
            self.assertEqual(len(calls), 1)
            settings.raw.models_dir = "models"
            settings.changed.emit()
            settings.raw.ffmpeg_dir = "tools"
            settings.changed.emit()
            self.assertEqual(len(calls), 3)
            bridge.refresh()  # явный опрос после скачивания остаётся доступным
            self.assertEqual(len(calls), 4)


if __name__ == "__main__":
    app = QCoreApplication([])
    unittest.main()
