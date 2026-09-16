import QtQuick
import QtQuick.Controls.Basic
import Transcriber

// Кнопка в двух видах: главная (акцентом) и обычная.
// Ширина растёт по содержимому — надписи переживают перевод (решение D-4).
Button {
    id: control

    property bool primary: false
    property int height_: primary ? Theme.hPrimary : Theme.hField

    implicitHeight: height_
    implicitWidth: Math.max(contentItem.implicitWidth + 28, 92)
    font.family: Theme.fontFamily
    font.pixelSize: primary ? Theme.fontStrong : Theme.fontBase
    font.weight: primary ? Theme.weightBold : Font.Normal

    contentItem: Text {
        text: control.text
        font: control.font
        color: !control.enabled ? Theme.textOff
             : control.primary ? Theme.onAccent : Theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: Theme.radiusField
        color: {
            if (!control.enabled)
                return Theme.panel
            if (control.primary)
                return control.down ? Qt.darker(Theme.accent, 1.15)
                     : control.hovered ? Qt.lighter(Theme.accent, 1.08) : Theme.accent
            return control.down ? Qt.darker(Theme.buttonFill, 1.06)
                 : control.hovered ? Qt.lighter(Theme.buttonFill, 1.02) : Theme.buttonFill
        }
        border.width: control.primary ? 0 : 1
        border.color: control.hovered ? Theme.lineStrong : Theme.line
        opacity: control.enabled ? 1 : 0.6

        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
}
