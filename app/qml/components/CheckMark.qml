import QtQuick

// Галочка из двух палочек.
//
// Раньше она рисовалась вручную на холсте, и это давало тихую ошибку: холст
// пишется один раз, при создании, и цвет в нём застывает. Сменили тему —
// галочка осталась прежней, хотя фон под ней поменялся. Здесь цвет привязан,
// поэтому фигура следует за темой сама.
Item {
    id: root

    property color color: "white"
    property real thickness: 2

    implicitWidth: 12
    implicitHeight: 12

    Rectangle {
        color: root.color
        radius: root.thickness / 2
        width: root.thickness
        height: root.height * 0.45
        x: root.width * 0.26
        y: root.height * 0.42
        rotation: -45
        transformOrigin: Item.Center
        antialiasing: true
    }

    Rectangle {
        color: root.color
        radius: root.thickness / 2
        width: root.thickness
        height: root.height * 0.82
        x: root.width * 0.6
        y: root.height * 0.1
        rotation: 45
        transformOrigin: Item.Center
        antialiasing: true
    }
}
