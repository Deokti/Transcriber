import QtQuick
import QtQuick.Shapes
import Transcriber
import "."

// Знак итога проверки: галочка, треугольник, «i» в круге, крестик.
//
// Рисуем сами, а не символами шрифта: «⚠» на Windows подменяется цветной
// эмодзи и перестаёт следовать за темой. Знак и цвет идут вместе — по
// одному цвету состояние не читается (правило из брифа).
Item {
    id: icon

    property string level: "ok"        // ok · note · warn · fail

    readonly property color tone: level === "ok" ? Theme.okFg
                                : level === "fail" ? Theme.errorFg
                                : Theme.warnFg
    readonly property bool warn: level === "warn"
    readonly property bool note: level === "note"
    readonly property bool fail: level === "fail"

    implicitWidth: 16
    implicitHeight: 16

    CheckMark {
        anchors.centerIn: parent
        visible: icon.level === "ok"
        width: 13
        height: 13
        color: icon.tone
    }

    // предупреждение: треугольник с восклицательным знаком
    Shape {
        anchors.fill: parent
        visible: icon.warn
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: icon.tone
            strokeWidth: 1.5
            fillColor: "transparent"
            joinStyle: ShapePath.RoundJoin
            startX: 8; startY: 1.5
            PathLine { x: 15.2; y: 14.5 }
            PathLine { x: 0.8; y: 14.5 }
            PathLine { x: 8; y: 1.5 }
        }
    }
    Rectangle {
        visible: icon.warn
        x: 7.25; y: 5.6
        width: 1.5; height: 4.8; radius: 0.75
        color: icon.tone
    }
    Rectangle {
        visible: icon.warn
        x: 7.25; y: 11.6
        width: 1.5; height: 1.6; radius: 0.75
        color: icon.tone
    }

    // замечание и неудача: круг, внутри «i» или крестик
    Rectangle {
        visible: icon.note || icon.fail
        anchors.fill: parent
        anchors.margins: 1
        radius: width / 2
        color: "transparent"
        border.color: icon.tone
        border.width: 1.5
        antialiasing: true
    }
    Rectangle {
        visible: icon.note
        x: 7.25; y: 6.8
        width: 1.5; height: 5; radius: 0.75
        color: icon.tone
    }
    Rectangle {
        visible: icon.note
        x: 7.25; y: 4.1
        width: 1.5; height: 1.6; radius: 0.75
        color: icon.tone
    }
    Repeater {
        model: [45, -45]
        Rectangle {
            required property int modelData
            visible: icon.fail
            anchors.centerIn: parent
            width: 1.5; height: 7.5; radius: 0.75
            rotation: modelData
            antialiasing: true
            color: icon.tone
        }
    }
}
