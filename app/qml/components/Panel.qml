import QtQuick
import Transcriber

// Панель отделяется рамкой и фоном, без теней: так решено в брифе.
Rectangle {
    color: Theme.panelBg
    border.color: Theme.panelBorder
    border.width: 1
    radius: Theme.radiusPanel
}
