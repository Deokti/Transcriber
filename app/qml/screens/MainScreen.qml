import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import Transcriber
import "../components"

// Главный экран: выбор файлов, три группы настроек, запуск.
// Одна страница, а не мастер: на пятый запуск щёлкать шесть шагов невыносимо.
Item {
    id: screen

    signal openSettings()

    property var files: []
    property bool hasFiles: files.length > 0

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // --- полоса инструментов ---------------------------------------
        // У полос свой фон: так отделены рабочая область и действия.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.hBar
            color: Theme.barBg

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.barDivider
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.gapPanels
                anchors.rightMargin: Theme.gapPanels
                spacing: Theme.gapButtons

            AppButton { text: I18n.strings["action.chooseFiles"] }

            Item { Layout.fillWidth: true }

            AppButton { text: I18n.strings["nav.storage"]; flat_: true }
            AppButton { text: I18n.strings["nav.diagnostics"]; flat_: true }
            AppButton {
                text: I18n.strings["nav.settings"]
                flat_: true
                    onClicked: screen.openSettings()
                }
            }
        }

        // --- рабочая область --------------------------------------------
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.gapPanels
            spacing: Theme.gapPanels

        // --- пусто или очередь -----------------------------------------
        // Одна панель, разделённая вертикальной линией: слева приглашение,
        // справа проверка готовности. Так в макете.
        Panel {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            visible: !screen.hasFiles

            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.padPanel
                spacing: Theme.padPanel

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: Theme.gapButtons

                    Text {
                        text: I18n.strings["main.emptyTitle"]
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSection
                        font.weight: Theme.weightSemiBold
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.maximumWidth: Theme.textWidth
                        wrapMode: Text.WordWrap
                        text: I18n.strings["main.emptyHint"]
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                    }
                    RowLayout {
                        spacing: Theme.gapButtons
                        AppButton { text: I18n.strings["action.chooseFiles"]; primary: true }
                        AppButton { text: I18n.strings["action.chooseFolder"] }
                    }
                }

                Rectangle {
                    Layout.fillHeight: true
                    Layout.preferredWidth: 1
                    color: Theme.panelDivider
                }

                ColumnLayout {
                    Layout.preferredWidth: 230
                    Layout.alignment: Qt.AlignTop
                    spacing: 6

                    Text {
                        text: I18n.strings["main.ready"]
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        font.weight: Theme.weightSemiBold
                    }
                    Repeater {
                        model: ["ffmpeg 7.0", "модель large-v3",
                                "видеокарта NVIDIA RTX 5070 Ti", "свободно 214 ГБ"]
                        RowLayout {
                            spacing: 6
                            CheckMark {
                                width: 11; height: 11
                                thickness: 1.8
                                color: Theme.okFg
                                Layout.alignment: Qt.AlignVCenter
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
                        text: I18n.strings["sound.title"]
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Theme.weightSemiBold
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: I18n.strings["sound.denoise"]
                        model: [I18n.strings["sound.denoise.off"],
                                I18n.strings["sound.denoise.medium"],
                                I18n.strings["sound.denoise.strong"]]
                        currentIndex: 1
                    }
                    CheckField { text: I18n.strings["sound.loudnorm"]; checked: true }
                    CheckField { text: I18n.strings["sound.trimSilence"]; checked: true }
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
                        text: I18n.strings["asr.title"]
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Theme.weightSemiBold
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: I18n.strings["asr.language"]
                        model: ["Русский", "English", "Deutsch"]
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: I18n.strings["asr.model"]
                        model: ["large-v3 · 99 языков, лучшее качество",
                                "large-v3-turbo · быстрее, качество чуть ниже",
                                "medium · быстрее и слабее"]
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: I18n.strings["asr.device"]
                        model: [I18n.strings["asr.device.gpu"] + " NVIDIA RTX 5070 Ti",
                                I18n.strings["asr.device.cpu"]]
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
                        text: I18n.strings["out.title"]
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Theme.weightSemiBold
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: I18n.strings["out.format"]
                        model: ["DOCX", "DOCX и SRT", "TXT", "Markdown"]
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: I18n.strings["out.layout"]
                        model: [I18n.strings["out.layout.timecodes"],
                                I18n.strings["out.layout.plain"]]
                    }
                    ComboField {
                        Layout.fillWidth: true
                        label: I18n.strings["out.where"]
                        model: [I18n.strings["out.where.nextToSource"],
                                I18n.strings["action.chooseFolder"]]
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
                    text: I18n.strings["advanced.title"]
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
        }

        // --- подвал -----------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.hBar
            color: Theme.barBg

            Rectangle {
                width: parent.width
                height: 1
                color: Theme.barDivider
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.gapPanels
                anchors.rightMargin: Theme.gapPanels
                spacing: Theme.gapButtons

            ColumnLayout {
                spacing: 2
                Text {
                    text: screen.hasFiles ? "1 файл · 1 ч 21 мин звука"
                                        : I18n.strings["main.noFiles"]
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                }
                Text {
                    text: screen.hasFiles ? "расчётное время ≈ 19 мин на видеокарте"
                                          : I18n.strings["main.noFilesHint"]
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                }
            }

            Item { Layout.fillWidth: true }

            AppButton { text: I18n.strings["action.savePreset"] }
            AppButton {
                text: screen.hasFiles ? I18n.strings["action.start"]
                                      : I18n.strings["action.startDisabled"]
                    primary: true
                    enabled: screen.hasFiles
                }
            }
        }

        // --- строка состояния -------------------------------------------
        // Молчит, пока всё в порядке: три одинаковых факта мелким шрифтом —
        // это шум. Заговорит, когда чего-то не хватает.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.hStatus
            color: Theme.statusBg

            Text {
                anchors.verticalCenter: parent.verticalCenter
                x: Theme.gapPanels
                text: "ffmpeg 7.0 · модель large-v3 · свободно 214 ГБ"
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }
    }
}
