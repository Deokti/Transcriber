import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import Transcriber
import "../components"

// Главный экран: выбор файлов, три группы настроек, запуск.
// Одна страница, а не мастер: на пятый запуск щёлкать шесть шагов невыносимо.
Item {
    id: screen

    property var files: []
    property bool hasFiles: files.length > 0

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.gapPanels
        spacing: Theme.gapPanels

        // --- полоса инструментов ---------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.gapButtons

            AppButton { text: "Выбрать файлы…" }

            Item { Layout.fillWidth: true }

            AppButton { text: "Хранилище"; flat_: true }
            AppButton { text: "Диагностика"; flat_: true }
            AppButton { text: "Настройки"; flat_: true }
        }

        // --- пусто или очередь -----------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.gapPanels
            visible: !screen.hasFiles

            Panel {
                Layout.fillWidth: true
                Layout.preferredHeight: 150

                ColumnLayout {
                    anchors.centerIn: parent
                    width: parent.width - Theme.padPanel * 2
                    spacing: Theme.gapButtons

                    Text {
                        text: "Выберите запись — или перетащите её в окно"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSection
                        font.weight: Theme.weightBold
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.maximumWidth: Theme.textWidth
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        text: "MP4, MKV, MOV, MP3, WAV, M4A и другие. Час записи " +
                              "превращается в документ примерно за 19 минут на видеокарте. " +
                              "Всё считается на этом компьютере, ничего не уходит в сеть."
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                    }
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: Theme.gapButtons
                        AppButton { text: "Выбрать файлы…"; primary: true }
                        AppButton { text: "Выбрать папку…" }
                    }
                }
            }

            // Блок «Готово к работе» — он же предупредит, если что-то не так
            Panel {
                Layout.preferredWidth: 260
                Layout.preferredHeight: 150

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.padPanel
                    spacing: 6

                    Text {
                        text: "Готово к работе"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Theme.weightBold
                    }
                    Repeater {
                        model: ["ffmpeg 7.0", "модель large-v3",
                                "видеокарта NVIDIA RTX 5070 Ti", "свободно 214 ГБ"]
                        RowLayout {
                            spacing: 6
                            Canvas {
                                width: 11; height: 9
                                Layout.alignment: Qt.AlignVCenter
                                onPaint: {
                                    const ctx = getContext("2d");
                                    ctx.reset();
                                    ctx.strokeStyle = Theme.ok;
                                    ctx.lineWidth = 1.8;
                                    ctx.lineCap = "round";
                                    ctx.beginPath();
                                    ctx.moveTo(0.5, 4.5);
                                    ctx.lineTo(4, 8);
                                    ctx.lineTo(10.5, 0.8);
                                    ctx.stroke();
                                }
                            }
                            Text {
                                text: modelData
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }

        // --- три группы настроек на одной линии -------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.gapPanels

            Panel {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                Layout.preferredHeight: soundColumn.implicitHeight + Theme.padPanel * 2

                ColumnLayout {
                    id: soundColumn
                    anchors.fill: parent
                    anchors.margins: Theme.padPanel
                    spacing: 10

                    Text {
                        text: "Звук"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Theme.weightBold
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: "Шумоподавление"
                        model: ["Выключено", "Умеренное", "Сильное"]
                        currentIndex: 1
                    }
                    CheckField { text: "Выровнять громкость"; checked: true }
                    CheckField { text: "Обрезать тишину по краям"; checked: true }
                    Item { Layout.fillHeight: true }
                }
            }

            Panel {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                Layout.preferredHeight: asrColumn.implicitHeight + Theme.padPanel * 2

                ColumnLayout {
                    id: asrColumn
                    anchors.fill: parent
                    anchors.margins: Theme.padPanel
                    spacing: 10

                    Text {
                        text: "Распознавание"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Theme.weightBold
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: "Язык записи"
                        model: ["Русский", "English", "Deutsch"]
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: "Модель"
                        model: ["large-v3 · 99 языков, лучшее качество",
                                "large-v3-turbo · быстрее, качество чуть ниже",
                                "medium · быстрее и слабее"]
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: "Считать на"
                        model: ["Видеокарте NVIDIA RTX 5070 Ti", "Процессоре"]
                    }
                }
            }

            Panel {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.alignment: Qt.AlignTop
                Layout.preferredHeight: outColumn.implicitHeight + Theme.padPanel * 2

                ColumnLayout {
                    id: outColumn
                    anchors.fill: parent
                    anchors.margins: Theme.padPanel
                    spacing: 10

                    Text {
                        text: "Результат"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Theme.weightBold
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: "Формат документа"
                        model: ["DOCX", "DOCX и SRT", "TXT", "Markdown"]
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: "Оформление"
                        model: ["Абзацы с тайм-кодами", "Сплошной текст"]
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: "Куда положить"
                        model: ["Рядом с исходным", "Выбрать папку…"]
                    }
                }
            }
        }

        // --- дополнительно ---------------------------------------------
        Panel {
            Layout.fillWidth: true
            Layout.preferredHeight: 38

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.padPanel
                anchors.rightMargin: Theme.padPanel
                spacing: 10

                Text {
                    text: "›"
                    color: Theme.textMuted
                    font.pixelSize: Theme.fontSection
                }
                Text {
                    text: "Дополнительно"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                }
                Text {
                    Layout.fillWidth: true
                    text: "фрагмент 30 секунд · чувствительность к речи средняя · " +
                          "потоки не нужны — видеокарта · WAV удалить"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    elide: Text.ElideRight
                }
            }
        }

        Item { Layout.fillHeight: true }

        // --- подвал -----------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.gapButtons

            ColumnLayout {
                spacing: 2
                Text {
                    text: screen.hasFiles ? "1 файл · 1 ч 21 мин звука" : "Файлы не выбраны"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                }
                Text {
                    text: screen.hasFiles ? "расчётное время ≈ 19 мин на видеокарте"
                                          : "настройки уже проставлены — достаточно выбрать файл"
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                }
            }

            Item { Layout.fillWidth: true }

            AppButton { text: "Сохранить пресет" }
            AppButton {
                text: screen.hasFiles ? "Запустить" : "Сначала выберите файл"
                primary: true
                enabled: screen.hasFiles
            }
        }
    }
}
