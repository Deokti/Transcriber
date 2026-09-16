"""Точка входа окна.

Здесь только подъём движка QML и передача ему мостов. Никакой логики
распознавания: она в ядре, и окно её не знает (принципы П-1 и П-2).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle

from app.bridge import SettingsBridge
from app.i18n import I18n

HERE = Path(__file__).resolve().parent
QML_DIR = HERE / "qml"
ICON_DIR = HERE / "icons"


def _claim_own_identity() -> None:
    """Просит Windows считать нас отдельным приложением.

    Панель задач берёт значок не у окна, а у процесса. Пока процесс — это
    python.exe, там будет логотип Python, сколько окну значков ни ставь.
    Собственный идентификатор разрывает эту связь: система заводит нам свою
    ячейку в панели и берёт значок из окна.
    """
    if not sys.platform.startswith("win"):
        return
    import ctypes

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Transcriber.Desktop")
    except Exception:
        pass   # не вышло — значок будет питоновский, но работать это не мешает


def _app_icon() -> QIcon:
    """Значок окна и панели задач.

    Берём SVG напрямую: Qt отрисует их в любом размере, и собранные ICO с
    ICNS нужны только при упаковке. Для мелких размеров подставляем
    упрощённый знак — в 16 px подробный превращается в пятно.
    """
    icon = QIcon()
    small = ICON_DIR / "app-icon-small.svg"
    large = ICON_DIR / "app-icon.svg"
    for size in (16, 24):
        icon.addFile(str(small), QSize(size, size))
    for size in (32, 48, 64, 128, 256, 512):
        icon.addFile(str(large), QSize(size, size))
    return icon


def _load_dev_fonts() -> None:
    """Подсовывает системные шрифты файлами.

    В безэкранном режиме, которым удобно снимать картинки при разработке,
    список шрифтов у Qt пуст — весь текст превращается в квадраты. На живом
    экране этого не бывает, поэтому и функция только для разработки.
    """
    from PySide6.QtGui import QFontDatabase

    for name in ("segoeui.ttf", "segoeuib.ttf", "SegUIVar.ttf", "consola.ttf",
                 "arial.ttf", "DejaVuSans.ttf"):
        candidate = Path("C:/Windows/Fonts") / name
        if candidate.exists():
            QFontDatabase.addApplicationFont(str(candidate))


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    _claim_own_identity()

    # По умолчанию Qt рисует текст через поля расстояний — так дешевле
    # анимировать и масштабировать, но мелкие надписи слегка плывут.
    # Нам важнее чёткость: интерфейс статичный, а читают его часами.
    QQuickWindow.setTextRenderType(QQuickWindow.TextRenderType.NativeTextRendering)

    # Служебный режим для разработки: отрисовать окно и сохранить картинку.
    forced_theme = ""
    if "--dark" in argv:
        forced_theme = "dark"
        argv.remove("--dark")
    if "--light" in argv:
        forced_theme = "light"
        argv.remove("--light")

    ui_lang = ""
    if "--ui-lang" in argv:
        index = argv.index("--ui-lang")
        ui_lang = argv[index + 1]
        del argv[index:index + 2]

    start_screen = ""
    if "--screen" in argv:
        index = argv.index("--screen")
        start_screen = argv[index + 1]
        del argv[index:index + 2]

    shot: str | None = None
    if "--shot" in argv:
        index = argv.index("--shot")
        shot = argv[index + 1]
        del argv[index:index + 2]

    app = QGuiApplication(sys.argv[:1] + argv)
    app.setApplicationName("Transcriber")
    app.setOrganizationName("Transcriber")
    app.setWindowIcon(_app_icon())

    # Свой стиль, а не подражание каждой системе (решение D-11).
    # Basic ничего не навязывает и полностью переопределяется темой.
    QQuickStyle.setStyle("Basic")

    if shot:
        _load_dev_fonts()

    settings = SettingsBridge()
    i18n = I18n(ui_lang or settings.language)
    # Язык меняют в настройках — каталог переключается следом
    settings.changed.connect(lambda: i18n.setLanguage(settings.language))

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    context = engine.rootContext()
    context.setContextProperty("forcedTheme", forced_theme)
    context.setContextProperty("Settings", settings)
    context.setContextProperty("I18n", i18n)
    if start_screen:
        engine.setInitialProperties({"screen": start_screen})
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        return 1

    if shot:
        window = engine.rootObjects()[0]

        def grab() -> None:
            image = window.grabWindow()
            image.save(shot)
            app.quit()

        QTimer.singleShot(900, grab)   # даём шрифтам и раскладке устояться

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
