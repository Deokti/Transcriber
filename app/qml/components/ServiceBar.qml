import QtQuick
import QtQuick.Layouts
import Transcriber
import "."

// Полоса служебных экранов, как в прототипе: «К главному экрану» слева,
// переходы справа. Хранилище, Диагностика и Настройки — соседи: между ними
// ходят напрямую, не возвращаясь на главный.
Rectangle {
    id: bar

    property string current: ""
    // Куда вернёт кнопка слева: на главный или к результату. Подпись честно
    // говорит, куда именно, — «К главному» с экрана результата обманула бы.
    property string origin: "main"

    signal home()
    signal navigate(string name)

    implicitHeight: Theme.hBar
    color: Theme.barBg

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.barDivider
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.gapPanels
        anchors.rightMargin: Theme.gapPanels
        spacing: Theme.gapButtons

        AppButton {
            text: "‹  " + I18n.strings[bar.origin === "result" ? "nav.toResult" : "nav.home"]
            onClicked: bar.home()
        }

        Item { Layout.fillWidth: true }

        NavLinks {
            current: bar.current
            onNavigate: function (name) { bar.navigate(name) }
        }
    }
}
