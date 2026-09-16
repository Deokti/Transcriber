"""Перевод событий ядра в человеческие фразы.

Единственное место в командной строке, где живут слова. Когда появится
окно, у него будет свой такой же файл — а ядро об этом по-прежнему
не узнает (принцип П-1, решение D-4).
"""
from __future__ import annotations

from core.events import Code, Event, Kind, Stage
from core.platform import NO_CUDA_DEVICE, NO_CUDA_LIBS, NO_CUDA_ON_MACOS
from core.timecode import hms

STAGE_NAMES = {
    Stage.DOWNLOAD: "скачивание модели",
    Stage.PROBE: "разбор файла",
    Stage.PREPARE: "подготовка звука",
    Stage.TRANSCRIBE: "распознавание",
    Stage.CHECK: "проверка качества",
    Stage.EXPORT: "выдача документов",
    Stage.CLEANUP: "уборка",
}

VERDICTS = {
    Code.QUALITY_CLEAN: "ЧИСТО",
    Code.QUALITY_MINOR: "мелкие повторы",
    Code.QUALITY_STUCK: "ЕСТЬ ЗАЛИПАНИЯ",
}

DEVICE_REASONS = {
    NO_CUDA_ON_MACOS: "на Mac ускорение недоступно: движок работает с видеокартами "
                      "только через CUDA, а её на Mac не существует",
    NO_CUDA_LIBS: "не найдены библиотеки CUDA (cuBLAS/cuDNN)",
    NO_CUDA_DEVICE: "видеокарта с поддержкой CUDA не обнаружена",
}


def mb(size: float) -> str:
    return f"{size / 1024 / 1024:.0f} МБ"


def render(e: Event) -> str | None:
    """Фраза для события или None, если показывать нечего."""
    d = e.data
    stage = STAGE_NAMES.get(e.stage, "")

    if e.kind is Kind.QUEUE_STARTED:
        return f"В очереди {d['total']} файл(ов)"

    if e.kind is Kind.QUEUE_DONE:
        parts = [f"готово {d['done']}"]
        for key, word in (("skipped", "пропущено"), ("failed", "ошибок"),
                          ("cancelled", "отменено")):
            if d.get(key):
                parts.append(f"{word} {d[key]}")
        return f"Очередь закончена за {d['seconds']/60:.1f} мин: " + ", ".join(parts)

    if e.kind is Kind.JOB_STARTED:
        return f"=== {d['name']} — стадий: {len(d['stages'])}"

    if e.kind is Kind.STAGE_STARTED:
        # У скачивания нет номера в плане стадий: его может и не быть
        return f"[{d['number']}/{d['of']}] {stage}" if d.get("of") else stage

    if e.kind is Kind.STAGE_DONE:
        head = f"[{d['number']}/{d['of']}] " if d.get("of") else ""
        return f"{head}{stage} — завершено за {d['seconds']:.0f} с"

    if e.kind is Kind.PROGRESS and e.stage is Stage.DOWNLOAD:
        return (f"    {100 * d.get('done', 0):5.1f}%  скачано {mb(d.get('bytes', 0))} "
                f"из {mb(d.get('total', 0))}")

    if e.kind is Kind.PROGRESS:
        done = 100 * d.get("done", 0)
        position = hms(d.get("position", 0))
        if "eta" in d:
            return (f"    {done:5.1f}%  аудио {position}  прошло {d['elapsed']/60:.1f} мин  "
                    f"осталось ~{d['eta']/60:.0f} мин  сегментов {d['segments']}")
        return f"    {done:5.1f}%  извлечено {position} из {hms(d.get('total', 0))}"

    if e.kind is Kind.JOB_DONE:
        return "готово"

    return _by_code(e, d, stage)


def _by_code(e: Event, d: dict, stage: str) -> str | None:
    code = e.code
    prefix = {Kind.WARNING: "    [!] ", Kind.FAILED: "ОШИБКА: "}.get(e.kind, "    ")

    if code == Code.SOURCE_INFO:
        kind = "видео" if d["has_video"] else "аудио"
        return f"{prefix}{kind}, {hms(d['duration'])}, {mb(d['size'])}"

    if code == Code.TRACKS_FOUND:
        parts = []
        for t in d["tracks"]:
            bits = [f"a:{t['index']}", t["codec"], f"{t['channels']}ch"]
            if t["lang"]:
                bits.append(t["lang"])
            if t["default"]:
                bits.append("default")
            parts.append(" ".join(str(b) for b in bits))
        return f"{prefix}дорожки: " + " | ".join(parts)

    if code == Code.TRACK_FALLBACK:
        return f"{prefix}дорожки {d['asked']} нет, беру первую (всего {d['available']})"

    if code == Code.FILTERS_APPLIED:
        what = []
        if d.get("denoise"):
            what.append("шумоподавление")
        if d.get("trim_silence"):
            what.append("обрезка тишины по краям")
        if d.get("loudnorm"):
            what.append("выравнивание громкости")
        return f"{prefix}ffmpeg -> WAV 16 кГц моно ({', '.join(what) or 'без обработки'})"

    if code == Code.AUDIO_READY:
        return f"{prefix}звук готов за {d['seconds']:.0f} с ({mb(d['size'])})"

    if code == Code.MODEL_LOADING:
        return f"{prefix}модель {d['model']} на {d['device']} ({d['compute']})..."

    if code == Code.MODEL_READY:
        if d["cached"]:
            return f"{prefix}модель уже в памяти"
        return f"{prefix}модель готова за {d['seconds']:.0f} с"

    if code == Code.LANGUAGE_DETECTED:
        return (f"{prefix}язык {d['language']} ({d['probability']:.2f}), "
                f"длительность {hms(d['duration'])}")

    if code == Code.TRANSCRIBE_DONE:
        return (f"{prefix}распознано: {d['segments']} сегментов, {d['words']} слов "
                f"за {d['seconds']/60:.1f} мин (x{d['speed']:.1f} к реальному времени)")

    if code in VERDICTS:
        lines = [f"{prefix}вердикт: {VERDICTS[code]} — строк {d['lines']}, "
                 f"речь {hms(d['speech'])}, максимальная серия {d['max_run']}, "
                 f"повторов в окне {d['near_repeats']}"]
        for run in d.get("bad_runs", []):
            lines.append(f"        {hms(run['start'])}-{hms(run['end'])}  x{run['count']}  "
                         f"{run['text']!r}")
        return "\n".join(lines)

    if code == Code.GAPS_FOUND:
        return f"{prefix}пропусков длиннее 2 минут: {d['count']}"

    if code == Code.EXPORT_DONE:
        return f"{prefix}-> {d['path']}"

    if code == Code.TEMP_DELETED:
        return f"{prefix}промежуточный WAV удалён ({mb(d['size'])})"
    if code == Code.TEMP_KEPT:
        return f"{prefix}промежуточный WAV оставлен: {d['path']}"
    if code == Code.TEMP_MOVED:
        return f"{prefix}промежуточный WAV перенесён: {d['path']}"
    if code == Code.TEMP_MOVE_FAILED:
        return f"{prefix}не удалось перенести WAV ({d.get('reason')})"

    if code == Code.OUTPUT_EXISTS:
        return (f"{prefix}пропуск {d['name']}: {', '.join(d['formats'])} уже есть "
                f"(--force чтобы перезаписать)")

    if code == Code.STOP_REQUESTED:
        return f"{prefix}доработаю {d.get('current') or 'текущий файл'}, в очереди ещё {d['pending']}"
    if code == Code.CANCEL_REQUESTED:
        return f"{prefix}прерываю, сохраняю посчитанное"
    if code == Code.STOP_UNDONE:
        return f"{prefix}продолжаю работу, в очереди {d['pending']}"
    if code == Code.PARTIAL_SAVED:
        return (f"{prefix}сохранено посчитанное: {d['segments']} сегментов, "
                f"{hms(d['position'])} из {hms(d['total'])}")

    if code == Code.CUDA_READY:
        return f"{prefix}CUDA готова: библиотек загружено {d['loaded']}"
    if code == Code.CUDA_UNAVAILABLE:
        return f"{prefix}CUDA недоступна: нет {', '.join(d.get('missing', []))}"
    if code == Code.DEVICE_FALLBACK:
        reason = DEVICE_REASONS.get(d.get("reason"), d.get("reason", ""))
        return f"{prefix}видеокарта недоступна ({reason}), считаю на процессоре"

    # ошибки
    if code == Code.FFMPEG_MISSING:
        return f"{prefix}не найден ffmpeg. Искал в: " + ", ".join(d.get("searched", [])[:6])
    if code == Code.FFPROBE_FAILED:
        return f"{prefix}ffprobe не смог прочитать файл: {d.get('stderr', '')}"
    if code == Code.FFMPEG_FAILED:
        return f"{prefix}ffmpeg завершился с кодом {d.get('returncode')}: {d.get('stderr', '')}"
    if code == Code.NO_AUDIO_TRACK:
        return f"{prefix}в файле нет звуковой дорожки"
    if code == Code.MODEL_LANGUAGE_MISMATCH:
        alt = ", ".join(d.get("alternatives", [])[:3])
        return (f"{prefix}модель {d['model']} понимает только английский, "
                f"а язык записи — {d['language']}. Подойдут: {alt}")
    if code == Code.MODEL_LOAD_FAILED:
        return f"{prefix}не удалось загрузить модель {d.get('model')}: {d.get('reason')}"
    if code == Code.CANCELLED:
        return f"{prefix}прервано"
    if code == Code.UNEXPECTED:
        return f"{prefix}{d.get('reason')}"

    return f"{prefix}{code} {d}" if code else None
