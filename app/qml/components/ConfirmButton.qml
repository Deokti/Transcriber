import QtQuick
import Transcriber
import "."

// Кнопка для необратимого: первое нажатие спрашивает, второе делает.
// Без модального окна — бриф просит обходиться без них, — но и без
// удаления трёх гигабайт одним случайным щелчком. Если за три секунды
// не подтвердили, кнопка возвращается в прежний вид.
AppButton {
    id: control

    property string confirmText: ""
    property bool armed: false

    signal confirmed()

    // Ширина по более длинной из двух надписей: иначе на «Точно удалить?»
    // кнопка раздувается, и соседи в строке прыгают под курсором.
    implicitWidth: Math.max(plain.width, asking.width) + leftPadding + rightPadding

    contentItem: Text {
        text: control.armed ? control.confirmText : control.text
        font: control.font
        color: !control.enabled ? Theme.textDisabled
             : control.armed ? Theme.errorFg : Theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    TextMetrics { id: plain; font: control.font; text: control.text }
    TextMetrics { id: asking; font: control.font; text: control.confirmText }

    onClicked: {
        if (armed) {
            armed = false
            confirmed()
        } else {
            armed = true
            disarm.restart()
        }
    }
    onEnabledChanged: if (!enabled) armed = false

    Timer {
        id: disarm
        interval: 3000
        onTriggered: control.armed = false
    }
}
