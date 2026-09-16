import QtQuick
import QtQuick.Window
import Transcriber
import "screens"

// Окно и переключение экранов. Рамка системная: своя ломает привычные
// жесты, особенно на маке.
Window {
    id: root

    width: 1080
    height: 720
    minimumWidth: Theme.minWidth
    minimumHeight: Theme.minHeight
    visible: true
    title: "Transcriber"
    color: Theme.window

    // Тёмная тема включается по системе; переключатель будет в настройках.
    Component.onCompleted: Theme.dark =
        forcedTheme === "dark" ? true
      : forcedTheme === "light" ? false
      : (Qt.styleHints.colorScheme === Qt.Dark)

    MainScreen {
        anchors.fill: parent
    }
}
