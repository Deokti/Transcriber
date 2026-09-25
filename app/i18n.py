"""Переводы интерфейса.

Ядро слов не знает: оно отдаёт коды, а фразы к ним подбираются здесь
(принцип П-1, решение D-4). Добавить язык — положить рядом ещё один json.

Устройство намеренно простое. Наружу торчит свойство `strings` — весь
каталог разом. QML пишет `I18n.strings["nav.settings"]`, и когда язык
меняется, свойство меняется целиком, а значит перерисовываются все надписи
сразу. Если бы вместо этого была функция, привязки бы о смене языка
не узнали и остались бы на старом языке до перезапуска.
"""
from __future__ import annotations

import json

from PySide6.QtCore import Property, QObject, Signal, Slot

from core import platform

CATALOG_DIR = platform.bundle_dir() / "app" / "i18n"
FALLBACK = "ru"


def available() -> list[dict]:
    """Языки, для которых есть каталог: код и самоназвание."""
    found = []
    for path in sorted(CATALOG_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        found.append({"code": path.stem, "name": data.get("language.name", path.stem)})
    return found


class I18n(QObject):
    languageChanged = Signal()

    def __init__(self, language: str = FALLBACK, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._catalogs: dict[str, dict] = {}
        self._language = ""
        self.setLanguage(language)

    def _catalog(self, code: str) -> dict:
        if code not in self._catalogs:
            path = CATALOG_DIR / f"{code}.json"
            try:
                self._catalogs[code] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._catalogs[code] = {}
        return self._catalogs[code]

    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._language

    @Property("QVariantList", constant=True)
    def languages(self) -> list:
        return available()

    @Property("QVariantMap", notify=languageChanged)
    def strings(self) -> dict:
        """Каталог целиком. Недостающие ключи добираются из запасного языка."""
        base = dict(self._catalog(FALLBACK))
        base.update(self._catalog(self._language))
        return base

    @Slot(str)
    def setLanguage(self, code: str) -> None:
        if code == self._language:
            return
        if not (CATALOG_DIR / f"{code}.json").exists():
            code = FALLBACK
        self._language = code
        self.languageChanged.emit()

    @Slot(str, result=str)
    def t(self, key: str) -> str:
        """Для кода на Python. В QML пользуйтесь strings — иначе не обновится."""
        return self.strings.get(key, key)
