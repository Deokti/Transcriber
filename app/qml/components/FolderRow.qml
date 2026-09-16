import QtQuick
import QtQuick.Layouts
import Transcriber

// Строка выбора папки: подпись, текущий путь, пояснение и две кнопки.
// Пустое значение — не ошибка, а «как обычно», поэтому показываем, что
// именно будет вместо него.
ColumnLayout {
    id: root

    property string label: ""
    property string hint: ""
    property string value: ""
    property string placeholder: ""

    signal choose()
    signal reset()

    spacing: Theme.gapLabel

    Text {
        text: root.label
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.gapButtons

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Theme.hField
            radius: Theme.radiusField
            color: Theme.fieldBg
            border.width: 1
            border.color: Theme.fieldBorder

            Text {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                verticalAlignment: Text.AlignVCenter
                text: root.value !== "" ? root.value : root.placeholder
                color: root.value !== "" ? Theme.text : Theme.textDisabled
                font.family: root.value !== "" ? Theme.monoFamily : Theme.fontFamily
                font.pixelSize: Theme.fontSmall
                elide: Text.ElideMiddle
            }
        }

        AppButton {
            text: I18n.strings["action.choose"]
            onClicked: root.choose()
        }

        AppButton {
            text: I18n.strings["action.reset"]
            flat_: true
            enabled: root.value !== ""
            onClicked: root.reset()
        }
    }

    Text {
        visible: root.hint !== ""
        Layout.fillWidth: true
        Layout.maximumWidth: Theme.textWidth
        text: root.hint
        wrapMode: Text.WordWrap
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
    }
}
