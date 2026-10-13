import QtQuick
import QtQuick.Layouts
import Transcriber
import "."

// Переходы на служебные экраны: Хранилище, Диагностика, Настройки.
// Один набор на все полосы — чтобы порядок и названия нигде не разъехались.
// Открытый сейчас экран отмечен чертой снизу, как вкладка: ссылка на то
// место, где человек и так стоит, сбивает с толку.
RowLayout {
    id: links

    property string current: ""

    signal navigate(string name)

    spacing: Theme.gapButtons

    Repeater {
        model: ["storage", "diagnostics", "settings"]

        delegate: AppButton {
            id: link

            required property string modelData

            text: I18n.strings["nav." + modelData]
            flat_: true
            onClicked: if (links.current !== modelData) links.navigate(modelData)

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: link.leftPadding
                anchors.rightMargin: link.rightPadding
                height: 2
                radius: 1
                color: Theme.accent
                visible: links.current === link.modelData
            }
        }
    }
}
