import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import Transcriber
import "../components"

// Главный экран: выбор файлов, три группы настроек, запуск.
// Одна страница, а не мастер: на пятый запуск щёлкать шесть шагов невыносимо.
//
// Значения приходят из мостов: Env знает машину, Task — что сделать с
// записью. Заглушек здесь больше нет.
Item {
    id: screen

    signal openSettings()

    property var files: []
    property bool hasFiles: files.length > 0

    // --- вспомогательное -------------------------------------------------
    function tr(key, fallback) {
        const value = I18n.strings[key]
        return value !== undefined ? value : fallback
    }

    function languageName(code) {
        return tr("lang." + code, code)
    }

    function modelText(entry) {
        const langs = entry.languages === "en" ? I18n.strings["model.enOnly"]
                                               : I18n.strings["model.multi"]
        const size = (entry.size_mb / 1024).toFixed(1) + " " + I18n.strings["unit.gb"]
        const state = entry.downloaded ? "" : " · " + I18n.strings["model.notDownloaded"]
        return entry.id + " · " + langs + " · " + size + state
    }

    function deviceText(entry) {
        if (entry.id !== "cuda")
            return I18n.strings["asr.device.cpu"]
        return Env.gpuName !== "" ? Env.gpuName : I18n.strings["asr.device.gpu"]
    }

    function gigabytes(bytes) {
        return (bytes / 1024 / 1024 / 1024).toFixed(0) + " " + I18n.strings["unit.gb"]
    }

    FolderDialog {
        id: outputPicker
        onAccepted: Task.setOutputDir(selectedFolder)
    }

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
                            color: Theme.textBody
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
                        Layout.preferredWidth: 250
                        Layout.alignment: Qt.AlignTop
                        spacing: 6

                        Text {
                            text: I18n.strings["main.ready"]
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            font.weight: Theme.weightSemiBold
                        }

                        // Настоящее состояние машины, а не четыре галочки
                        // «всё хорошо»: чего-то нет — здесь это и видно.
                        Repeater {
                            model: [
                                {
                                    ok: Env.ffmpegOk,
                                    text: Env.ffmpegOk
                                        ? I18n.strings["ready.ffmpeg"].arg(Env.ffmpegVersion)
                                        : I18n.strings["ready.ffmpegMissing"]
                                },
                                {
                                    ok: Env.modelDownloaded(Task.model),
                                    text: Env.modelDownloaded(Task.model)
                                        ? I18n.strings["ready.model"].arg(Task.model)
                                        : I18n.strings["ready.modelMissing"].arg(Task.model)
                                },
                                {
                                    ok: Env.gpuAvailable && Task.device === "cuda",
                                    text: Env.gpuAvailable && Task.device === "cuda"
                                        ? Env.gpuName
                                        : I18n.strings["ready.cpu"]
                                },
                                {
                                    ok: Env.freeBytes > 5 * 1024 * 1024 * 1024,
                                    text: I18n.strings["ready.free"].arg(
                                        screen.gigabytes(Env.freeBytes))
                                }
                            ]

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                CheckMark {
                                    width: 11; height: 11
                                    thickness: 1.8
                                    visible: modelData.ok
                                    color: Theme.okFg
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                Rectangle {
                                    width: 9; height: 9; radius: 4.5
                                    visible: !modelData.ok
                                    color: "transparent"
                                    border.color: Theme.warnFg
                                    border.width: 1.6
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.text
                                    color: modelData.ok ? Theme.textMuted : Theme.warnFg
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                    elide: Text.ElideRight
                                }
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            // --- три группы настроек на одной линии ----------------------
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
                            values: ["off", "medium", "strong"]
                            value: Task.denoise
                            onChosen: function (code) { Task.setDenoise(code) }
                        }
                        CheckField {
                            text: I18n.strings["sound.loudnorm"]
                            checked: Task.loudnorm
                            onToggled: Task.setLoudnorm(checked)
                        }
                        CheckField {
                            text: I18n.strings["sound.trimSilence"]
                            checked: Task.trimSilence
                            onToggled: Task.setTrimSilence(checked)
                        }
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
                            model: Env.languages.map(screen.languageName)
                            values: Env.languages
                            value: Task.language
                            onChosen: function (code) { Task.setLanguage(code) }
                        }
                        ComboField {
                            Layout.fillWidth: true
                            label: I18n.strings["asr.model"]
                            // Модель, не знающая выбранного языка, остаётся
                            // в списке, но выбрать её нельзя (требование FR-35)
                            model: Env.models.map(function (m) {
                                return {
                                    text: screen.modelText(m),
                                    disabled: m.languages === "en" && Task.language !== "en"
                                }
                            })
                            values: Env.models.map(function (m) { return m.id })
                            value: Task.model
                            onChosen: function (id) { Task.setModel(id) }
                        }
                        ComboField {
                            Layout.fillWidth: true
                            label: I18n.strings["asr.device"]
                            model: Env.devices.map(function (d) {
                                return { text: screen.deviceText(d), disabled: !d.available }
                            })
                            values: Env.devices.map(function (d) { return d.id })
                            value: Task.device
                            hint: Env.gpuAvailable ? ""
                                : screen.tr("device.reason." + Env.gpuReason, "")
                            onChosen: function (id) { Task.setDevice(id) }
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
                            // Показываем только то, что ядро умеет собрать
                            model: Env.formats.map(function (f) {
                                return screen.tr("format." + f, f.toUpperCase())
                            })
                            values: Env.formats
                            value: Task.format
                            onChosen: function (f) { Task.setFormat(f) }
                        }
                        ComboField {
                            Layout.fillWidth: true
                            label: I18n.strings["out.layout"]
                            model: [I18n.strings["out.layout.timecodes"],
                                    I18n.strings["out.layout.plain"]]
                            values: ["timecodes", "plain"]
                            value: Task.layout
                            onChosen: function (code) { Task.setLayout(code) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.gapButtons

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: Theme.gapLabel
                                Text {
                                    text: I18n.strings["out.where"]
                                    color: Theme.textMuted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: Theme.hField
                                    radius: Theme.radiusField
                                    color: Theme.fieldBg
                                    border.width: 1
                                    border.color: Theme.fieldBorder
                                    Text {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        verticalAlignment: Text.AlignVCenter
                                        text: Task.outputDir !== "" ? Task.outputDir
                                            : I18n.strings["out.where.nextToSource"]
                                        color: Task.outputDir !== "" ? Theme.text : Theme.textMuted
                                        font.family: Task.outputDir !== "" ? Theme.monoFamily
                                                                           : Theme.fontFamily
                                        font.pixelSize: Theme.fontSmall
                                        elide: Text.ElideMiddle
                                    }
                                }
                            }
                            AppButton {
                                text: I18n.strings["action.choose"]
                                Layout.alignment: Qt.AlignBottom
                                onClicked: outputPicker.open()
                            }
                        }
                    }
                }
            }

            // --- дополнительно -------------------------------------------
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
                        text: [
                            I18n.strings["advanced.chunk"].arg(Task.chunkLength),
                            I18n.strings["advanced.sensitivity"].arg(
                                screen.tr("sensitivity." + Task.sensitivity, Task.sensitivity)),
                            screen.tr("temp." + Task.tempAction, Task.tempAction)
                        ].join(" · ")
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
                        text: screen.hasFiles ? "" : I18n.strings["main.noFiles"]
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                    }
                    Text {
                        text: screen.hasFiles ? "" : I18n.strings["main.noFilesHint"]
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
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.hStatus
            color: Theme.statusBg

            Text {
                anchors.verticalCenter: parent.verticalCenter
                x: Theme.gapPanels
                width: parent.width - Theme.gapPanels * 2
                elide: Text.ElideRight
                text: [
                    Env.ffmpegOk ? I18n.strings["ready.ffmpeg"].arg(Env.ffmpegVersion)
                                 : I18n.strings["ready.ffmpegMissing"],
                    Task.model,
                    I18n.strings["ready.free"].arg(screen.gigabytes(Env.freeBytes))
                ].join(" · ")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }
    }
}
