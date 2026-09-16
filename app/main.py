"""Точка входа окна.

Здесь только подъём движка QML и передача ему мостов. Никакой логики
распознавания: она в ядре, и окно её не знает (принципы П-1 и П-2).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

HERE = Path(__file__).resolve().parent
QML_DIR = HERE / "qml"


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

    # Служебный режим для разработки: отрисовать окно и сохранить картинку.
    forced_theme = ""
    if "--dark" in argv:
        forced_theme = "dark"
        argv.remove("--dark")
    if "--light" in argv:
        forced_theme = "light"
        argv.remove("--light")

    shot: str | None = None
    if "--shot" in argv:
        index = argv.index("--shot")
        shot = argv[index + 1]
        del argv[index:index + 2]

    app = QGuiApplication(sys.argv[:1] + argv)
    app.setApplicationName("Transcriber")
    app.setOrganizationName("Transcriber")

    # Свой стиль, а не подражание каждой системе (решение D-11).
    # Basic ничего не навязывает и полностью переопределяется темой.
    QQuickStyle.setStyle("Basic")

    if shot:
        _load_dev_fonts()

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("forcedTheme", forced_theme)
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
