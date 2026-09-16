import QtQuick
import Transcriber

// Заголовок группы: «Звук», «Распознавание», «Результат».
// Размер перебивается на месте — на экране настроек заголовок крупнее,
// в блоке готовности мельче, — а начертание и цвет везде одни.
Text {
    color: Theme.text
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBase
    font.weight: Theme.weightSemiBold
}
