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

    // Очередь живёт в мосте: окно её показывает, но не хранит.
    readonly property bool hasFiles: Queue.count > 0
    // Выбранной модели нет на диске: работа начнётся со скачивания, и
    // кнопка обязана сказать об этом заранее — так в макете.
    // Что человек заказал. Распознавания может и не быть — тогда модель,
    // язык и устройство ни при чём, и это должно быть видно: недоступное
    // выключено и объяснено, а не спрятано (правило 3 брифа).
    readonly property bool audioOnly: Task.target === "audio"
    readonly property bool needsDownload: !screen.audioOnly
                                          && Env.downloadedModels.indexOf(Task.model) < 0
    readonly property var chosenModel: Env.models.filter(function (m) {
        return m.id === Task.model
    })[0]


    FolderDialog {
        id: outputPicker
        onAccepted: Task.setOutputDir(selectedFolder)
    }

    FileDialog {
        id: filePicker
        title: I18n.strings["action.chooseFiles"]
        fileMode: FileDialog.OpenFiles
        // Первый фильтр — привычные расширения, второй оставляет лазейку:
        // тип определяется по содержимому (FR-1), и запись с чужим
        // расширением всё равно можно выбрать вручную.
        nameFilters: [
            I18n.strings["dialog.media"] + " ("
                + Queue.extensions.map(function (e) { return "*" + e }).join(" ") + ")",
            I18n.strings["dialog.allFiles"] + " (*)"
        ]
        onAccepted: Queue.add(selectedFiles)
    }

    FolderDialog {
        id: sourcePicker
        title: I18n.strings["action.chooseFolder"]
        onAccepted: Queue.addFolder(selectedFolder)
    }

    // Перетаскивание ловит всё окно, а не отведённый квадрат: человек
    // бросает файл туда, куда смотрит.
    DropArea {
        id: dropZone
        anchors.fill: parent
        onEntered: function (drag) { drag.accepted = drag.hasUrls }
        onDropped: function (drop) { if (drop.hasUrls) Queue.add(drop.urls) }
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

                AppButton {
                    text: I18n.strings["action.chooseFiles"]
                    onClicked: filePicker.open()
                }

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
                // С очередью панель занимает всё свободное место: список
                // растёт вниз, проверка готовности остаётся справа.
                Layout.fillHeight: screen.hasFiles

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.padPanel
                    spacing: Theme.padPanel

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        visible: !screen.hasFiles
                        spacing: Theme.gapButtons

                        SectionTitle {
                            text: I18n.strings["main.emptyTitle"]
                            font.pixelSize: Theme.fontSection
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
                            AppButton {
                                text: I18n.strings["action.chooseFiles"]
                                primary: true
                                onClicked: filePicker.open()
                            }
                            AppButton {
                                text: I18n.strings["action.chooseFolder"]
                                onClicked: sourcePicker.open()
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        visible: screen.hasFiles
                        spacing: Theme.gapButtons

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.gapButtons

                            SectionTitle { text: I18n.strings["queue.title"] }
                            Text {
                                text: Fmt.duration(Queue.totalDuration) + " · "
                                      + Fmt.fileSize(Queue.totalSize)
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                            }
                            Item { Layout.fillWidth: true }
                            AppButton {
                                text: I18n.strings["action.addQueue"]
                                flat_: true
                                Layout.preferredHeight: Theme.hRowButton
                                onClicked: filePicker.open()
                            }
                            AppButton {
                                text: I18n.strings["queue.clear"]
                                flat_: true
                                Layout.preferredHeight: Theme.hRowButton
                                onClicked: Queue.clear()
                            }
                        }

                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: Queue.files
                            boundsBehavior: Flickable.StopAtBounds
                            delegate: FileRow {
                                width: ListView.view.width
                                entry: modelData
                                position: index
                                onRemoveRequested: Queue.remove(index)
                                onTrackChosen: function (track) { Queue.setTrack(index, track) }
                            }
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

                        SectionTitle {
                            text: I18n.strings["main.ready"]
                            font.pixelSize: Theme.fontSmall
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
                                    // Список, а не вопрос: привязка следит за
                                    // свойствами, а вызов пересчитан не будет.
                                    ok: screen.audioOnly
                                        || Env.downloadedModels.indexOf(Task.model) >= 0,
                                    text: screen.audioOnly
                                        ? I18n.strings["ready.modelNotNeeded"]
                                        : Env.downloadedModels.indexOf(Task.model) >= 0
                                        ? I18n.strings["ready.model"].arg(Task.model)
                                        : I18n.strings["ready.modelMissing"].arg(Task.model)
                                },
                                {
                                    ok: screen.audioOnly
                                        || (Env.gpuAvailable && Task.device === "cuda"),
                                    text: screen.audioOnly ? I18n.strings["ready.audioOnly"]
                                        : Env.gpuAvailable && Task.device === "cuda"
                                        ? Env.gpuName
                                        : I18n.strings["ready.cpu"]
                                },
                                {
                                    ok: Env.freeBytes > 5 * 1024 * 1024 * 1024,
                                    text: I18n.strings["ready.free"].arg(
                                        Fmt.gigabytes(Env.freeBytes))
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
                id: settings
                Layout.fillWidth: true
                spacing: Theme.gapPanels

                // Высота у всех трёх одна, по самой высокой. Иначе короткая
                // колонка обрывается на полпути, и белый фон панели кончается
                // там, где соседям ещё есть что показать.
                readonly property int rowHeight:
                    Math.max(soundColumn.implicitHeight,
                             asrColumn.implicitHeight,
                             outColumn.implicitHeight) + Theme.padPanel * 2

                Panel {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: settings.rowHeight

                    ColumnLayout {
                        id: soundColumn
                        anchors.fill: parent
                        anchors.margins: Theme.padPanel
                        spacing: 10

                        SectionTitle { text: I18n.strings["sound.title"] }
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
                    Layout.preferredHeight: settings.rowHeight

                    ColumnLayout {
                        id: asrColumn
                        anchors.fill: parent
                        anchors.margins: Theme.padPanel
                        spacing: 10

                        SectionTitle {
                            text: I18n.strings["asr.title"]
                            color: screen.audioOnly ? Theme.textDisabled : Theme.text
                        }
                        ComboField {
                            Layout.fillWidth: true
                            enabled_: !screen.audioOnly
                            hint: screen.audioOnly ? I18n.strings["asr.notNeeded"] : ""
                            label: I18n.strings["asr.language"]
                            model: Env.languages.map(function (c) { return Fmt.languageName(c) })
                            values: Env.languages
                            value: Task.language
                            onChosen: function (code) { Task.setLanguage(code) }
                        }
                        ComboField {
                            Layout.fillWidth: true
                            enabled_: !screen.audioOnly
                            label: I18n.strings["asr.model"]
                            // Модель, не знающая выбранного языка, остаётся
                            // в списке, но выбрать её нельзя (требование FR-35)
                            model: Env.models.map(function (m) {
                                return {
                                    text: Fmt.modelText(m),
                                    disabled: m.languages === "en" && Task.language !== "en"
                                }
                            })
                            values: Env.models.map(function (m) { return m.id })
                            value: Task.model
                            onChosen: function (id) { Task.setModel(id) }
                        }
                        ComboField {
                            Layout.fillWidth: true
                            enabled_: !screen.audioOnly
                            label: I18n.strings["asr.device"]
                            model: Env.devices.map(function (d) {
                                return { text: Fmt.deviceText(d), disabled: !d.available }
                            })
                            values: Env.devices.map(function (d) { return d.id })
                            value: Task.device
                            hint: screen.audioOnly || Env.gpuAvailable ? ""
                                : Fmt.tr("device.reason." + Env.gpuReason, "")
                            onChosen: function (id) { Task.setDevice(id) }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                Panel {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: settings.rowHeight

                    ColumnLayout {
                        id: outColumn
                        anchors.fill: parent
                        anchors.margins: Theme.padPanel
                        spacing: 10

                        SectionTitle { text: I18n.strings["out.title"] }

                        // Первое поле группы — сам заказ (решение D-13):
                        // это вопрос «что я получу», а не деталь оформления.
                        ComboField {
                            Layout.fillWidth: true
                            label: I18n.strings["out.target"]
                            model: ["text", "both", "audio"].map(function (t) {
                                return I18n.strings["out.target." + t]
                            })
                            values: ["text", "both", "audio"]
                            value: Task.target
                            onChosen: function (code) { Task.setTarget(code) }
                        }

                        ComboField {
                            Layout.fillWidth: true
                            visible: Task.needsText
                            label: I18n.strings["out.format"]
                            // Показываем только то, что ядро умеет собрать
                            model: Env.formats.map(function (f) {
                                return Fmt.tr("format." + f, f.toUpperCase())
                            })
                            values: Env.formats
                            value: Task.format
                            onChosen: function (f) { Task.setFormat(f) }
                        }
                        ComboField {
                            Layout.fillWidth: true
                            visible: Task.needsText
                            label: I18n.strings["out.layout"]
                            model: [I18n.strings["out.layout.timecodes"],
                                    I18n.strings["out.layout.plain"]]
                            values: ["timecodes", "plain"]
                            value: Task.layout
                            onChosen: function (code) { Task.setLayout(code) }
                        }

                        // Формат звука появляется только тогда, когда звук
                        // и правда заказан (FR-8).
                        ComboField {
                            Layout.fillWidth: true
                            visible: Task.needsAudio
                            label: I18n.strings["out.audioFormat"]
                            model: Env.audioFormats.map(function (f) {
                                return Fmt.tr("audio." + f, f)
                            })
                            values: Env.audioFormats
                            value: Task.audioFormat
                            onChosen: function (f) { Task.setAudioFormat(f) }
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

                        Item { Layout.fillHeight: true }
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
                        // В режиме звука параметры распознавания не применяются,
                        // а промежуточных файлов не остаётся — значит и сводке
                        // рассказывать о них нечего.
                        text: screen.audioOnly
                            ? [I18n.strings["advanced.asrOnly"],
                               I18n.strings["advanced.noTemp"]].join(" · ")
                            : [
                                I18n.strings["advanced.chunk"].arg(Task.chunkLength),
                                I18n.strings["advanced.sensitivity"].arg(
                                    Fmt.tr("sensitivity." + Task.sensitivity, Task.sensitivity)),
                                Fmt.tr("temp." + Task.tempAction, Task.tempAction)
                            ].join(" · ")
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        elide: Text.ElideRight
                    }
                }
            }

            Item {
                Layout.fillHeight: true
                visible: !screen.hasFiles
            }
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
                        text: screen.hasFiles
                            ? I18n.strings["queue.summary"].arg(Queue.count)
                            : I18n.strings["main.noFiles"]
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                    }
                    Text {
                        text: Run.failure.code !== undefined
                            ? Fmt.noticeText(Run.failure)
                            : screen.needsDownload && screen.hasFiles
                            ? I18n.strings["main.modelWillDownload"]
                                  .arg(Task.model)
                                  .arg(Fmt.fileSize((screen.chosenModel
                                       ? screen.chosenModel.size_mb : 0) * 1024 * 1024))
                            : screen.hasFiles
                            ? Fmt.duration(Queue.totalDuration) + " · "
                              + Fmt.fileSize(Queue.totalSize)
                            : I18n.strings["main.noFilesHint"]
                        color: Run.failure.code !== undefined ? Theme.errorFg
                             : screen.needsDownload && screen.hasFiles ? Theme.warnFg
                             : Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                    }
                }

                Item { Layout.fillWidth: true }

                AppButton { text: I18n.strings["action.savePreset"] }
                AppButton {
                    text: !screen.hasFiles ? I18n.strings["action.startDisabled"]
                        : screen.needsDownload ? I18n.strings["action.downloadAndStart"]
                        : I18n.strings["action.start"]
                    primary: true
                    // Пока файлы разбираются, длительности неизвестны —
                    // запускать рано.
                    enabled: Queue.readyCount > 0 && !Queue.reading
                    onClicked: Run.start()
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
                // В режиме звука модель не при чём — показываем формат файла
                text: [
                    Env.ffmpegOk ? I18n.strings["ready.ffmpeg"].arg(Env.ffmpegVersion)
                                 : I18n.strings["ready.ffmpegMissing"],
                    screen.audioOnly ? Fmt.tr("audio." + Task.audioFormat, Task.audioFormat)
                                     : Task.model,
                    I18n.strings["ready.free"].arg(Fmt.gigabytes(Env.freeBytes))
                ].join(" · ")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }
    }
}
