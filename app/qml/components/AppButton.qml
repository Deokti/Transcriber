import QtQuick
import QtQuick.Controls.Basic
import Transcriber

// Кнопка в трёх видах: главная (акцентом), обычная (с рамкой) и плоская
// (без рамки — такими в макете сделаны пункты справа в полосе инструментов).
// Ширина растёт по содержимому: надписи должны переживать перевод (D-4).
Button {
    id: control

    property bool primary: false
    property bool flat_: false

    implicitHeight: primary ? Theme.hPrimary : Theme.hField
    implicitWidth: flat_ ? contentItem.implicitWidth + 20
                         : Math.max(contentItem.implicitWidth + 28, 92)
    font.family: Theme.fontFamily
    font.pixelSize: primary ? Theme.fontStrong : Theme.fontBase
    font.weight: Font.Normal   // 14/400 и 13/400 по шкале из токенов

    contentItem: Text {
        text: control.text
        font: control.font
        color: {
            if (!control.enabled)
                return Theme.textOff
            if (control.primary)
                return Theme.onAccent
            if (control.flat_)
                return control.hovered ? Theme.text : Theme.textMuted
            return Theme.text
        }
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight

        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }

    background: Rectangle {
        radius: Theme.radiusField
        color: {
            if (!control.enabled)
                return control.flat_ ? "transparent" : Theme.panel
            if (control.primary)
                return control.down ? Qt.darker(Theme.accent, 1.15)
                     : control.hovered ? Qt.lighter(Theme.accent, 1.08) : Theme.accent
            if (control.flat_)
                return control.down ? Theme.panel
                     : control.hovered ? Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.06)
                     : "transparent"
            return control.down ? Qt.darker(Theme.buttonFill, 1.06)
                 : control.hovered ? Qt.lighter(Theme.buttonFill, 1.02) : Theme.buttonFill
        }
        border.width: (control.primary || control.flat_) ? 0 : 1
        border.color: control.hovered ? Theme.lineStrong : Theme.line

        Behavior on color { ColorAnimation { duration: Theme.fast } }

        // Qt сам курсор не меняет: без этого рука над кнопкой не появится
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.NoButton
            cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        }
    }
}
