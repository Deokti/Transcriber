pragma Singleton
import QtQuick

// Единственное место, где живут цвета, размеры и длительности.
// Значения — из docs/design-tokens.md, снятые с макетов. Правим там, сюда
// переносим. Имена одинаковы в обеих темах: меняются значения, не названия.
QtObject {
    id: theme

    // Тему выставляет приложение: по умолчанию как в системе.
    property bool dark: false

    // --- окно и полосы --------------------------------------------------
    readonly property color windowBg:     dark ? "#1b1a19" : "#f4f2f0"
    readonly property color windowBorder: dark ? "#0f0e0e" : "#bdb8b2"
    readonly property color barBg:        dark ? "#141313" : "#eae7e4"
    readonly property color statusBg:     dark ? "#1f1e1d" : "#efedea"
    readonly property color barDivider:   dark ? "#383634" : "#d9d5d0"

    // --- панели и списки ------------------------------------------------
    readonly property color panelBg:      dark ? "#232221" : "#fbfaf9"
    readonly property color panelBorder:  dark ? "#383634" : "#dcd8d3"
    readonly property color panelDivider: dark ? "#2f2d2c" : "#eceae7"
    readonly property color rowDivider:   dark ? "#2a2928" : "#f0edea"
    readonly property color tableHeadBg:  dark ? "#1f1e1d" : "#f4f2f0"
    readonly property color iconTileBg:   dark ? "#33291f" : "#f3e7dc"

    // --- поля и кнопки --------------------------------------------------
    readonly property color fieldBg:          dark ? "#1f1e1d" : "#ffffff"
    readonly property color fieldBorder:      dark ? "#4a4744" : "#c3beb8"
    readonly property color buttonBg:         dark ? "#2a2827" : "#ffffff"
    readonly property color buttonBorderSoft: dark ? "#3f3c3a" : "#d3cdc6"
    readonly property color checkBorder:      dark ? "#5c5854" : "#9a938c"

    // --- состояния ------------------------------------------------------
    readonly property color hoverBg:             dark ? "#2f2d2c" : "#f7f5f3"
    readonly property color hoverBorder:         dark ? "#6b6661" : "#a89f96"
    readonly property color activeBg:            dark ? "#262423" : "#eeeae6"
    readonly property color navHoverBg:          dark ? "#2a2827" : "#e6e2de"
    readonly property color disabledBg:          dark ? "#262423" : "#e0dcd7"
    readonly property color disabledBorder:      dark ? "#333130" : "#d1ccc6"
    readonly property color disabledFieldBg:     dark ? "#1c1b1a" : "#f0edea"
    readonly property color disabledFieldBorder: dark ? "#2f2d2c" : "#ddd8d2"

    // --- текст ----------------------------------------------------------
    readonly property color text:          dark ? "#ecebe9" : "#1b1a19"
    readonly property color textStrong:    dark ? "#f2f1ef" : "#3d3a37"
    readonly property color textSecondary: dark ? "#c9c5c1" : "#4a4643"
    readonly property color textBody:      dark ? "#b8b3ae" : "#5c5853"
    readonly property color textMuted:     dark ? "#a09b96" : "#6d6864"
    readonly property color textDisabled:  dark ? "#8b8681" : "#a29c95"
    readonly property color textIdle:      dark ? "#8b8681" : "#8d8882"

    // --- акцент, прогресс, ссылки ---------------------------------------
    readonly property color accent:       dark ? "#c9793d" : "#b4642a"
    readonly property color accentText:   dark ? "#1b1a19" : "#ffffff"
    readonly property color accentHover:  dark ? "#d78a50" : "#9d5623"
    readonly property color accentActive: dark ? "#b96a30" : "#8a4a1d"
    readonly property color trackBg:      dark ? "#2f2d2c" : "#e3dfda"
    readonly property color trackBorder:  dark ? "#4a4744" : "#d1ccc6"
    readonly property color linkFg:       dark ? "#c9793d" : "#b4642a"
    readonly property color linkHoverFg:  dark ? "#dc9260" : "#8f4d1e"

    // --- смысловые ------------------------------------------------------
    // Цветом одним смысл не передают: рядом всегда значок и текст.
    readonly property color okFg:     dark ? "#6fbf95" : "#2f7d5b"
    readonly property color okBg:     dark ? "#1c2a23" : "#eef6f1"
    readonly property color okBorder: dark ? "#2f4a3c" : "#b6d2c3"
    readonly property color okText:   dark ? "#cfe6da" : "#2c473a"

    readonly property color warnFg:     dark ? "#d9b45a" : "#8a5a12"
    readonly property color warnBg:     dark ? "#2a2620" : "#faf4e8"
    readonly property color warnBorder: dark ? "#514227" : "#d9c9a8"
    readonly property color warnText:   dark ? "#e8d5a8" : "#5c4a28"
    readonly property color warnRowBg:  dark ? "#241f1a" : "#faf3ec"

    readonly property color errorFg:     dark ? "#e0776a" : "#9c3a28"
    readonly property color errorBg:     dark ? "#2b1e1b" : "#fbeeea"
    readonly property color errorBorder: dark ? "#5c3730" : "#c98d7c"
    readonly property color errorText:   dark ? "#f0c6bd" : "#5c342b"

    // --- шрифты --------------------------------------------------------
    readonly property string fontFamily:
        Qt.platform.os === "windows" ? "Segoe UI Variable Text"
      : Qt.platform.os === "osx"     ? "SF Pro Text"
      : "Noto Sans"
    readonly property string monoFamily:
        Qt.platform.os === "windows" ? "Cascadia Mono"
      : Qt.platform.os === "osx"     ? "SF Mono"
      : "Noto Sans Mono"

    readonly property int fontHuge:    46   // процент во время работы
    readonly property int fontTitle:   26   // заголовок экрана результата
    readonly property int fontSection: 19   // заголовок раздела
    readonly property int fontMessage: 15   // заголовок сообщения
    readonly property int fontStrong:  14   // имена файлов, главная кнопка
    readonly property int fontBase:    13   // поля, кнопки, списки
    readonly property int fontSmall:   12   // подписи, строка состояния
    readonly property int weightSemiBold: 600   // 600 — полужирный, не жирный

    // Строка объяснения не шире 70 символов — примерно столько при 13 px
    readonly property int textWidth: 520

    // --- отступы -------------------------------------------------------
    readonly property int gapLabel:   4     // между подписью и полем
    readonly property int gapButtons: 8     // между кнопками в ряду
    readonly property int gapPanels:  12    // между панелями и колонками
    readonly property int padPanel:   14    // внутри панели
    readonly property int padScreen:  18    // поля экранов работы и результата
    readonly property int padFirst:   24    // поля экрана первого запуска

    // --- размеры -------------------------------------------------------
    readonly property int hField:     32    // поле, выпадающий список
    readonly property int hPrimary:   36    // главная кнопка
    readonly property int hRowButton: 28    // кнопка внутри строки списка
    readonly property int hProgress:  16    // главная полоса прогресса
    readonly property int hRowBar:    6     // полоса в строке очереди
    readonly property int hBar:       52    // полоса инструментов и подвал
    readonly property int hStatus:    26    // строка состояния

    readonly property int radiusField: 4
    readonly property int radiusPanel: 6
    readonly property int radiusWindow: 8

    readonly property int minWidth:  900
    readonly property int minHeight: 620

    // --- движение ------------------------------------------------------
    // Анимация помогает понять, а не украшает: дольше 300 мс раздражает,
    // когда запускаешь программу каждый день.
    readonly property int fast: 120
    readonly property int normal: 180
    readonly property int screenChange: 250
}
