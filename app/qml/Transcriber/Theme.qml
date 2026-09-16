pragma Singleton
import QtQuick

// Единственное место, где живут цвета, размеры и длительности.
// Значения взяты из docs/design-tokens.md — правим их там, а сюда переносим.
QtObject {
    id: theme

    // Тему выставляет приложение: по умолчанию как в системе.
    property bool dark: false

    // --- цвета ---------------------------------------------------------
    readonly property color window:      dark ? "#1b1a19" : "#f4f2f0"
    readonly property color panel:       dark ? "#232221" : "#fbfaf9"
    readonly property color field:       dark ? "#1f1e1d" : "#ffffff"
    readonly property color line:        dark ? "#383634" : "#d9d5d0"
    readonly property color lineStrong:  dark ? "#4a4744" : "#c3beb8"
    readonly property color text:        dark ? "#ecebe9" : "#1b1a19"
    readonly property color textMuted:   dark ? "#a09b96" : "#6d6864"
    readonly property color textOff:     dark ? "#8b8681" : "#a29c95"
    readonly property color accent:      dark ? "#c9793d" : "#b4642a"
    readonly property color onAccent:    dark ? "#1b1a19" : "#ffffff"
    readonly property color ok:          dark ? "#6fbf95" : "#2f7d5b"
    readonly property color warn:        dark ? "#d9b45a" : "#8a5a12"
    readonly property color error:       dark ? "#e0776a" : "#9c3a28"

    // Фоны и рамки для сообщений: цветом одним смысл не передают
    readonly property color warnFill:    dark ? "#2a2620" : "#faf4e8"
    readonly property color warnLine:    dark ? "#4a4030" : "#d9c9a8"
    readonly property color errorFill:   dark ? "#2b1e1b" : "#fbeeea"
    readonly property color errorLine:   dark ? "#5a332c" : "#c98d7c"
    readonly property color buttonFill:  dark ? "#2a2827" : "#ffffff"

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
    readonly property int weightBold:  600

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
