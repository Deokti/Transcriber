"""Сборка выпуска: приложение, архив для скачивания и контрольные суммы.

  python tools/build.py              — обычная сборка
  python tools/build.py --cuda       — с поддержкой видеокарты (Windows, Linux)
  python tools/build.py --all        — обе подряд
  python tools/build.py --installer  — плюс установщик, где он бывает
  python tools/build.py --sums       — только пересчитать суммы в release

Собирать можно только для той системы, на которой запущен скрипт:
PyInstaller не умеет кросс-сборку. Поэтому маковский .dmg делается на
маке, а линуксовый архив — на линуксе.

Что получается:

  Windows  Setup.exe (нужен Inno Setup) и zip с распакованной программой
  macOS    .dmg с .app внутри и ярлыком на /Applications
  Linux    tar.gz с папкой программы и .desktop
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import platform as target_platform   # noqa: E402
from core.version import VERSION               # noqa: E402

DIST = ROOT / "dist"
WORK = ROOT / "build"
RELEASE = ROOT / "release"

NAME = "Transcriber"
SYSTEM = target_platform.system_name()          # windows · macos · linux

#: Что кладём рядом с кодом: QML, переводы, значки, каталог сборок ffmpeg.
DATA = [
    ("app/qml", "app/qml"),
    ("app/i18n", "app/i18n"),
    ("app/icons", "app/icons"),
    ("core/deps/catalog.json", "core/deps"),
]

#: Тексты лицензий и документы кладём рядом с программой.
EXTRAS = [("LICENSE", "LICENSE.txt"),
          ("docs/licenses/LGPL-3.0.txt", "LICENSE.Qt.LGPL-3.0.txt"),
          ("README.md", "README.md"),
          ("CHANGELOG.md", "CHANGELOG.md")]

#: PyInstaller не видит эти модули сам: они подтягиваются по имени.
HIDDEN = ["faster_whisper", "ctranslate2", "onnxruntime", "av", "huggingface_hub"]

#: Пакеты, у которых кроме кода есть данные. PyInstaller забирает только код,
#: а faster-whisper держит рядом модель тишины — без неё распознавание падает.
COLLECT = ["faster_whisper"]

#: Что обязано оказаться в готовой папке. Проверяем сразу после сборки: такую
#: пропажу видно только на чужой машине, в середине первой же работы.
REQUIRED = {"модель тишины (VAD)": "silero_*.onnx"}

ICONS = {"windows": "app/icons/build/app.ico", "macos": "app/icons/build/app.icns"}

#: Линуксу нужна запись в меню рабочего стола. Готовый .desktop в архив не
#: положить: в нём обязателен абсолютный путь до программы, а папку
#: распаковывают куда угодно. Поэтому кладём скрипт — он пишет запись на месте.
MENU = """#!/bin/sh
# Добавляет {name} в меню рабочего стола. Программа остаётся там, где лежит,
# скрипт только создаёт запись со ссылкой на неё.
set -e
here=$(cd "$(dirname "$0")" && pwd)
apps="${{XDG_DATA_HOME:-$HOME/.local/share}}/applications"
mkdir -p "$apps"
chmod +x "$here/{binary}"
cat > "$apps/transcriber.desktop" <<DESKTOP
[Desktop Entry]
Name={name}
Comment=Видео и аудио в текст
Exec=$here/{binary}
Icon=$here/_internal/app/icons/build/icon-256.png
Terminal=false
Type=Application
Categories=AudioVideo;Utility;
DESKTOP
echo "готово: $apps/transcriber.desktop"
echo "убрать: rm $apps/transcriber.desktop"
"""


def run(cmd: list[str]) -> None:
    print("  ", Path(cmd[0]).name, " ".join(cmd[1:3]), "…")
    if subprocess.run(cmd, cwd=ROOT).returncode != 0:
        raise SystemExit(f"не получилось: {Path(cmd[0]).name}")


def suffix(with_cuda: bool) -> str:
    """Имя выпуска: система, разрядность и вариант."""
    return f"{target_platform.target()}-{'cuda' if with_cuda else 'cpu'}"


def bundle_name(with_cuda: bool) -> str:
    """Имя самой программы.

    На винде и линуксе к нему приписан вариант сборки: рядом могут лежать
    и процессорная, и с видеокартой. На маке вариант всего один, и суффикс
    в папке «Программы» только мешает — там просто Transcriber.app.
    """
    if SYSTEM == "macos":
        return NAME
    return f"{NAME}-{'cuda' if with_cuda else 'cpu'}"


def build(with_cuda: bool) -> Path:
    target = bundle_name(with_cuda)
    print(f"\n=== сборка {target} для {SYSTEM} ===")
    shutil.rmtree(DIST / target, ignore_errors=True)

    cmd = [str(pyinstaller()), "--noconfirm", "--clean", "--windowed",
           "--name", target,
           "--distpath", str(DIST), "--workpath", str(WORK), "--specpath", str(WORK),
           "--paths", str(ROOT)]

    icon = ICONS.get(SYSTEM)
    if icon and (ROOT / icon).exists():
        cmd += ["--icon", str(ROOT / icon)]

    for source, where in DATA:
        # Разделитель у --add-data свой на каждой системе
        cmd += ["--add-data", f"{ROOT / source}{os.pathsep}{where}"]
    for module in HIDDEN:
        cmd += ["--hidden-import", module]
    for package in COLLECT:
        cmd += ["--collect-data", package]

    if with_cuda:
        # Библиотеки CUDA кладём деревом как есть: их грузит не импорт,
        # а ctypes по пути, поэтому важна раскладка папок.
        libs = site_packages() / "nvidia"
        if not libs.is_dir():
            raise SystemExit("библиотек CUDA нет в окружении — собирать нечего")
        cmd += ["--add-data", f"{libs}{os.pathsep}nvidia"]
    else:
        cmd += ["--exclude-module", "nvidia"]

    cmd.append(str(ROOT / "tools/entry.py"))
    run(cmd)

    folder = app_folder(target)
    check_bundle(folder)
    for source, name in EXTRAS:
        if (ROOT / source).exists():
            shutil.copy2(ROOT / source, folder.parent / name if SYSTEM == "macos"
                         else folder / name)
    return folder


def check_bundle(folder: Path) -> None:
    """Смотрит, что в собранную папку доехали не только модули, но и данные."""
    lost = [what for what, pattern in REQUIRED.items()
            if next(folder.rglob(pattern), None) is None]
    if lost:
        raise SystemExit("в сборке не хватает: " + ", ".join(lost))


def app_folder(target: str) -> Path:
    """Куда PyInstaller сложил программу: на маке это .app, иначе папка."""
    bundle = DIST / f"{target}.app"
    return bundle if SYSTEM == "macos" and bundle.exists() else DIST / target


def pyinstaller() -> Path:
    scripts = ROOT / (".venv/Scripts" if SYSTEM == "windows" else ".venv/bin")
    exe = scripts / ("pyinstaller.exe" if SYSTEM == "windows" else "pyinstaller")
    return exe if exe.exists() else Path("pyinstaller")


def site_packages() -> Path:
    if SYSTEM == "windows":
        return ROOT / ".venv/Lib/site-packages"
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    return ROOT / ".venv/lib" / version / "site-packages"


# --- упаковка под каждую систему --------------------------------------
def pack(folder: Path, with_cuda: bool) -> Path:
    RELEASE.mkdir(exist_ok=True)
    base = f"{NAME}-{VERSION}-{suffix(with_cuda)}"
    if SYSTEM == "macos":
        return pack_dmg(folder, base)
    if SYSTEM == "linux":
        return pack_tar(folder, base)
    return pack_zip(folder, base)


def pack_zip(folder: Path, base: str) -> Path:
    archive = RELEASE / f"{base}.zip"
    archive.unlink(missing_ok=True)
    print(f"   пакую {archive.name} …")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zip_file.write(path, Path(f"{NAME}-{VERSION}") / path.relative_to(folder))
    return archive


def pack_tar(folder: Path, base: str) -> Path:
    archive = RELEASE / f"{base}.tar.gz"
    archive.unlink(missing_ok=True)
    print(f"   пакую {archive.name} …")
    script = folder / "install.sh"
    script.write_text(MENU.format(name=NAME, binary=folder.name), encoding="utf-8")
    script.chmod(0o755)
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(folder, arcname=f"{NAME}-{VERSION}")
    return archive


def pack_dmg(folder: Path, base: str) -> Path:
    """Образ с .app внутри и ярлыком на /Applications — как принято на маке."""
    image = RELEASE / f"{base}.dmg"
    image.unlink(missing_ok=True)

    staging = WORK / "dmg"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    shutil.copytree(folder, staging / folder.name)
    os.symlink("/Applications", staging / "Applications")
    for source, name in EXTRAS:
        if (ROOT / source).exists():
            shutil.copy2(ROOT / source, staging / name)

    print(f"   собираю {image.name} …")
    run(["hdiutil", "create", "-volname", f"{NAME} {VERSION}",
         "-srcfolder", str(staging), "-ov", "-format", "UDZO", str(image)])
    return image


def installer(with_cuda: bool) -> Path | None:
    """Установщик там, где он вообще бывает отдельным файлом.

    На винде он один и собирается из сборки с видеокартой: на машине без
    NVIDIA она просто не находит карту и считает на процессоре. Процессорная
    сборка остаётся лёгким архивом для тех, кому важен вес, — гонять человека
    по вариантам ради полутора гигабайт не стоит.
    """
    if SYSTEM == "windows" and not with_cuda:
        print("   установщик собираем из сборки с CUDA — процессорная уезжает архивом")
        return None
    if SYSTEM == "macos":
        print("   на маке установщик — это сам .dmg")
        return None
    if SYSTEM == "linux":
        print("   на линуксе отдельного установщика не делаем: архив распаковывается куда угодно")
        return None

    iscc = next((p for p in (
        Path.home() / "AppData/Local/Programs/Inno Setup 6/ISCC.exe",
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
    ) if p.exists()), None)
    if iscc is None:
        print("   [!] Inno Setup не найден — установщик пропускаем")
        return None

    # В имени файла варианта нет: установщик один на всех
    name = f"{NAME}-{VERSION}-{target_platform.target()}-setup"
    print(f"   собираю {name}.exe …")
    run([str(iscc), "/Q", f"/DAppVersion={VERSION}", "/DVariant=cuda",
         f"/DSourceDir={DIST / bundle_name(True)}",
         f"/DOutputName={name}",
         str(ROOT / "tools/installer.iss")])
    return RELEASE / f"{name}.exe"


def sums() -> Path:
    """Один файл с суммами на всё, что лежит в release."""
    lines = []
    for path in sorted(RELEASE.iterdir()):
        if path.suffix.lower() in (".zip", ".exe", ".dmg", ".gz"):
            digest = hashlib.sha256()
            with path.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)
            lines.append(f"{digest.hexdigest()}  {path.name}")
            print(f"   {path.name}: {path.stat().st_size / 1024 / 1024:.0f} МБ")

    target = RELEASE / "SHA256SUMS.txt"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main() -> int:
    if "--sums" in sys.argv:
        # Пригодится, когда в release добавили файл с другой машины:
        # маковский образ собирается на маке и приезжает отдельно.
        print("=== контрольные суммы ===")
        print("  ", sums())
        return 0

    if "--all" in sys.argv:
        variants = [False, True]
    elif "--cuda" in sys.argv:
        variants = [True]
    else:
        variants = [False]

    if SYSTEM == "macos" and any(variants):
        # CTranslate2 на маке умеет только процессор (решение D-2)
        print("на macOS сборки с видеокартой не бывает — делаю обычную")
        variants = [False]

    for with_cuda in variants:
        folder = build(with_cuda)
        pack(folder, with_cuda)
        if "--installer" in sys.argv:
            installer(with_cuda)

    print("\n=== контрольные суммы ===")
    print("  ", sums())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
