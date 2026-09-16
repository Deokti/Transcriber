import QtQuick
import QtQuick.Window
import Transcriber
import "screens"

// Окно и переключение экранов. Рамка системная: своя ломает привычные
// жесты, особенно на маке.
Window {
    id: root

    property string screen: "main"

    width: 1080
    height: 720
    minimumWidth: Theme.minWidth
    minimumHeight: Theme.minHeight
    visible: true
    title: "Transcriber"
    color: Theme.windowBg

    // Тема приходит из настроек: там же живёт вариант «как в системе».
    // forcedTheme — только для снимков при разработке.
    Binding {
        target: Theme
        property: "dark"
        value: forcedTheme === "dark" ? true
             : forcedTheme === "light" ? false
             : Settings.isDark
    }

    MainScreen {
        anchors.fill: parent
        visible: root.screen === "main"
        onOpenSettings: root.screen = "settings"
    }

    SettingsScreen {
        anchors.fill: parent
        visible: root.screen === "settings"
        onBack: root.screen = "main"
    }

    ProgressScreen {
        anchors.fill: parent
        visible: root.screen === "progress"
        onDone: root.screen = "main"
    }

    // Экран переключает не кнопка, а сам факт начала работы: запуск может
    // и не случиться — например, не нашёлся ffmpeg.
    Connections {
        target: Run
        function onStarted() { root.screen = "progress" }
    }
}
