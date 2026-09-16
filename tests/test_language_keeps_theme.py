"""Смена языка интерфейса не должна трогать другие настройки.

Ошибка, из-за которой тест появился: при переводе меняется список надписей
в выпадающем списке, Qt при подмене списка обнуляет выбранный пункт, а
обработчик «пункт изменился» записывал этот ноль в настройки. Человек менял
язык — и вместе с ним менялась тема.
"""
import sys

from PySide6.QtCore import QTimer

from harness import done, start

app, window, settings, i18n = start(theme="dark", language="ru", screen="settings")

was_theme = settings.theme
was_models = settings.modelsDir
print(f"до смены языка: язык={settings.language} тема={was_theme}")


def switch():
    settings.setLanguage("en" if settings.language != "en" else "ru")
    QTimer.singleShot(400, check)


def check():
    print(f"после смены:    язык={settings.language} тема={settings.theme}")
    if settings.theme != was_theme:
        done(app, False, f"тема слетела: было {was_theme}, стало {settings.theme}")
    elif settings.modelsDir != was_models:
        done(app, False, "папка моделей слетела")
    else:
        done(app, True, "смена языка не задела остальные настройки")


QTimer.singleShot(700, switch)
sys.exit(app.exec())
