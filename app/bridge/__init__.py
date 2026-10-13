"""Мосты между окном и ядром — единственное место их встречи."""

from app.bridge.deps import DepsBridge
from app.bridge.diagnostics import DiagnosticsBridge
from app.bridge.env import EnvBridge
from app.bridge.profile import ProfileBridge
from app.bridge.queue import QueueBridge
from app.bridge.run import RunBridge
from app.bridge.shell import ShellBridge
from app.bridge.storage import StorageBridge
from app.bridge.settings import SettingsBridge

__all__ = ["DepsBridge", "DiagnosticsBridge", "EnvBridge", "ProfileBridge", "QueueBridge",
           "RunBridge", "SettingsBridge", "ShellBridge", "StorageBridge"]
