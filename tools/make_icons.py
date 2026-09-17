"""Собирает значки приложения из SVG под все три системы.

  python tools/make_icons.py

Читает app/icons/*.svg, раскладывает по размерам и пакует контейнеры:
Windows — .ico, macOS — .icns, Linux — набор png по папкам.

Растеризует Qt, который и так стоит. Контейнеры собираются здесь же, без
посторонних библиотек: и ICO, и ICNS умеют хранить готовые png внутри себя,
а их заголовки занимают полтора десятка строк.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "app" / "icons"
OUT = ROOT / "app" / "icons" / "build"

#: Размеры для Windows и для наборов Linux.
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
PNG_SIZES = (16, 24, 32, 48, 64, 128, 256, 512)

#: Какой файл брать для мелких размеров: у знака есть упрощённый вариант.
SMALL_LIMIT = 24

#: Куски ICNS: код и сторона картинки. Набор такой же, какой складывает
#: маковский iconutil. Ранние коды icp4/icp5/icp6 система понимает через раз,
#: поэтому берём пары «обычный и удвоенный»: ic11 — это 16 точек на экране
#: retina, ic12 — 32, и дальше по той же схеме.
ICNS_TYPES = ((b"ic11", 32), (b"ic12", 64), (b"ic07", 128),
              (b"ic13", 256), (b"ic08", 256), (b"ic14", 512),
              (b"ic09", 512), (b"ic10", 1024))


def render(svg: Path, size: int) -> bytes:
    """SVG -> png нужного размера, возвращает байты файла."""
    from PySide6.QtCore import QBuffer, QByteArray, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(str(svg)).render(painter)
    painter.end()

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data.data())


def write_ico(pngs: dict[int, bytes], target: Path) -> Path:
    """Пакует png в .ico. Размер 256 хранится как есть, это разрешено."""
    sizes = sorted(pngs)
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = len(header) + 16 * len(sizes)
    entries, blobs = b"", b""
    for size in sizes:
        blob = pngs[size]
        side = 0 if size >= 256 else size    # 0 означает 256
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(blob), offset)
        blobs += blob
        offset += len(blob)
    target.write_bytes(header + entries + blobs)
    return target


def write_icns(pngs: dict[int, bytes], target: Path) -> Path:
    """Пакует png в .icns: заголовок, затем куски вида код+длина+данные."""
    chunks = b""
    for code, size in ICNS_TYPES:
        blob = pngs[size]
        chunks += code + struct.pack(">I", len(blob) + 8) + blob
    target.write_bytes(b"icns" + struct.pack(">I", len(chunks) + 8) + chunks)
    return target


def main() -> int:
    main_svg = SRC / "app-icon.svg"
    small_svg = SRC / "app-icon-small.svg"
    if not main_svg.exists():
        print(f"Нет {main_svg} — положите SVG знака туда.")
        return 1
    if not small_svg.exists():
        small_svg = main_svg   # упрощённого нет, обойдёмся основным

    OUT.mkdir(parents=True, exist_ok=True)
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication(sys.argv)   # растеризация требует приложения

    sizes = set(ICO_SIZES) | set(PNG_SIZES) | {side for _, side in ICNS_TYPES}
    pngs = {size: render(small_svg if size <= SMALL_LIMIT else main_svg, size)
            for size in sorted(sizes)}

    for size in PNG_SIZES:
        (OUT / f"icon-{size}.png").write_bytes(pngs[size])
    write_ico({s: pngs[s] for s in ICO_SIZES}, OUT / "app.ico")
    write_icns(pngs, OUT / "app.icns")

    print(f"Готово: {OUT}")
    for path in sorted(OUT.iterdir()):
        print(f"  {path.name:<16} {path.stat().st_size:>8} байт")
    del app
    return 0


if __name__ == "__main__":
    sys.exit(main())
