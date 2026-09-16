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

    function gigabytes(bytes) {
        return (bytes / 1024 / 1024 / 1024).toFixed(0) + " " + I18n.strings["unit.gb"]
    }
}
