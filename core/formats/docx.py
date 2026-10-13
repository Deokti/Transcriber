"""DOCX — документ Word (решение D-3: только docx, без старого .doc).

Пишем сами, без библиотеки. Docx — это zip из нескольких XML-файлов, и для
текста с абзацами нужно ровно три из них: опись содержимого, ссылка на
документ и сам документ. Библиотека ради этого принесла бы в сборку lxml —
мегабайты, которые человеку ни к чему.

Оформление то же, что у остальных документов: «по строкам» — абзац на
сегмент с серым моментом начала, «связный текст» — абзацы без времени.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from core.asr.base import Segment
from core.formats.text import to_paragraphs
from core.profile import LAYOUT_PLAIN
from core.timecode import stamp

_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
{body}
<w:sectPr/>
</w:body>
</w:document>"""

#: Управляющие символы XML не разрешает вовсе: один такой в тексте — и Word
#: откажется открывать весь документ. Табуляцию и переводы строк оставляем.
_FORBIDDEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

#: Размеры в полупунктах: так их меряет Word.
_TITLE_SIZE = 32       # 16 pt
_META_SIZE = 18        # 9 pt
_GRAY = "808080"


def _clean(text: str) -> str:
    return escape(_FORBIDDEN.sub("", text))


def _run(text: str, *, bold: bool = False, size: int = 0, color: str = "") -> str:
    props = ""
    if bold:
        props += "<w:b/>"
    if color:
        props += f'<w:color w:val="{color}"/>'
    if size:
        props += f'<w:sz w:val="{size}"/>'
    head = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{head}<w:t xml:space="preserve">{_clean(text)}</w:t></w:r>'


def _paragraph(*runs: str) -> str:
    return f"<w:p>{''.join(runs)}</w:p>"


def write(path: Path, segments: list[Segment], *, layout: str,
          title: str = "", meta: str = "") -> Path:
    body: list[str] = []
    if title:
        body.append(_paragraph(_run(title, bold=True, size=_TITLE_SIZE)))
    if meta:
        body.append(_paragraph(_run(meta, size=_META_SIZE, color=_GRAY)))

    if layout == LAYOUT_PLAIN:
        body += [_paragraph(_run(text)) for _started, text in to_paragraphs(segments)]
    else:
        for s in segments:
            text = s.text.strip()
            if text:
                body.append(_paragraph(_run(stamp(s.start) + "  ", color=_GRAY), _run(text)))

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _TYPES)
        package.writestr("_rels/.rels", _RELS)
        package.writestr("word/document.xml", _DOCUMENT.format(body="\n".join(body)))
    return path
