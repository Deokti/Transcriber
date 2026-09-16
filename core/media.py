"""Работа с ffmpeg и ffprobe: поиск программ, разбор файла, извлечение звука.

Отличие от прежнего ffmpeg_tools.py: модуль не печатает и не завершает
процесс. Всё, что может пойти не так, поднимается как CoreError с кодом —
решать, что показать человеку, будет интерфейс.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.events import Cancelled, Code, CoreError

VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts", ".mpg", ".mpeg", ".wmv", ".flv", ".m4v"}
AUDIO_EXT = {".m4a", ".mp3", ".wav", ".ogg", ".opus", ".flac", ".aac", ".wma", ".m4b", ".amr", ".aiff"}
MEDIA_EXT = VIDEO_EXT | AUDIO_EXT

#: Где искать ffmpeg, если его нет ни в папке данных, ни в PATH.
GUESS_DIRS = [
    r"D:\ffmpeg\bin", r"D:\ffmpeg",
    r"C:\ffmpeg\bin", r"C:\ffmpeg",
    r"C:\Program Files\ffmpeg\bin",
    "/usr/local/bin", "/opt/homebrew/bin", "/usr/bin",
]


@dataclass(frozen=True)
class AudioTrack:
    index: int          # номер среди аудиодорожек, для -map 0:a:N
    codec: str
    channels: int
    rate: str
    lang: str
    title: str
    default: bool


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    has_video: bool
    container: str
    audio: list[AudioTrack] = field(default_factory=list)


@dataclass(frozen=True)
class Tools:
    ffmpeg: Path
    ffprobe: Path


def find_tool(name: str, *, extra_dirs: list[Path] | None = None) -> Path | None:
    """Ищет программу: сначала там, куда её скачали мы, потом в системе."""
    import shutil

    exe = name + (".exe" if os.name == "nt" else "")
    candidates: list[Path] = []
    for d in extra_dirs or []:
        candidates += [Path(d) / exe, Path(d) / "bin" / exe]
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    candidates += [Path(d) / exe for d in GUESS_DIRS]
    for c in candidates:
        if c.is_file():
            return c
    return None


def ensure_tools(extra_dirs: list[Path] | None = None) -> Tools:
    ffmpeg = find_tool("ffmpeg", extra_dirs=extra_dirs)
    ffprobe = find_tool("ffprobe", extra_dirs=extra_dirs)
    if not ffmpeg or not ffprobe:
        raise CoreError(Code.FFMPEG_MISSING,
                        searched=[str(d) for d in (extra_dirs or [])] + GUESS_DIRS)
    return Tools(ffmpeg, ffprobe)


def probe(ffprobe: Path, path: Path) -> MediaInfo:
    """Длительность, наличие картинки и список аудиодорожек."""
    cmd = [str(ffprobe), "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise CoreError(Code.FFPROBE_FAILED, path=str(path), stderr=r.stderr.strip()[:300])

    data = json.loads(r.stdout or "{}")
    audio: list[AudioTrack] = []
    video: list[str] = []
    for s in data.get("streams", []):
        if s.get("codec_type") == "audio":
            tags = s.get("tags") or {}
            audio.append(AudioTrack(
                index=len(audio),
                codec=s.get("codec_name") or "?",
                channels=int(s.get("channels") or 0),
                rate=str(s.get("sample_rate") or ""),
                lang=tags.get("language", ""),
                title=tags.get("title", ""),
                default=bool((s.get("disposition") or {}).get("default")),
            ))
        elif s.get("codec_type") == "video" and (s.get("disposition") or {}).get("attached_pic") != 1:
            video.append(s.get("codec_name") or "?")

    fmt = data.get("format") or {}
    try:
        duration = float(fmt.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0

    return MediaInfo(duration=duration, has_video=bool(video),
                     container=fmt.get("format_name", ""), audio=audio)


def build_filters(loudnorm: bool = True, denoise: bool = False) -> str:
    """Цепочка -af. Порядок важен: сначала чистим, потом равняем громкость."""
    chain = []
    if denoise:
        chain.append("highpass=f=80")    # убрать гул ниже речи
        chain.append("afftdn=nf=-25")    # спектральное шумоподавление
    if loudnorm:
        chain.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    return ",".join(chain)


def extract_audio(
    ffmpeg: Path,
    src: Path,
    dst: Path,
    *,
    track: int = 0,
    loudnorm: bool = True,
    denoise: bool = False,
    duration: float = 0.0,
    on_progress: Callable[[float, float], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
    """Вытаскивает звук в WAV 16 кГц моно.

    Именно в этот формат Whisper конвертирует внутри себя в любом случае,
    так что лишней потери качества здесь нет.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(ffmpeg), "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
           "-i", str(src), "-map", f"0:a:{track}?", "-vn", "-sn", "-dn",
           "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le"]
    filters = build_filters(loudnorm, denoise)
    if filters:
        cmd += ["-af", filters]
    cmd += ["-progress", "pipe:1", "-nostats", str(dst)]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    cancelled = False
    try:
        for line in proc.stdout:
            if should_cancel is not None and should_cancel():
                cancelled = True
                proc.terminate()
                break
            if line.startswith("out_time_us=") and on_progress and duration > 0:
                try:
                    current = int(line.split("=", 1)[1]) / 1_000_000
                except ValueError:
                    continue
                on_progress(current, duration)
    finally:
        if proc.stdout:
            proc.stdout.close()
        err = proc.stderr.read() if proc.stderr else ""
        if proc.stderr:
            proc.stderr.close()
        code = proc.wait()

    if cancelled:
        dst.unlink(missing_ok=True)
        raise Cancelled()
    if code != 0 or not dst.exists() or dst.stat().st_size < 1024:
        raise CoreError(Code.FFMPEG_FAILED, returncode=code, stderr=err.strip()[:400])
    return dst


def describe_tracks(tracks: list[AudioTrack]) -> list[dict]:
    """Дорожки в машинном виде — фразу из этого собирает интерфейс."""
    return [{"index": t.index, "codec": t.codec, "channels": t.channels,
             "lang": t.lang, "title": t.title, "default": t.default} for t in tracks]
