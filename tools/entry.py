"""Точка входа для собранного приложения.

PyInstaller хочет отдельный файл-скрипт, а не модуль пакета. Здесь только
запуск: вся логика в app/main.py, как и при запуске из исходников.
"""
import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
