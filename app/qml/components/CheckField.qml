import QtQuick
import QtQuick.Controls.Basic
import Transcriber
import "."

// Галочка с подписью. Знак рисуем сами: у Basic он чужой обеим темам.
CheckBox {
    id: control

    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBase
    implicitHeight: 24
    spacing: 8

    indicator: Rectangle {
        implicitWidth: 16
        implicitHeight: 16
        x: 0
        y: (control.height - height) / 2
        radius: 3
        color: control.checked ? Theme.accent : Theme.fieldBg
        border.width: 1
        border.color: control.checked ? Theme.accent
                    : control.hovered ? Theme.hoverBorder : Theme.checkBorder
        Behavior on color { ColorAnimation { duration: Theme.fast } }

        CheckMark {
            anchors.centerIn: parent
            width: 11
            height: 11
            visible: control.checked
            color: Theme.accentText
        }
    }

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    contentItem: Text {
        text: control.text
        font: control.font
        color: control.enabled ? Theme.text : Theme.textDisabled
        leftPadding: control.indicator.width + control.spacing
        verticalAlignment: Text.AlignVCenter
    }
}
