import QtQuick
import Transcriber

// Полоса хода работы. Человек смотрит на неё с другого конца комнаты,
// поэтому она крупная и без украшений.
//
// Когда доля неизвестна (уборка, сборка документа — секунды), полоса не
// притворяется: вместо заливки по проценту она показывает бегунок.
Rectangle {
    id: bar

    property real value: 0        // 0…1
    property bool known: true

    implicitHeight: Theme.hProgress
    radius: height / 2
    color: Theme.trackBg
    border.width: 1
    border.color: Theme.trackBorder

    Rectangle {
        visible: bar.known
        width: Math.max(0, Math.min(1, bar.value)) * (parent.width - 2)
        height: parent.height - 2
        x: 1
        y: 1
        radius: height / 2
        color: Theme.accent

        Behavior on width { NumberAnimation { duration: Theme.normal } }
    }

    Item {
        visible: !bar.known
        anchors.fill: parent
        anchors.margins: 1
        clip: true

        Rectangle {
            id: runner
            width: parent.width / 4
            height: parent.height
            radius: height / 2
            color: Theme.accent
            opacity: 0.7

            SequentialAnimation on x {
                running: !bar.known && bar.visible
                loops: Animation.Infinite
                NumberAnimation { from: -runner.width; to: runner.parent.width
                                  duration: 1400; easing.type: Easing.InOutQuad }
            }
        }
    }
}
