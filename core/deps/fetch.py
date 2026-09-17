"""Скачивание ffmpeg: каталог сборок, загрузка, распаковка, проверка.

Программе нужны два файла — ffmpeg и ffprobe. Где их взять, зависит от
системы и разрядности, поэтому адреса лежат в `catalog.json` рядом, а не
в коде: сборки переезжают чаще, чем меняется эта логика.

Контрольная сумма есть не у всех источников. Где её публикуют — сверяем,
где нет — проверяем скачанное запуском `-version`: это не защита от
подмены, а проверка, что файл целый и работает.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core import platform
from core.events import Cancelled, Code, CoreError

CATALOG = platform.bundle_dir() / "core" / "deps" / "catalog.json"

#: Что ищем в архиве. Внутри сборок это лежит на разной глубине, поэтому
#: берём по имени файла, а не по пути.
WANTED = {"ffmpeg", "ffmpeg.exe", "ffprobe", "ffprobe.exe"}

#: Качаем кусками, чтобы показывать прогресс и успевать услышать отмену.
CHUNK = 256 * 1024

Progress = Callable[[int, int], None]
Cancel = Callable[[], bool]


@dataclass(frozen=True)
class Build:
    """Откуда и что качать для этой системы."""

    key: str
    source: str
    license: str
    size_mb: int
    note: str
    assets: list[dict]


def catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def build_for(key: str) -> Build:
    """Сборка для ключа вида «windows-amd64». Нет такой — CoreError."""
    entry = catalog().get(key)
    if not entry:
        raise CoreError(Code.DOWNLOAD_FAILED, reason="no_build_for_platform", platform=key)
    return Build(key=key, source=entry["source"], license=entry["license"],
                 size_mb=entry.get("size_mb", 0), note=entry.get("note", ""),
                 assets=entry["assets"])


def get_ffmpeg(bin_dir, key: str, *, on_progress: Progress | None = None,
               should_cancel: Cancel | None = None) -> list[Path]:
    """Приносит ffmpeg и ffprobe в указанную папку. Возвращает пути."""
    build = build_for(key)
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    temp = bin_dir / "_download"
    temp.mkdir(exist_ok=True)

    total_hint = build.size_mb * 1024 * 1024
    done_before = 0
    made: list[Path] = []

    try:
        for asset in build.assets:
            url = _resolve(asset)
            archive = temp / url.split("/")[-1].split("?")[0]

            def report(done: int, total: int) -> None:
                if on_progress:
                    on_progress(done_before + done, max(done_before + total, total_hint))

            _download(url, archive, report, should_cancel)
            if asset.get("sha256_url"):
                _check_sum(archive, asset["sha256_url"])
            done_before += archive.stat().st_size
            made += _unpack(archive, bin_dir, asset["kind"])

        if not made:
            raise CoreError(Code.DOWNLOAD_FAILED, reason="nothing_extracted", source=build.source)
        _verify(made)
        return made
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _resolve(asset: dict) -> str:
    """Адрес архива: либо прямой, либо через справку источника."""
    if asset.get("url"):
        return asset["url"]

    with urllib.request.urlopen(asset["api"], timeout=30) as response:
        info = json.loads(response.read().decode("utf-8"))
    url = (info.get("download", {}).get("zip", {}) or {}).get("url")
    if not url:
        raise CoreError(Code.DOWNLOAD_FAILED, reason="no_url_in_api", api=asset["api"])
    return url


def _download(url: str, target: Path, on_progress: Progress, should_cancel: Cancel | None) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Transcriber"})
    with urllib.request.urlopen(request, timeout=60) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with target.open("wb") as file:
            while True:
                if should_cancel is not None and should_cancel():
                    raise Cancelled(stage="download")
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                file.write(chunk)
                done += len(chunk)
                on_progress(done, total)


def _check_sum(archive: Path, sha256_url: str) -> None:
    with urllib.request.urlopen(sha256_url, timeout=30) as response:
        expected = response.read().decode("utf-8").split()[0].strip().lower()

    digest = hashlib.sha256()
    with archive.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    if digest.hexdigest() != expected:
        archive.unlink(missing_ok=True)
        raise CoreError(Code.DOWNLOAD_FAILED, reason="checksum_mismatch", file=archive.name)


def _unpack(archive: Path, bin_dir: Path, kind: str) -> list[Path]:
    """Достаёт из архива только ffmpeg и ffprobe, кладёт их плоско."""
    made: list[Path] = []

    if kind == "zip":
        with zipfile.ZipFile(archive) as zip_file:
            for member in zip_file.namelist():
                name = member.rsplit("/", 1)[-1]
                if name.lower() in WANTED:
                    made.append(_write(bin_dir / name, zip_file.read(member)))
    elif kind == "tar.xz":
        with tarfile.open(archive, "r:xz") as tar:
            for member in tar.getmembers():
                name = member.name.rsplit("/", 1)[-1]
                if member.isfile() and name.lower() in WANTED:
                    source = tar.extractfile(member)
                    if source is not None:
                        made.append(_write(bin_dir / name, source.read()))
    else:
        raise CoreError(Code.DOWNLOAD_FAILED, reason="unknown_archive", kind=kind)

    return made


def _write(target: Path, data: bytes) -> Path:
    target.write_bytes(data)
    target.chmod(0o755)     # на маке и линуксе иначе не запустится
    return target


def _verify(files: list[Path]) -> None:
    """Проверяем, что скачанное вообще работает."""
    for path in files:
        if "ffmpeg" not in path.name.lower():
            continue
        try:
            result = subprocess.run([str(path), "-version"], capture_output=True,
                                    text=True, timeout=30)
        except OSError as e:
            raise CoreError(Code.DOWNLOAD_FAILED, reason="not_runnable",
                            file=path.name, error=repr(e)) from e
        if result.returncode != 0 or "ffmpeg version" not in result.stdout:
            raise CoreError(Code.DOWNLOAD_FAILED, reason="bad_binary", file=path.name)
