import QtQuick
import QtQuick.Controls.Basic
import Transcriber

// Кнопка в трёх видах: главная (акцентом), обычная (с рамкой) и плоская
// (без фона — такими в макете сделаны пункты справа в полосе инструментов).
//
// Цвета меняются мгновенно, без плавных переходов. Переход в 120 мс на
// наведении и нажатии читается как вспышка, если состояние меняется быстро,
// а на кнопке это происходит постоянно: нажал, отпустил, увёл курсор.
Button {
    id: control

    property bool primary: false
    property bool flat_: false

    // Ширину считает сам Control из содержимого и полей — своя формула
    // от contentItem умеет дёргать раскладку на каждое изменение состояния.
    leftPadding: flat_ ? 10 : 14
    rightPadding: leftPadding
    implicitWidth: Math.max(implicitContentWidth + leftPadding + rightPadding,
                            flat_ ? 0 : 92)
    implicitHeight: primary ? Theme.hPrimary : Theme.hField

    font.family: Theme.fontFamily
    font.pixelSize: primary ? Theme.fontStrong : Theme.fontBase
    font.weight: Font.Normal      // 14/400 и 13/400 по шкале из токенов

    contentItem: Text {
        text: control.text
        font: control.font
        color: !control.enabled ? Theme.textOff
             : control.primary ? Theme.onAccent
             : control.flat_ && !control.hovered ? Theme.textMuted
             : Theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: Theme.radiusField
        border.width: (control.primary || control.flat_) ? 0 : 1
        border.color: control.hovered ? Theme.lineStrong : Theme.line
        color: {
            if (!control.enabled)
                return control.flat_ ? "transparent" : Theme.panel
            if (control.primary)
                return control.down ? Qt.darker(Theme.accent, 1.15)
                     : control.hovered ? Qt.lighter(Theme.accent, 1.08)
                     : Theme.accent
            if (control.flat_)
                return control.down ? Theme.line
                     : control.hovered ? Theme.panel
                     : "transparent"
            return control.down ? Theme.line
                 : control.hovered ? Theme.panel
                 : Theme.buttonFill
        }
    }

    // Курсор ставит обработчик, а не область мыши: область забирает наведение
    // у самой кнопки, и тогда состояние начинает скакать.
    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}
