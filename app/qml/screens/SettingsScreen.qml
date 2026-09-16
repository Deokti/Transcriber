import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import Transcriber
import "../components"

// Настройки: язык, тема, папки. Меняется сразу, сохраняется кнопкой —
// человек должен видеть, что выбрал, ещё до того, как согласится.
Item {
    id: screen

    signal back()

    property string pickerTarget: ""

    FolderDialog {
        id: picker
        title: I18n.strings["action.choose"]
        onAccepted: {
            if (screen.pickerTarget === "models") Settings.setModelsDir(selectedFolder)
            else if (screen.pickerTarget === "output") Settings.setOutputDir(selectedFolder)
            else if (screen.pickerTarget === "ffmpeg") Settings.setFfmpegDir(selectedFolder)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.padScreen
        spacing: Theme.gapPanels

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.gapButtons

            AppButton {
                text: "‹  " + I18n.strings["action.back"]
                flat_: true
                onClicked: screen.back()
            }
            Text {
                text: I18n.strings["settings.title"]
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSection
                font.weight: Theme.weightBold
            }
            Item { Layout.fillWidth: true }
            // Молчим, пока всё сохранено: сообщать стоит о том, что требует
            // внимания, а не о том, что и так в порядке.
            Text {
                visible: !Settings.saved
                text: I18n.strings["settings.unsaved"]
                color: Theme.warn
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }

        // --- интерфейс ---------------------------------------------------
        Panel {
            Layout.fillWidth: true
            Layout.preferredHeight: interfaceColumn.implicitHeight + Theme.padPanel * 2

            ColumnLayout {
                id: interfaceColumn
                anchors.fill: parent
                anchors.margins: Theme.padPanel
                spacing: 12

                Text {
                    text: I18n.strings["settings.interface"]
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Theme.weightBold
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.gapPanels

                    ComboField {
                        Layout.preferredWidth: 240
                        label: I18n.strings["settings.language"]
                        model: I18n.languages.map(function (l) { return l.name })
                        currentIndex: {
                            const codes = I18n.languages.map(function (l) { return l.code })
                            return Math.max(0, codes.indexOf(Settings.language))
                        }
                        onCurrentIndexChanged: {
                            const codes = I18n.languages.map(function (l) { return l.code })
                            if (currentIndex >= 0 && codes[currentIndex] !== Settings.language)
                                Settings.setLanguage(codes[currentIndex])
                        }
                    }

                    ComboField {
                        Layout.preferredWidth: 240
                        label: I18n.strings["settings.theme"]
                        property var codes: ["system", "light", "dark"]
                        model: [I18n.strings["settings.theme.system"],
                                I18n.strings["settings.theme.light"],
                                I18n.strings["settings.theme.dark"]]
                        currentIndex: Math.max(0, codes.indexOf(Settings.theme))
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && codes[currentIndex] !== Settings.theme)
                                Settings.setTheme(codes[currentIndex])
                        }
                    }

                    Item { Layout.fillWidth: true }
                }
            }
        }

        // --- папки --------------------------------------------------------
        Panel {
            Layout.fillWidth: true
            Layout.preferredHeight: foldersColumn.implicitHeight + Theme.padPanel * 2

            ColumnLayout {
                id: foldersColumn
                anchors.fill: parent
                anchors.margins: Theme.padPanel
                spacing: 14

                Text {
                    text: I18n.strings["settings.folders"]
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Theme.weightBold
                }

                FolderRow {
                    Layout.fillWidth: true
                    label: I18n.strings["settings.models"]
                    hint: I18n.strings["settings.modelsHint"]
                    value: Settings.modelsDir
                    placeholder: Settings.defaultModelsDir
                    onChoose: { screen.pickerTarget = "models"; picker.open() }
                    onReset: Settings.setModelsDir("")
                }

                FolderRow {
                    Layout.fillWidth: true
                    label: I18n.strings["settings.output"]
                    hint: I18n.strings["settings.outputHint"]
                    value: Settings.outputDir
                    placeholder: I18n.strings["out.where.nextToSource"]
                    onChoose: { screen.pickerTarget = "output"; picker.open() }
                    onReset: Settings.setOutputDir("")
                }

                FolderRow {
                    Layout.fillWidth: true
                    label: I18n.strings["settings.ffmpeg"]
                    hint: I18n.strings["settings.ffmpegHint"]
                    value: Settings.ffmpegDir
                    placeholder: I18n.strings["settings.default"]
                    onChoose: { screen.pickerTarget = "ffmpeg"; picker.open() }
                    onReset: Settings.setFfmpegDir("")
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        text: I18n.strings["settings.dataDir"] + ":"
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                    }
                    Text {
                        Layout.fillWidth: true
                        text: Settings.dataDir
                        color: Theme.textMuted
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.fontSmall
                        elide: Text.ElideMiddle
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            AppButton {
                text: I18n.strings["action.save"]
                primary: true
                enabled: !Settings.saved
                onClicked: Settings.save()
            }
        }
    }
}
