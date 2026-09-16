"""Общая обвязка для тестов интерфейса.

Каждый тест запускается отдельным процессом: приложение Qt в процессе может
быть только одно, а тестам нужно разное начальное состояние — тема, язык,
экран. Поэтому здесь не классы и не фикстуры, а одна функция запуска.

Тесты ничего не сохраняют на диск: настройки читаются настоящие, но
`save()` никто не зовёт, так что файл пользователя остаётся нетронутым.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Иначе русский вывод рассыпается: консоль Windows отдаёт свою кодировку.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def start(*, theme: str | None = None, language: str = "ru", screen: str = "main"):
    """Поднимает окно и возвращает (приложение, окно, настройки, переводы)."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    from app.bridge import EnvBridge, ProfileBridge, SettingsBridge
    from app.i18n import I18n
    from app.main import QML_DIR, _load_dev_fonts

    app = QGuiApplication(sys.argv)
    _load_dev_fonts()          # без экрана у Qt пустой список шрифтов
    QQuickStyle.setStyle("Basic")

    settings = SettingsBridge()
    if theme:
        settings.setTheme(theme)
    env = EnvBridge(settings)
    task = ProfileBridge(settings)
    i18n = I18n(language)
    settings.changed.connect(lambda: i18n.setLanguage(settings.language))

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    context = engine.rootContext()
    context.setContextProperty("forcedTheme", "")
    context.setContextProperty("Settings", settings)
    context.setContextProperty("I18n", i18n)
    context.setContextProperty("Env", env)
    context.setContextProperty("Task", task)
    engine.setInitialProperties({"screen": screen})
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    assert engine.rootObjects(), "окно не загрузилось"

    # Движок держим от сборщика мусора: без ссылки окно исчезнет вместе с ним.
    window = engine.rootObjects()[0]
    # Держим от сборщика мусора: без ссылок окно исчезнет вместе с ними.
    window._keep = (engine, env, task)
    return app, window, settings, i18n


def luminance(color) -> float:
    """Грубая яркость точки, 0…255. Для сравнения светлее/темнее хватает."""
    return (color.red() + color.green() + color.blue()) / 3


def done(app, ok: bool, message: str) -> None:
    """Печатает вердикт и выходит с кодом, понятным запускалке."""
    print(("УСПЕХ: " if ok else "ПРОВАЛ: ") + message)
    app.exit(0 if ok else 1)
