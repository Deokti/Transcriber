pragma Singleton
import QtQuick

// Как показать человеку то, что ядро отдаёт кодами и числами.
//
// Живёт рядом с темой, а не внутри экрана, потому что нужно всем сразу:
// «Хранилище» показывает те же модели с теми же размерами, что и главный
// экран, и переписывать это во второй раз незачем.
QtObject {

    // Перевод с запасным вариантом. Ключа может не быть — каталог
    // пополняется по ходу дела, — и тогда лучше показать код, чем пустоту.
    function tr(key, fallback) {
        const value = I18n.strings[key]
        return value !== undefined ? value : fallback
    }

    // Код языка в название: ru → Русский. Сам список кодов даёт ядро.
    function languageName(code) {
        return tr("lang." + code, code)
    }

    // «large-v3 · Все языки · 2,9 ГБ · не скачана»
    function modelText(entry) {
        const langs = entry.languages === "en" ? I18n.strings["model.enOnly"]
                                               : I18n.strings["model.multi"]
        const size = decimal(entry.size_mb / 1024, 1) + " " + I18n.strings["unit.gb"]
        const state = entry.downloaded ? "" : " · " + I18n.strings["model.notDownloaded"]
        return entry.id + " · " + langs + " · " + size + state
    }

    // Видеокарту называем по имени, если драйвер его сказал: «NVIDIA RTX 5070 Ti»
    // человеку говорит больше, чем слово «Видеокарта».
    function deviceText(entry) {
        if (entry.id !== "cuda")
            return I18n.strings["asr.device.cpu"]
        return Env.gpuName !== "" ? Env.gpuName : I18n.strings["asr.device.gpu"]
    }

    // То же устройство, но не ответом на «считать на чём»: в строке итогов
    // оно просто называется — «medium · процессор», а не «· Процессоре».
    function deviceName(id) {
        if (id !== "cuda")
            return I18n.strings["asr.device.cpuName"]
        return Env.gpuName !== "" ? Env.gpuName : I18n.strings["asr.device.gpuName"]
    }

    // Длительность словами, а не 01:12:30: в очереди важен порядок величины,
    // а не точная секунда. Секунды показываем только там, где их видно —
    // у коротких записей.
    function duration(seconds) {
        const total = Math.round(seconds || 0)
        const h = Math.floor(total / 3600)
        const m = Math.floor((total % 3600) / 60)
        const s = total % 60
        if (h > 0)
            return h + " " + I18n.strings["unit.hour"] + " " + m + " " + I18n.strings["unit.min"]
        if (m > 0 && s > 0)
            return m + " " + I18n.strings["unit.min"] + " " + s + " " + I18n.strings["unit.sec"]
        if (m > 0)
            return m + " " + I18n.strings["unit.min"]
        return s + " " + I18n.strings["unit.sec"]
    }

    // Между числом и единицей — неразрывный пробел: «3,1» в конце строки
    // и «ГБ» в начале следующей читаются как два разных числа.
    function fileSize(bytes) {
        const kb = (bytes || 0) / 1024
        // «214 ГБ», а не «214,0 ГБ»: у больших чисел десятые — шум
        const gb = kb / 1024 / 1024
        if (gb >= 1)
            return decimal(gb, gb >= 100 ? 0 : 1) + " " + I18n.strings["unit.gb"]
        if (kb >= 1024)
            return Math.round(kb / 1024) + " " + I18n.strings["unit.mb"]
        return Math.round(kb) + " " + I18n.strings["unit.kb"]
    }

    // «Дорожка 2 · Комментарий · 2 кан. · aac» — из того, что сказал ffprobe.
    // Порядок по убыванию пользы: в строке очереди поле узкое, и хвост
    // обрезается. Кодек нужен реже всего, поэтому он последний.
    // Пустые поля пропускаем: у половины записей нет ни названия, ни языка.
    function trackText(track) {
        const parts = [I18n.strings["track.number"].arg(track.index + 1)]
        if (track.title)
            parts.push(track.title)
        if (track.lang && track.lang !== "und")
            parts.push(track.lang)
        if (track.channels)
            parts.push(I18n.strings["track.channels"].arg(track.channels))
        if (track.codec)
            parts.push(track.codec)
        return parts.join(" · ")
    }

    // «около 6 мин»: точность здесь никого не спасает, а мельтешение
    // секунд на восьмидесятиминутном счёте раздражает.
    function roughDuration(seconds) {
        const total = Math.round(seconds || 0)
        if (total >= 90)
            return Math.round(total / 60) + " " + I18n.strings["unit.min"]
        return Math.max(total, 1) + " " + I18n.strings["unit.sec"]
    }

    // Фраза по коду события. Числа берём из данных: ядро отдаёт код и
    // значения, слова живут здесь (принцип П-1).
    function noticeText(notice) {
        const data = notice.data || {}
        const text = tr("notice." + notice.code, notice.code)
        switch (notice.code) {
        case "DEVICE_FALLBACK":
            return text.arg(tr("device.reason." + data.reason, data.reason || ""))
        case "TRACK_FALLBACK":
            return text.arg(data.asked)
        case "OUTPUT_EXISTS":
        case "SEGMENTS_REUSED":
            return text.arg(data.name || "")
        case "OUTPUT_RENAMED":
            return text.arg(data.name || "").arg(data.stem || "")
        case "QUALITY_MINOR":
        case "QUALITY_STUCK":
            return text.arg((data.bad_runs || []).length)
        case "GAPS_FOUND":
            return text.arg(data.count)
        case "PARTIAL_SAVED":
            return text.arg(duration(data.position)).arg(duration(data.total))
        case "MODEL_MISSING":
            return text.arg(data.model || "").arg(fileSize((data.size_mb || 0) * 1024 * 1024))
        case "MODEL_LOAD_FAILED":
        case "MODEL_LANGUAGE_MISMATCH":
            return text.arg(data.model || "")
        case "DOWNLOAD_FAILED":
            return text.arg(data.reason || "")
        case "UNEXPECTED":
            return text.arg(data.reason || "")
        }
        return text
    }

    // Строка журнала запуска: «14:07:12 звук готов за 12 с, 88 МБ».
    // Журнал хранит коды и числа, слова подбираются при показе — поэтому
    // журнал, записанный по-русски, читается и по-английски (принцип П-1).
    // Пустая строка — показывать нечего.
    function logLine(item) {
        const text = logText(item)
        return text ? String(item.time || "").substring(11, 19) + "  " + text : ""
    }

    function logText(item) {
        const d = item.data || {}
        switch (item.kind) {
        case "queue_started":
            return tr("log.queue", "").arg(plural(d.total, I18n.strings["log.file"]))
        case "job_started":
            return tr("log.job", "").arg(d.name || "")
        case "stage_done":
            // Время этапа говорит, где ушли минуты; мгновенные — шум
            return d.seconds >= 1 ? tr("log.stageDone", "").arg(tr("log.stage." + item.stage, item.stage))
                                                            .arg(duration(d.seconds))
                                  : ""
        case "queue_done":
            return tr("log.queueDone", "").arg(duration(d.seconds)).arg(
                ["done", "skipped", "failed", "cancelled"]
                    .filter(function (key) { return key === "done" || d[key] > 0 })
                    .map(function (key) { return tr("log." + key, "").arg(d[key] || 0) })
                    .join(", "))
        case "info":
        case "warning":
        case "failed":
            return logEvent(item.code, d)
        }
        return ""
    }

    function baseName(path) {
        const text = String(path || "")
        return text.substring(Math.max(text.lastIndexOf("/"), text.lastIndexOf("\\")) + 1)
    }

    function logEvent(code, d) {
        switch (code) {
        case "SOURCE_INFO":
            return tr("log.SOURCE_INFO", "").arg(d.name || "")
                .arg(tr(d.has_video ? "log.video" : "log.audio", ""))
                .arg(duration(d.duration) + ", " + fileSize(d.size))
        case "TRACKS_FOUND":
            return tr("log.TRACKS_FOUND", "").arg((d.tracks || []).length)
        case "FILTERS_APPLIED": {
            const what = []
            if (d.denoise && d.denoise !== "off")
                what.push(tr("log.denoise", "").arg(tr("sound.denoise." + d.denoise, d.denoise).toLowerCase()))
            if (d.trim_silence)
                what.push(tr("log.trim", ""))
            if (d.loudnorm)
                what.push(tr("log.loudnorm", ""))
            return tr("log.FILTERS_APPLIED", "").arg(tr("audio." + d.format, d.format || ""))
                .arg(what.length ? what.join(", ") : tr("log.noFilters", ""))
        }
        case "AUDIO_READY":
            return tr("log.AUDIO_READY", "").arg(duration(d.seconds)).arg(fileSize(d.size))
        case "AUDIO_SAVED":
        case "TEMP_MOVED":
            return tr("log." + code, "").arg(baseName(d.path))
        case "EXPORT_DONE":
            return tr("log.EXPORT_DONE", "").arg(baseName(d.path))
        case "TEMP_DELETED":
            return tr("log.TEMP_DELETED", "").arg(fileSize(d.size))
        case "MODEL_LOADING":
            return tr("log.MODEL_LOADING", "").arg(d.model || "").arg(deviceName(d.device))
        case "MODEL_READY":
            return d.cached ? tr("log.MODEL_CACHED", "")
                            : tr("log.MODEL_READY", "").arg(duration(d.seconds))
        case "LANGUAGE_DETECTED":
            return tr("log.LANGUAGE_DETECTED", "").arg(languageName(d.language))
                .arg(Math.round((d.probability || 0) * 100))
        case "TRANSCRIBE_DONE":
            return tr("log.TRANSCRIBE_DONE", "")
                .arg(plural(d.segments, I18n.strings["log.fragment"]))
                .arg(plural(d.words, I18n.strings["log.word"]))
                .arg(duration(d.seconds))
        case "QUALITY_CLEAN":
        case "CUDA_READY":
            return tr("log." + code, "")
        case "CUDA_UNAVAILABLE":
            return tr("log.CUDA_UNAVAILABLE", "").arg((d.missing || []).join(", "))
        case "FFMPEG_FAILED":
        case "FFPROBE_FAILED":
            // Хвост вывода ffmpeg — ради него журнал и открывают
            return noticeText({code: code, data: d}) + lastLine(d.stderr)
        case "MODEL_LOAD_FAILED":
            return noticeText({code: code, data: d}) + (d.reason ? " " + d.reason : "")
        }
        // Остальное говорит теми же словами, что и лента сообщений; а код,
        // которому слов не нашлось, лучше показать как есть, чем потерять.
        return tr("notice." + code, "") !== "" ? noticeText({code: code, data: d}) : (code || "")
    }

    function lastLine(text) {
        const lines = String(text || "").trim().split("\n")
        const tail = lines[lines.length - 1].trim()
        return tail ? " " + tail : ""
    }

    // Дробное число по правилам языка интерфейса: «2,9» по-русски, «2.9»
    // по-английски. toFixed ставит точку всегда, и в русском тексте она режет глаз.
    function decimal(value, digits) {
        return Number(value || 0).toLocaleString(Qt.locale(I18n.language), "f", digits)
    }

    // День словами: «12 сентября», а если сегодня — «сегодня». Месяц по
    // правилам языка интерфейса: Qt сам ставит его в нужный падеж.
    function day(iso) {
        if (!iso)
            return ""
        const when = new Date(iso)
        if (when.toDateString() === new Date().toDateString())
            return I18n.strings["date.today"]
        return Qt.locale(I18n.language).toString(when, "d MMMM")
    }

    // Число со словом в нужной форме: «1 файл», «3 файла», «5 файлов».
    // forms — «один|несколько|много» через черту; у английского вторая и
    // третья совпадают.
    function plural(n, forms) {
        const words = String(forms || "").split("|")
        const ten = n % 10, hundred = n % 100
        let index = 2
        if (I18n.language === "ru") {
            if (ten === 1 && hundred !== 11)
                index = 0
            else if (ten >= 2 && ten <= 4 && (hundred < 12 || hundred > 14))
                index = 1
        } else {
            index = n === 1 ? 0 : 1
        }
        return n + " " + (words[index] || words[words.length - 1] || "")
    }

    // «…\Лекции\Готовое» — человеку нужна папка, а не полный путь
    function folderOf(path) {
        const text = String(path || "")
        const cut = Math.max(text.lastIndexOf("/"), text.lastIndexOf("\\"))
        return cut > 0 ? text.substring(0, cut) : text
    }

    function gigabytes(bytes) {
        return (bytes / 1024 / 1024 / 1024).toFixed(0) + " " + I18n.strings["unit.gb"]
    }
}
