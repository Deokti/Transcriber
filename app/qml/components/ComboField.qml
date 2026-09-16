import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import Transcriber

// Подпись над полем плюс выпадающий список — основной кирпич настроек.
ColumnLayout {
    id: root

    property alias label: caption.text
    property alias model: combo.model
    property alias currentIndex: combo.currentIndex
    property string hint: ""              // почему пункт недоступен или что он значит
    property bool enabled_: true

    // Работа по кодам, а не по номеру пункта. Номер привязан к списку надписей,
    // а тот меняется при смене языка — и выбор бы сбрасывался.
    property var values: []               // коды пунктов, в том же порядке
    property string value: ""             // выбранный код

    // Только о выборе человеком: Qt сбрасывает номер и сам, когда меняется
    // список. Если слушать «номер изменился», смена языка перепишет настройку.
    signal chosen(string value)

    spacing: Theme.gapLabel

    onValueChanged: syncIndex()
    Component.onCompleted: syncIndex()

    function syncIndex() {
        if (values.length === 0)
            return
        const index = values.indexOf(value)
        combo.currentIndex = index >= 0 ? index : 0
    }

    Text {
        id: caption
        color: root.enabled_ ? Theme.textMuted : Theme.textDisabled
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
    }

    ComboBox {
        id: combo
        Layout.fillWidth: true
        implicitHeight: Theme.hField
        // Иначе длинный пункт списка растягивает всю колонку
        implicitWidth: 160
        enabled: root.enabled_
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBase

        // Список надписей сменился (например, перевели интерфейс) — Qt обнулил
        // выбор. Возвращаем его по коду, не трогая настройку.
        onModelChanged: Qt.callLater(root.syncIndex)
        onActivated: function (index) {
            if (root.values.length > index)
                root.chosen(root.values[index])
        }

        contentItem: Text {
            leftPadding: 10
            rightPadding: 28
            text: combo.displayText
            font: combo.font
            color: combo.enabled ? Theme.text : Theme.textDisabled
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: Theme.radiusField
            color: combo.enabled ? Theme.fieldBg : Theme.disabledFieldBg
            border.width: 1
            border.color: !combo.enabled ? Theme.disabledFieldBorder
                        : combo.hovered ? Theme.hoverBorder : Theme.fieldBorder
            Behavior on border.color { ColorAnimation { duration: Theme.fast } }
        }

        HoverHandler {
            cursorShape: combo.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        }

        indicator: Item {
            x: combo.width - width - 10
            y: (combo.height - height) / 2
            width: 10
            height: 6

            // Те же две палочки, что и в галочке: цвет привязан, значит
            // стрелка переживает смену темы без перерисовки вручную.
            Rectangle {
                color: combo.enabled ? Theme.textMuted : Theme.textDisabled
                radius: 0.75
                width: 1.5
                height: 7
                x: 1.6
                y: -0.6
                rotation: -45
                transformOrigin: Item.Center
                antialiasing: true
            }
            Rectangle {
                color: combo.enabled ? Theme.textMuted : Theme.textDisabled
                radius: 0.75
                width: 1.5
                height: 7
                x: 6.9
                y: -0.6
                rotation: 45
                transformOrigin: Item.Center
                antialiasing: true
            }
        }

        delegate: ItemDelegate {
            width: combo.width
            height: Theme.hField
            enabled: !(modelData !== undefined && modelData.disabled === true)
            contentItem: Text {
                text: modelData !== undefined && modelData.text !== undefined
                      ? modelData.text : modelData
                color: parent.enabled ? Theme.text : Theme.textDisabled
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle {
                color: parent.hovered ? Theme.navHoverBg : "transparent"
            }
            HoverHandler { cursorShape: Qt.PointingHandCursor }
        }

        popup: Popup {
            y: combo.height + 2
            width: combo.width
            implicitHeight: Math.min(contentItem.implicitHeight + 8, 260)
            padding: 4
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: combo.popup.visible ? combo.delegateModel : null
                ScrollIndicator.vertical: ScrollIndicator {}
            }
            background: Rectangle {
                color: Theme.fieldBg
                border.color: Theme.fieldBorder
                radius: Theme.radiusField
            }
        }
    }

    Text {
        visible: root.hint.length > 0
        Layout.fillWidth: true
        Layout.maximumWidth: Theme.textWidth
        text: root.hint
        wrapMode: Text.WordWrap
        color: Theme.textBody
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
    }
}
