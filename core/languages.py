"""Языки записи.

Список берём у самого движка: он знает ровно те коды, которые понимает.
Названия здесь не живут — их подбирает интерфейс из своего каталога
(принцип П-1). Ядро отдаёт коды и порядок.
"""
from __future__ import annotations

#: Языки, которые в списке идут первыми. Остальные — следом по алфавиту кода.
#: Порядок не про важность языков, а про то, что чаще выбирают в этой программе.
POPULAR = ("ru", "en", "uk", "de", "fr", "es", "it", "pl", "pt", "tr",
           "zh", "ja", "ko", "ar", "kk")

#: Запасной список, если движок почему-то не отдал свой.
_FALLBACK = POPULAR + ("be", "cs", "nl", "sv", "fi", "he", "hi", "hu", "id",
                       "ro", "sr", "sk", "th", "vi")


def codes() -> list[str]:
    """Все коды языков, популярные первыми."""
    try:
        from faster_whisper.tokenizer import _LANGUAGE_CODES

        known = set(_LANGUAGE_CODES)
    except Exception:
        known = set(_FALLBACK)

    head = [code for code in POPULAR if code in known]
    tail = sorted(known - set(head))
    return head + tail


def supported(code: str) -> bool:
    return code in set(codes())
