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
        anchors.margins: Theme.gapPanels
        spacing: Theme.gapPanels

        // --- полоса инструментов ---------------------------------------
        RowLayout {
            Layout.fillWidth: true
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
                        text: I18n.strings["main.emptyTitle"]
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
                        text: I18n.strings["main.emptyHint"]
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                    }
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: Theme.gapButtons
                        AppButton { text: I18n.strings["action.chooseFiles"]; primary: true }
                        AppButton { text: I18n.strings["action.chooseFolder"] }
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
                        text: I18n.strings["main.ready"]
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
                        text: I18n.strings["sound.title"]
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.weight: Theme.weightBold
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
                        font.weight: Theme.weightBold
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
                        font.weight: Theme.weightBold
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

        // --- подвал -----------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
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
}
