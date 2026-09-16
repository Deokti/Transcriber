import QtQuick
import QtQuick.Layouts
import Transcriber

// Одна стадия в списке хода работы: знак состояния и название.
//
// Знак и цвет идут вместе, а не вместо друг друга: пройденная стадия —
// галочка, текущая — заполненный кружок, будущая — пустой. По одному цвету
// состояние не читается, и это правило из брифа.
RowLayout {
    id: row

    property string state_: "waiting"     // waiting · running · done · failed · cancelled
    property string label: ""

    readonly property bool done: state_ === "done"
    readonly property bool running: state_ === "running"
    readonly property bool broken: state_ === "failed" || state_ === "cancelled"

    spacing: Theme.gapButtons

    Item {
        Layout.preferredWidth: 16
        Layout.preferredHeight: 16
        Layout.alignment: Qt.AlignVCenter

        Rectangle {
            anchors.centerIn: parent
            visible: !row.done
            width: row.running ? 10 : 8
            height: width
            radius: width / 2
            color: row.running ? Theme.accent : "transparent"
            border.width: row.running ? 0 : 1
            border.color: row.broken ? Theme.errorFg : Theme.checkBorder

            // Текущая стадия дышит — так взгляд находит её сразу.
            SequentialAnimation on opacity {
                running: row.running && row.visible
                loops: Animation.Infinite
                NumberAnimation { to: 0.45; duration: 700; easing.type: Easing.InOutQuad }
                NumberAnimation { to: 1.0; duration: 700; easing.type: Easing.InOutQuad }
            }
        }

        CheckMark {
            anchors.centerIn: parent
            visible: row.done
            width: 11
            height: 11
            color: Theme.okFg
        }
    }

    Text {
        Layout.fillWidth: true
        text: row.label
        elide: Text.ElideRight
        color: row.running ? Theme.text
             : row.done ? Theme.textSecondary
             : row.broken ? Theme.errorFg
             : Theme.textIdle
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBase
        font.weight: row.running ? Theme.weightSemiBold : Font.Normal
    }
}
