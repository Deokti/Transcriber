import QtQuick
import Transcriber

// Панель отделяется рамкой и фоном, без теней: так решено в брифе.
Rectangle {
    color: Theme.panel
    border.color: Theme.line
    border.width: 1
    radius: Theme.radiusPanel
}
