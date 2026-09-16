import QtQuick
import QtQuick.Layouts
import Transcriber

// Строка очереди: имя записи, что о ней уже известно, и кнопка убрать.
// Данные приходят готовыми из моста Queue — здесь только показ.
//
// Пока файл разбирается, строка не пустует и не прыгает: имя видно сразу,
// на месте длительности стоит «читаю…», и высота не меняется, когда данные
// приезжают.
Item {
    id: row

    property var entry: ({})
    property int position: 0
    signal removeRequested()
    signal trackChosen(int track)

    readonly property bool failed: entry.state === "failed"
    readonly property bool reading: entry.state === "probing"

    implicitHeight: 44

    Rectangle {
        anchors.fill: parent
        color: hover.hovered ? Theme.hoverBg
             : row.failed ? Theme.warnRowBg : "transparent"

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Theme.rowDivider
        }
    }

    HoverHandler { id: hover }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.padPanel
        anchors.rightMargin: Theme.gapButtons
        spacing: Theme.gapButtons

        Text {
            Layout.fillWidth: true
            // Имя важнее списка дорожек: сначала место ему, остальное ужимается
            Layout.minimumWidth: 180
            text: row.entry.name || ""
            elide: Text.ElideMiddle
            color: row.failed ? Theme.textMuted : Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontStrong
        }

        Text {
            text: row.reading ? I18n.strings["queue.reading"]
                : row.failed ? Fmt.tr("error." + row.entry.code, row.entry.code)
                : Fmt.duration(row.entry.duration) + " · " + Fmt.fileSize(row.entry.size)
            color: row.failed ? Theme.errorFg : Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
        }

        // Выбор дорожки появляется только там, где выбирать есть из чего:
        // у обычной записи одна дорожка, и список над ней — лишний вопрос.
        ComboField {
            Layout.preferredWidth: 160
            popupWidth: 320
            visible: (row.entry.tracks || []).length > 1
            model: (row.entry.tracks || []).map(function (t) { return Fmt.trackText(t) })
            values: (row.entry.tracks || []).map(function (t) { return String(t.index) })
            value: String(row.entry.track)
            onChosen: function (code) { row.trackChosen(parseInt(code)) }
        }

        AppButton {
            text: I18n.strings["queue.remove"]
            flat_: true
            Layout.preferredHeight: Theme.hRowButton
            onClicked: row.removeRequested()
        }
    }
}
