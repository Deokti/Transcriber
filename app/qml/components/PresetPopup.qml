import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import Transcriber
import "."

// «Сохранить пресет»: имя и кнопка. Имя занято — говорим, что сохраним
// поверх. Удаляют пресет не здесь, а в полосе сверху, рядом с выбором:
// искать удаление в окне «Сохранить» никто не стал бы.
Popup {
    id: popup

    readonly property string name: field.text.trim()
    // Список пресетов в выражении нарочно: вызов сам по себе привязку не
    // будит, а после сохранения или удаления ответ меняется.
    readonly property bool taken: Task.presets.length >= 0 && name !== "" && Task.presetExists(name)
    property bool failed: false

    function save() {
        if (name === "")
            return
        failed = !Task.savePreset(name)
        if (!failed)
            close()
    }

    modal: true
    focus: true
    anchors.centerIn: Overlay.overlay
    width: Math.min(440, parent ? parent.width - 40 : 440)
    padding: 20
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    onOpened: {
        failed = false
        field.text = Task.preset
        field.selectAll()
        field.forceActiveFocus()
    }

    background: Rectangle {
        color: Theme.panelBg
        border.color: Theme.panelBorder
        border.width: 1
        radius: Theme.radiusPanel
    }

    Overlay.modal: Rectangle {
        color: Theme.dark ? "#99000000" : "#40000000"
    }

    contentItem: ColumnLayout {
        spacing: 12

        SectionTitle {
            text: I18n.strings["preset.saveTitle"]
            font.pixelSize: Theme.fontMessage
        }

        Text {
            Layout.fillWidth: true
            text: I18n.strings["preset.saveHint"]
            color: Theme.textBody
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.WordWrap
        }

        TextField {
            id: field
            Layout.fillWidth: true
            implicitHeight: Theme.hField
            maximumLength: 80
            selectByMouse: true
            placeholderText: I18n.strings["preset.placeholder"]
            placeholderTextColor: Theme.textMuted
            color: Theme.text
            selectionColor: Theme.accent
            selectedTextColor: Theme.accentText
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBase
            leftPadding: 10
            rightPadding: 10
            background: Rectangle {
                color: Theme.fieldBg
                border.color: field.activeFocus ? Theme.accent : Theme.fieldBorder
                border.width: 1
                radius: Theme.radiusField
            }
            onAccepted: popup.save()
        }

        Text {
            Layout.fillWidth: true
            visible: popup.taken || popup.failed
            text: popup.failed ? I18n.strings["preset.failed"]
                               : I18n.strings["preset.taken"].arg(popup.name)
            color: popup.failed ? Theme.errorFg : Theme.warnFg
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 4
            spacing: Theme.gapButtons

            Item { Layout.fillWidth: true }
            AppButton {
                text: I18n.strings["action.cancel"]
                onClicked: popup.close()
            }
            AppButton {
                primary: true
                enabled: popup.name !== ""
                text: popup.taken ? I18n.strings["preset.replace"] : I18n.strings["action.save"]
                onClicked: popup.save()
            }
        }
    }
}
