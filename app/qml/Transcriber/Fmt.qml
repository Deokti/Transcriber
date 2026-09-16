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

    // «large-v3 · Все языки · 2.9 ГБ · не скачана»
    function modelText(entry) {
        const langs = entry.languages === "en" ? I18n.strings["model.enOnly"]
                                               : I18n.strings["model.multi"]
        const size = (entry.size_mb / 1024).toFixed(1) + " " + I18n.strings["unit.gb"]
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

    function fileSize(bytes) {
        const kb = (bytes || 0) / 1024
        if (kb >= 1024 * 1024)
            return (kb / 1024 / 1024).toFixed(1) + " " + I18n.strings["unit.gb"]
        if (kb >= 1024)
            return Math.round(kb / 1024) + " " + I18n.strings["unit.mb"]
        return Math.round(kb) + " " + I18n.strings["unit.kb"]
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
            return text.arg(data.name || "")
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

    function gigabytes(bytes) {
        return (bytes / 1024 / 1024 / 1024).toFixed(0) + " " + I18n.strings["unit.gb"]
    }
}
