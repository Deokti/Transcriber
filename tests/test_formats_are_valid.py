"""Каждый формат собирается так, что его откроет то, чем его откроют.

Этап M5: к txt добавились md, docx и субтитры. Проверяем не «файл появился»,
а то, на чём они ломаются по-настоящему:

- docx — это zip из XML; один управляющий символ в тексте, и Word отказывается
  открывать документ целиком. Проверяем, что XML разбирается;
- субтитры — проигрыватели строги к времени. Старый перевод секунд в строку
  округлял 59.9996 в «00:00:60.000», и такую строку SRT не принимает;
- «связный текст» по FR-18 — без тайм-кодов. Раньше он писал их перед каждым
  абзацем, хотя назывался «Сплошной текст»;
- Markdown — звёздочка в речи не должна превращать фразу в курсив.
"""
from __future__ import annotations

import re
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core import formats
from core.formats import subtitles
from core.asr.base import Segment
from core.profile import LAYOUT_PLAIN, LAYOUT_TIMECODES
from core.timecode import stamp

SEGMENTS = [
    Segment(start=0.0, end=2.5, text="Добрый день, начнём."),
    Segment(start=2.5, end=59.9996, text="Слово *важное* и [скобки]\x07 внутри."),
    Segment(start=62.0, end=64.0, text=""),
    Segment(start=64.0, end=70.0, text="Это длинная фраза, которой в одной строке субтитра "
                                       "явно не уместиться целиком."),
]


def main() -> int:
    folder = Path(tempfile.mkdtemp(prefix="transcriber-formats-"))
    problems: list[str] = []

    # --- время в субтитрах ----------------------------------------------------
    edge = stamp(59.9996, comma=True)
    print("59.9996 с в субтитрах:", edge)
    if edge != "00:01:00,000":
        problems.append(f"время округлилось в {edge}, проигрыватель такое не примет")

    # --- txt: два вида оформления ---------------------------------------------
    lines = formats.write("txt", folder / "a.txt", SEGMENTS, layout=LAYOUT_TIMECODES,
                          title="лекция.mp4", meta="large-v3").read_text(encoding="utf-8")
    plain = formats.write("txt", folder / "b.txt", SEGMENTS, layout=LAYOUT_PLAIN,
                          title="лекция.mp4", meta="large-v3").read_text(encoding="utf-8")
    body = plain.split("\n", 2)[2]          # без строки заголовка
    print("txt по строкам: тайм-кодов", lines.count("-->"), "| связный: тайм-кодов",
          len(re.findall(r"\[\d\d:\d\d:\d\d", body)))
    if lines.count("-->") != len(SEGMENTS):
        problems.append("txt по строкам: не у каждого сегмента своё время")
    if re.search(r"\[\d\d:\d\d:\d\d", body):
        problems.append("связный текст с тайм-кодами, а по FR-18 их там быть не должно")

    # --- md -------------------------------------------------------------------
    md = formats.write("md", folder / "c.md", SEGMENTS, layout=LAYOUT_TIMECODES,
                       title="лекция.mp4").read_text(encoding="utf-8")
    print("md: звёздочки экранированы:", r"\*важное\*" in md)
    if r"\*важное\*" not in md:
        problems.append("md: звёздочка из речи станет курсивом")

    # --- docx -----------------------------------------------------------------
    path = formats.write("docx", folder / "d.docx", SEGMENTS, layout=LAYOUT_PLAIN,
                         title="лекция.mp4", meta="large-v3")
    with zipfile.ZipFile(path) as package:
        parts = set(package.namelist())
        document = package.read("word/document.xml")
    needed = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
    print("docx: части", sorted(parts))
    if not needed <= parts:
        problems.append(f"docx: не хватает {sorted(needed - parts)}")
    try:
        root = ElementTree.fromstring(document)
        texts = "".join(t.text or "" for t in root.iter(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
        print("docx: XML разбирается, текст на месте:", "Добрый день" in texts)
        if "Добрый день" not in texts:
            problems.append("docx: текста нет в документе")
    except ElementTree.ParseError as error:
        problems.append(f"docx: XML не разбирается — Word его не откроет ({error})")

    # --- субтитры -------------------------------------------------------------
    srt = formats.write("srt", folder / "e.srt", SEGMENTS, layout="").read_text(encoding="utf-8")
    vtt = formats.write("vtt", folder / "f.vtt", SEGMENTS, layout="").read_text(encoding="utf-8")
    numbers = re.findall(r"^(\d+)\n\d\d:\d\d:\d\d,\d{3} --> ", srt, re.MULTILINE)
    widest = max(len(line) for line in srt.splitlines())
    print("srt: реплик", len(numbers), "| самая длинная строка", widest,
          "| vtt начинается с WEBVTT:", vtt.startswith("WEBVTT"))
    if numbers != ["1", "2", "3"]:
        problems.append(f"srt: нумерация {numbers}, а пустой сегмент должен выпасть")
    if widest > subtitles.LINE_CHARS:
        problems.append(f"srt: строка в {widest} знаков не уместится на экране")
    if not vtt.startswith("WEBVTT"):
        problems.append("vtt: без заголовка WEBVTT браузер его не примет")

    if problems:
        print("ПРОВАЛ:", "; ".join(problems))
        return 1
    print("УСПЕХ: все пять форматов собираются правильно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
