"""Всё, что зависит от операционной системы: пути, папка данных, устройства.

Принцип П-5: различия между системами живут здесь и только здесь. В стадиях
конвейера не должно быть ни одной проверки вида «а мы случайно не на маке».
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from core.events import Code

APP_NAME = "Transcriber"

#: Корень приложения — папка, в которой лежит пакет core.
APP_DIR = Path(__file__).resolve().parent.parent

#: Файл-маркер рядом с приложением включает портативный режим (решение D-5).
PORTABLE_MARKER = "portable"


def system_name() -> str:
    """windows | macos | linux — в терминах, понятных остальному коду."""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def quiet_child() -> dict:
    """Ключи запуска, при которых у дочернего процесса нет своего окна.

    Нужно только на Windows и только в собранной программе: консоли у неё
    нет, поэтому каждый вызов ffmpeg открывает рядом с окном чёрный
    прямоугольник. Держим здесь, а не по месту вызова: разница между
    системами живёт в одном модуле (принцип П-5).
    """
    if system_name() != "windows":
        return {}
    import subprocess

    return {"creationflags": subprocess.CREATE_NO_WINDOW}


def is_packed() -> bool:
    """Собранная программа, а не запуск из исходников."""
    return bool(getattr(sys, "frozen", False))


def is_portable() -> bool:
    return (APP_DIR / PORTABLE_MARKER).exists()


def data_dir() -> Path:
    """Папка данных приложения (решение D-5).

    Портативный режим — рядом с приложением. Обычный — там, где данные
    пользователя положено держать в конкретной системе: это не формальность,
    а то, что позволяет нескольким людям на одном компьютере иметь свои
    настройки, а резервному копированию понимать, что сохранять.
    """
    if is_portable():
        return APP_DIR / "data"

    system = system_name()
    if system == "windows":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME
    if system == "macos":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / APP_NAME


@dataclass(frozen=True)
class Paths:
    """Папки, которыми пользуется приложение."""

    root: Path
    bin: Path
    models: Path
    temp: Path
    logs: Path
    profiles: Path

    def ensure(self) -> "Paths":
        for p in (self.root, self.bin, self.models, self.temp, self.logs, self.profiles):
            p.mkdir(parents=True, exist_ok=True)
        return self


def paths() -> Paths:
    root = data_dir()
    return Paths(
        root=root,
        bin=root / "bin",
        models=root / "models",
        temp=root / "temp",
        logs=root / "logs",
        profiles=root / "profiles",
    )


def free_bytes(path: Path) -> int:
    """Сколько свободно на диске, где лежит path. 0 — выяснить не удалось."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free
    except OSError:
        return 0


# --- CUDA на Windows и Linux ------------------------------------------------
#: Итог подключения CUDA. Считается один раз: загруженные в процесс
#: библиотеки никуда не деваются, а искать их заново при каждом опросе
#: машины — сотня миллисекунд в потоке окна.
_cuda_state: tuple[bool, dict] | None = None


def prepare_cuda(emit=None) -> tuple[bool, dict]:
    """Подключает cuBLAS и cuDNN и говорит, готова ли видеокарта.

    Самое хрупкое место всей системы. CTranslate2 грузит эти библиотеки
    отложенно, в обход обычного поиска DLL, поэтому мало добавить папки
    в список поиска — нужно загрузить их в процесс явно.

    Возвращает (готова, подробности). Текста не возвращает: подробности
    машинные, фразу собирает интерфейс.
    """
    global _cuda_state
    if _cuda_state is None:
        _cuda_state = _attach_cuda()
    ok, info = _cuda_state
    if emit is not None:
        from core.events import Event, Kind

        emit(Event(Kind.INFO, code=Code.CUDA_READY if ok else Code.CUDA_UNAVAILABLE, data=info))
    return ok, info


def _attach_cuda() -> tuple[bool, dict]:
    info: dict = {"system": system_name(), "dll_dirs": 0, "loaded": 0, "missing": []}
    if system_name() != "windows":
        # На Linux библиотеки находит сам загрузчик, на маке CUDA не существует.
        return True, info

    dll_dirs, dll_files = _cuda_libraries(_cuda_roots())
    for folder in dll_dirs:
        try:
            os.add_dll_directory(folder)
        except OSError:
            pass
    if dll_dirs:
        os.environ["PATH"] = os.pathsep.join(dll_dirs) + os.pathsep + os.environ.get("PATH", "")

    loaded = _load_dlls([p for p in dll_files
                         if os.path.basename(p).lower().startswith(("cublas", "cudnn", "cudart"))])
    names = {os.path.basename(p).lower() for p in loaded}
    missing = [lib for lib in ("cublas", "cudnn") if not any(n.startswith(lib) for n in names)]

    info.update(dll_dirs=len(dll_dirs), loaded=len(loaded), missing=missing)
    return not missing, info


def _cuda_roots() -> list[str]:
    """Где могут лежать библиотеки: пакет nvidia, папка сборки, site-packages, torch."""
    roots: list[str] = []
    try:
        import nvidia  # пакет-пространство имён: __file__ пустой, берём __path__

        roots.extend(list(getattr(nvidia, "__path__", []) or []))
    except ImportError:
        pass
    if not roots:
        # В собранном виде пакета нет, а папка с библиотеками лежит рядом.
        packed = bundle_dir() / "nvidia"
        if packed.is_dir():
            roots.append(str(packed))
    if not roots:
        import site

        for sp in {*site.getsitepackages(), site.getusersitepackages()}:
            candidate = Path(sp) / "nvidia"
            if candidate.is_dir():
                roots.append(str(candidate))
    try:  # запасной источник тех же библиотек — сборка PyTorch с CUDA
        import torch

        torch_lib = Path(torch.__file__).parent / "lib"
        if torch_lib.is_dir():
            roots.append(str(torch_lib))
    except Exception:
        pass
    return roots


def _cuda_libraries(roots: list[str]) -> tuple[list[str], list[str]]:
    """Папки с DLL и сами DLL под перечисленными корнями."""
    dll_dirs: list[str] = []
    dll_files: list[str] = []
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            dlls = [f for f in filenames if f.lower().endswith(".dll")]
            if dlls:
                dll_dirs.append(dirpath)
                dll_files += [os.path.join(dirpath, f) for f in dlls]
    return dll_dirs, dll_files


def _load_dlls(targets: list[str]) -> set[str]:
    """Грузит библиотеки в процесс. Несколько проходов: они зависят друг от друга."""
    import ctypes

    loaded: set[str] = set()
    for _ in range(4):
        progress = False
        for path in targets:
            if path in loaded:
                continue
            try:
                ctypes.WinDLL(path)
                loaded.add(path)
                progress = True
            except OSError:
                pass
        if not progress:
            break
    return loaded


@dataclass(frozen=True)
class Device:
    """Вариант устройства для интерфейса.

    Недоступное не прячется, а показывается выключенным с причиной
    (требование FR-11): иначе человек ищет то, чего нет.
    """

    id: str                    # cuda | cpu
    available: bool
    reason: str | None = None  # код причины, если недоступно


#: Причина, по которой на маке нет выбора видеокарты.
NO_CUDA_ON_MACOS = "NO_CUDA_ON_MACOS"
NO_CUDA_LIBS = "NO_CUDA_LIBS"
NO_CUDA_DEVICE = "NO_CUDA_DEVICE"
NO_CUDA_IN_BUILD = "NO_CUDA_IN_BUILD"


def cuda_device_count() -> int:
    try:
        import ctranslate2

        return int(ctranslate2.get_cuda_device_count())
    except Exception:
        return 0


def gpu_name() -> str:
    """Название видеокарты, как его показывает драйвер. Пусто — не спросили."""
    if system_name() == "macos":
        return ""
    import subprocess

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5, **quiet_child())
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip().splitlines()[0].strip() if result.returncode == 0 else ""


def devices() -> list[Device]:
    """Что можно выбрать на этой машине и почему нельзя остальное."""
    cpu = Device("cpu", True)

    if system_name() == "macos":
        # Решение D-2: движок умеет работать с видеокартами только через CUDA,
        # а CUDA бывает только у NVIDIA, то есть не на маке.
        return [Device("cuda", False, NO_CUDA_ON_MACOS), cpu]

    ok, _ = prepare_cuda()
    if not ok:
        # Из исходников это значит «доставьте библиотеки», а в собранной
        # программе — «у этой сборки нет поддержки видеокарты»: библиотеки
        # туда либо положили при сборке, либо нет, и человек их не доставит.
        reason = NO_CUDA_IN_BUILD if is_packed() else NO_CUDA_LIBS
        return [Device("cuda", False, reason), cpu]
    if cuda_device_count() < 1:
        return [Device("cuda", False, NO_CUDA_DEVICE), cpu]
    return [Device("cuda", True), cpu]


def bundle_dir() -> Path:
    """Корень файлов, которые лежат рядом с кодом: qml, переводы, каталоги.

    Из исходников это корень репозитория. В собранном виде PyInstaller
    распаковывает их к себе и говорит адрес в sys._MEIPASS.
    """
    packed = getattr(sys, "_MEIPASS", None)
    return Path(packed) if packed else Path(__file__).resolve().parent.parent


def target() -> str:
    """Система и разрядность одной строкой: windows-amd64, macos-arm64.

    По этому ключу в `core/deps/catalog.json` лежит адрес сборки ffmpeg.
    """
    import platform as std

    machine = std.machine().lower()
    arch = {"amd64": "amd64", "x86_64": "amd64",
            "arm64": "arm64", "aarch64": "arm64"}.get(machine, machine)
    system = system_name()
    if system == "macos":
        # У маков две ветки: Apple Silicon и старые интеловские
        return "macos-arm64" if arch == "arm64" else "macos-x86_64"
    return f"{system}-{arch}"


def open_file(path) -> None:
    """Открывает файл тем, чем система открывает такие файлы."""
    import subprocess

    target = str(path)
    system = system_name()
    if system == "windows":
        os.startfile(target)                      # штатный способ Windows
    elif system == "macos":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


def reveal_file(path) -> None:
    """Показывает файл в проводнике — выделенным, а не просто папку."""
    import subprocess

    target = Path(path)
    system = system_name()
    if system == "windows":
        subprocess.Popen(["explorer", "/select,", str(target)])
    elif system == "macos":
        subprocess.Popen(["open", "-R", str(target)])
    else:
        # У линуксовых проводников общего способа выделить файл нет —
        # открываем папку, это честнее, чем угадывать файловый менеджер.
        subprocess.Popen(["xdg-open", str(target.parent)])


def usable_device(device: str) -> tuple[str, str]:
    """Что из выбранного действительно доступно.

    Возвращает устройство и причину подмены; пустая причина — подмены не
    было. Недоступная видеокарта не повод падать: считаем на процессоре и
    говорим почему (FR-11). Причина — код, слова подберёт интерфейс.
    """
    if device != "cuda":
        return device, ""
    for item in devices():
        if item.id == "cuda" and not item.available:
            return "cpu", item.reason or NO_CUDA_DEVICE
    return device, ""


def default_device() -> str:
    for d in devices():
        if d.id == "cuda" and d.available:
            return "cuda"
    return "cpu"


def default_compute(device: str) -> str:
    return "float16" if device == "cuda" else "int8"


def default_model(device: str) -> str:
    """На процессоре large-v3 считает дольше, чем длится запись (FR-15)."""
    return "large-v3" if device == "cuda" else "medium"
