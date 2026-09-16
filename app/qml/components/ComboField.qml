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

    spacing: Theme.gapLabel

    Text {
        id: caption
        color: root.enabled_ ? Theme.textMuted : Theme.textOff
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

        contentItem: Text {
            leftPadding: 10
            rightPadding: 28
            text: combo.displayText
            font: combo.font
            color: combo.enabled ? Theme.text : Theme.textOff
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: Theme.radiusField
            color: combo.enabled ? Theme.field : Theme.panel
            border.width: 1
            border.color: combo.hovered && combo.enabled ? Theme.lineStrong : Theme.line
            Behavior on border.color { ColorAnimation { duration: Theme.fast } }
        }

        HoverHandler {
            cursorShape: combo.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        }

        indicator: Canvas {
            x: combo.width - width - 10
            y: (combo.height - height) / 2
            width: 10
            height: 6
            onPaint: {
                const ctx = getContext("2d");
                ctx.reset();
                ctx.strokeStyle = combo.enabled ? Theme.textMuted : Theme.textOff;
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(width / 2, height);
                ctx.lineTo(width, 0);
                ctx.stroke();
            }
        }

        delegate: ItemDelegate {
            width: combo.width
            height: Theme.hField
            enabled: !(modelData !== undefined && modelData.disabled === true)
            contentItem: Text {
                text: modelData !== undefined && modelData.text !== undefined
                      ? modelData.text : modelData
                color: parent.enabled ? Theme.text : Theme.textOff
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle {
                color: parent.hovered ? Qt.rgba(Theme.accent.r, Theme.accent.g,
                                                Theme.accent.b, 0.12) : "transparent"
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
                color: Theme.field
                border.color: Theme.line
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
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
    }
}
