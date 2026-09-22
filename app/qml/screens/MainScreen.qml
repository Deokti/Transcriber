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

    // Числовые настройки — списком, а не полем ввода: у длины фрагмента и
    // числа потоков есть разумные значения, а опечатка вроде 300 секунд
    // молча испортила бы работу на полтора часа.
    readonly property var sensitivityValues: ["low", "medium", "high"]
    readonly property var tempValues: ["delete", "keep", "move"]
    readonly property var chunkValues: [15, 30, 45, 60]
    readonly property var threadValues: [0, 2, 4, 8, 16]
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

                // Экраны «Хранилище» и «Диагностика» ещё не написаны — кнопки
                // вернутся вместе с ними (M4). Кнопка, ведущая в никуда,
                // хуже её отсутствия.
                // AppButton { text: I18n.strings["nav.storage"]; flat_: true }
                // AppButton { text: I18n.strings["nav.diagnostics"]; flat_: true }
                AppButton {
                    text: I18n.strings["nav.settings"]
                    flat_: true
                    onClicked: screen.openSettings()
                }
            }
        }

        // --- рабочая область --------------------------------------------
        // Прокрутка на случай низкого окна. При минимальной высоте (620 px)
        // содержимое не помещалось: подвал с кнопкой «Запустить» уезжал за
        // край экрана, и заметил бы это первым тот, у кого короткая матрица.
        Flickable {
            id: workArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: work.height + Theme.gapPanels * 2
            boundsBehavior: Flickable.StopAtBounds
            clip: true

            // Раскрытая панель лежит в самом низу колонки: показать её —
            // значит домотать до конца. Иначе человек жмёт на заголовок,
            // а поля открываются под краем окна, и кажется, что ничего
            // не произошло.
            function showBottom() {
                const overflow = contentHeight - height
                if (overflow > 0)
                    contentY = overflow
            }

            ColumnLayout {
                id: work
                x: Theme.gapPanels
                y: Theme.gapPanels
                width: workArea.width - Theme.gapPanels * 2
                // Пока содержимое помещается, колонка ровно с окно: панель
                // очереди растягивается на свободное место, как и раньше.
                // Перестало помещаться — колонка выше окна, и появляется
                // прокрутка, а не обрезанный подвал.
                height: Math.max(implicitHeight, workArea.height - Theme.gapPanels * 2)
                spacing: Theme.gapPanels

                // Одна панель, разделённая вертикальной линией: слева приглашение,
                // справа проверка готовности. Так в макете.
                Panel {
                    Layout.fillWidth: true
                    // Пустой экран ровно на 150, но кнопка «Скачать ffmpeg»
                    // и строка источника под ней не должны обрезаться.
                    Layout.preferredHeight: Math.max(150, readyColumn.implicitHeight
                                                          + Theme.padPanel * 2)
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
                            id: readyColumn
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
                            // ffmpeg не нашёлся — предлагаем принести его сами.
                            // Без него не будет ни звука, ни распознавания.
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.topMargin: Theme.gapLabel
                                visible: !Env.ffmpegOk
                                spacing: Theme.gapButtons

                                AppButton {
                                    text: Deps.busy
                                        ? I18n.strings["deps.downloading"]
                                              .arg(Math.round(Deps.percent * 100) + "%")
                                        : I18n.strings["deps.getFfmpeg"]
                                              .arg(Fmt.fileSize((Deps.ffmpegBuild.sizeMb || 0)
                                                                * 1024 * 1024))
                                    enabled: !Deps.busy
                                    Layout.preferredHeight: Theme.hRowButton
                                    onClicked: Deps.getFfmpeg()
                                }
                                AppButton {
                                    visible: Deps.busy
                                    flat_: true
                                    text: I18n.strings["deps.cancel"]
                                    Layout.preferredHeight: Theme.hRowButton
                                    onClicked: Deps.cancel()
                                }
                                Item { Layout.fillWidth: true }
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: !Env.ffmpegOk && !Deps.busy
                                         && Deps.ffmpegBuild.source !== undefined
                                text: Deps.error.code !== undefined
                                    ? I18n.strings["deps.failed"].arg(Deps.error.code)
                                    : I18n.strings["deps.source"]
                                          .arg(Deps.ffmpegBuild.source)
                                          .arg(Deps.ffmpegBuild.license)
                                wrapMode: Text.WordWrap
                                color: Deps.error.code !== undefined ? Theme.errorFg : Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
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
                // Настройки, которые меняют редко, но выбирать их нужно до
                // запуска: сидеть восемьдесят минут у экрана ради одного вопроса
                // в конце никто не станет (требование FR-29).
                Panel {
                    id: advanced
                    property bool open: false

                    Layout.fillWidth: true
                    // Свёрнутая панель — ровно полоса заголовка. Раскрытая растёт
                    // по содержимому: якоря высоту родителю не задают, и без этой
                    // строки поля оказались бы нарисованы поверх подвала.
                    Layout.preferredHeight: 38 + (open ? body.implicitHeight + Theme.padPanel : 0)

                    RowLayout {
                        id: head
                        height: 38
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.leftMargin: Theme.padPanel
                        anchors.rightMargin: Theme.padPanel
                        spacing: 10

                        Text {
                            // Тот же знак, повёрнутый: «⌄» есть не в каждом шрифте,
                            // и на снимке вместо него оказался пустой квадрат.
                            text: "›"
                            rotation: advanced.open ? 90 : 0
                            color: Theme.textMuted
                            font.pixelSize: Theme.fontSection
                            Behavior on rotation { NumberAnimation { duration: Theme.fast } }
                        }
                        Text {
                            text: I18n.strings["advanced.title"]
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                        }
                        Text {
                            Layout.fillWidth: true
                            // Раскрытой панели сводка не нужна: те же значения
                            // стоят прямо в полях под заголовком.
                            visible: !advanced.open
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
                        Item { Layout.fillWidth: advanced.open }
                    }

                    MouseArea {
                        anchors.fill: head
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            advanced.open = !advanced.open
                            // Высота панели пересчитывается не в этот миг, а к
                            // следующему кадру — домотать можно только после.
                            if (advanced.open)
                                Qt.callLater(workArea.showBottom)
                        }
                    }

                    ColumnLayout {
                        id: body
                        visible: advanced.open
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: head.bottom
                        anchors.leftMargin: Theme.padPanel
                        anchors.rightMargin: Theme.padPanel
                        spacing: Theme.gapPanels

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.gapPanels

                            ComboField {
                                Layout.fillWidth: true
                                // Подсказки под полями разной длины, и без общего
                                // верха поля разъезжаются по высоте.
                                Layout.alignment: Qt.AlignTop
                                enabled_: !screen.audioOnly
                                hint: screen.audioOnly ? I18n.strings["advanced.asrOnly"]
                                                       : I18n.strings["advanced.sensitivityHint"]
                                label: I18n.strings["advanced.sensitivityField"]
                                model: screen.sensitivityValues.map(function (id) {
                                    return Fmt.tr("sensitivity." + id, id)
                                })
                                values: screen.sensitivityValues
                                value: Task.sensitivity
                                onChosen: function (id) { Task.setSensitivity(id) }
                            }
                            ComboField {
                                Layout.fillWidth: true
                                // Подсказки под полями разной длины, и без общего
                                // верха поля разъезжаются по высоте.
                                Layout.alignment: Qt.AlignTop
                                enabled_: !screen.audioOnly
                                hint: screen.audioOnly ? "" : I18n.strings["advanced.chunkHint"]
                                label: I18n.strings["advanced.chunkField"]
                                model: screen.chunkValues.map(function (n) {
                                    return I18n.strings["advanced.seconds"].arg(n)
                                })
                                values: screen.chunkValues.map(function (n) { return String(n) })
                                value: String(Task.chunkLength)
                                onChosen: function (n) { Task.setChunkLength(parseInt(n)) }
                            }
                            ComboField {
                                Layout.fillWidth: true
                                // Подсказки под полями разной длины, и без общего
                                // верха поля разъезжаются по высоте.
                                Layout.alignment: Qt.AlignTop
                                // Потоки решают только там, где считает процессор:
                                // при выбранной видеокарте пункт неактивен (FR-34).
                                enabled_: !screen.audioOnly && Task.device !== "cuda"
                                hint: I18n.strings["advanced.threadsHint"]
                                label: I18n.strings["advanced.threadsField"]
                                model: screen.threadValues.map(function (n) {
                                    return n === 0 ? I18n.strings["advanced.threadsAuto"] : String(n)
                                })
                                values: screen.threadValues.map(function (n) { return String(n) })
                                value: String(Task.cpuThreads)
                                onChosen: function (n) { Task.setCpuThreads(parseInt(n)) }
                            }
                            ComboField {
                                Layout.fillWidth: true
                                // Подсказки под полями разной длины, и без общего
                                // верха поля разъезжаются по высоте.
                                Layout.alignment: Qt.AlignTop
                                enabled_: !screen.audioOnly
                                hint: screen.audioOnly ? I18n.strings["advanced.noTemp"] : ""
                                label: I18n.strings["advanced.tempField"]
                                model: screen.tempValues.map(function (id) {
                                    return Fmt.tr("temp." + id, id)
                                })
                                values: screen.tempValues
                                value: Task.tempAction
                                onChosen: function (id) { Task.setTempAction(id) }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.gapLabel

                            CheckField {
                                enabled: !screen.audioOnly
                                text: I18n.strings["advanced.force"]
                                checked: Task.force
                                onToggled: Task.setForce(checked)
                            }
                            Text {
                                Layout.fillWidth: true
                                text: I18n.strings["advanced.forceHint"]
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }

                Item {
                    Layout.fillHeight: true
                    visible: !screen.hasFiles
                }
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
