import QtQuick
import QtQuick.Controls.Basic
import Transcriber

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
        color: control.checked ? Theme.accent : Theme.field
        border.width: 1
        border.color: control.checked ? Theme.accent
                    : control.hovered ? Theme.lineStrong : Theme.line
        Behavior on color { ColorAnimation { duration: Theme.fast } }

        Canvas {
            anchors.centerIn: parent
            width: 10
            height: 8
            visible: control.checked
            onPaint: {
                const ctx = getContext("2d");
                ctx.reset();
                ctx.strokeStyle = Theme.onAccent;
                ctx.lineWidth = 2;
                ctx.lineCap = "round";
                ctx.beginPath();
                ctx.moveTo(0, 4);
                ctx.lineTo(3.5, 7.5);
                ctx.lineTo(10, 0.5);
                ctx.stroke();
            }
        }
    }

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    contentItem: Text {
        text: control.text
        font: control.font
        color: control.enabled ? Theme.text : Theme.textOff
        leftPadding: control.indicator.width + control.spacing
        verticalAlignment: Text.AlignVCenter
    }
}
