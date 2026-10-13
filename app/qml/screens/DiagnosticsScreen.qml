import QtCore
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import Transcriber
import "../components"

// Диагностика (FR-27): пять проверок, у каждой своё действие, и журнал
// последнего запуска — как в макете Artboards 3. Экран отвечает на
// «почему не работает» раньше, чем человек пойдёт это спрашивать.
//
// Проверки делает ядро и отвечает уровнем и кодом; слова — здесь.
Item {
    id: screen

    property string origin: "main"

    signal home()
    signal navigate(string name)

    // Куда отправлять за драйвером и за сборкой с поддержкой видеокарты
    readonly property string driverUrl: "https://www.nvidia.com/drivers"
    readonly property string releasesUrl: "https://github.com/Deokti/Transcriber/releases/latest"

    // Открыли экран — проверяем заново: за время, пока он был скрыт, машина
    // могла измениться. Окно может и открыться сразу на нём — тогда смены
    // видимости не будет, отсюда второй вызов.
    onVisibleChanged: if (visible) Diagnostics.refresh()
    Component.onCompleted: if (visible) Diagnostics.refresh()

    // Скачался ffmpeg, удалили модель, сменили папку — итог проверок другой.
    // Все такие перемены проходят через опрос машины, его и слушаем.
    Connections {
        target: Env
        function onChanged() { if (screen.visible) Diagnostics.refresh() }
    }

    readonly property var checks: Diagnostics.checks
    readonly property int okCount: checks.filter(function (c) { return c.level === "ok" }).length
    readonly property int failCount: checks.filter(function (c) { return c.level === "fail" }).length
    readonly property int remarkCount: checks.length - okCount - failCount

    readonly property var logLines: Diagnostics.log.map(function (item) { return Fmt.logLine(item) })
                                                   .filter(function (line) { return line !== "" })
    readonly property string logText: logLines.join("\n")

    function check(id) {
        for (let i = 0; i < checks.length; i++)
            if (checks[i].id === id)
                return checks[i]
        return null
    }

    // «три в порядке», «одна с замечанием»: число словом, как в макете
    function counted(key, n) {
        const words = I18n.strings["diag.numbers"].split("|")
        const forms = I18n.strings[key].split("|")
        return (n === 1 ? forms[0] : forms[forms.length - 1]).arg(words[n - 1] || String(n))
    }

    readonly property string title: checks.length === 0 ? I18n.strings["diag.checking"]
        : okCount === checks.length ? I18n.strings["diag.allOk"]
        : I18n.strings["diag.summary"].arg(
              [okCount > 0 ? counted("diag.ok", okCount) : "",
               remarkCount > 0 ? counted("diag.remarks", remarkCount) : "",
               failCount > 0 ? counted("diag.failed", failCount) : ""]
              .filter(function (part) { return part !== "" }).join(", "))

    function clock(iso) {
        return iso ? Qt.locale(I18n.language).toString(new Date(iso), "HH:mm") : ""
    }

    // Где пойдёт расчёт на самом деле: выбрана видеокарта и она отвечает
    readonly property bool onGpu: Task.device === "cuda"
                                  && (check("gpu") || {}).code === "GPU_READY"

    readonly property string statusText: Diagnostics.verdict === "blocked"
                                         ? I18n.strings["diag.status.blocked"]
                                         : I18n.strings[onGpu ? "diag.status.cuda" : "diag.status.cpu"]

    FolderDialog {
        id: ffmpegPicker
        title: I18n.strings["action.choose"]
        onAccepted: {
            Settings.setFfmpegDir(selectedFolder)
            Settings.save()
        }
    }

    FileDialog {
        id: saver
        fileMode: FileDialog.SaveFile
        defaultSuffix: "txt"
        nameFilters: ["*.txt"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        selectedFile: currentFolder + "/" + I18n.strings["diag.logName"]
        onAccepted: if (Diagnostics.save(selectedFile, screen.logText)) saved.restart()
    }

    // «Скопировано» и «Сохранено» держатся пару секунд — видно, что сработало
    Timer { id: copied; interval: 2000 }
    Timer { id: saved; interval: 2000 }

    // --- строка проверки ------------------------------------------------------
    component CheckRow: Rectangle {
        id: row

        property string level: "ok"
        property string title: ""
        property string detail: ""
        property bool mono: false            // подробность — путь к файлу
        property bool busy: false
        property real progress: 0
        default property alias actions: actionsColumn.data

        Layout.fillWidth: true
        implicitHeight: line.implicitHeight + 28
        color: level === "fail" ? Theme.errorBg
             : level === "ok" ? "transparent" : Theme.warnRowBg

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: Theme.rowDivider
        }

        // Текст и значок прижаты к верху, кнопки — по середине строки.
        // Одна кнопка встаёт против текста, две — растягивают строку, и
        // текст оказывается вровень с первой из них, как в макете.
        RowLayout {
            id: line
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: 14
            anchors.leftMargin: 16
            anchors.rightMargin: 14
            spacing: 14

            StatusIcon {
                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 2
                level: row.level
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 5

                Text {
                    Layout.fillWidth: true
                    text: row.title
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.weight: Theme.weightSemiBold
                    wrapMode: Text.WordWrap
                }
                Text {
                    Layout.fillWidth: true
                    visible: text !== ""
                    text: row.detail
                    color: row.level === "ok" ? Theme.textMuted : Theme.textBody
                    font.family: row.mono ? Theme.monoFamily : Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    wrapMode: row.mono ? Text.WrapAnywhere : Text.WordWrap
                }
                ProgressBar {
                    Layout.preferredWidth: 280
                    visible: row.busy
                    value: row.progress
                    known: row.progress > 0
                }
            }

            ColumnLayout {
                id: actionsColumn
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                spacing: 8
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ServiceBar {
            Layout.fillWidth: true
            current: "diagnostics"
            origin: screen.origin
            onHome: screen.home()
            onNavigate: function (name) { screen.navigate(name) }
        }

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: page.implicitHeight + Theme.padScreen * 2
            boundsBehavior: Flickable.StopAtBounds
            clip: true

            ColumnLayout {
                id: page
                x: Theme.padScreen
                y: Theme.padScreen
                width: parent.width - Theme.padScreen * 2
                spacing: Theme.gapPanels

                // --- заголовок ----------------------------------------------
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.gapButtons

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text {
                            Layout.fillWidth: true
                            text: screen.title
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSection + 3
                            font.weight: Theme.weightSemiBold
                            wrapMode: Text.WordWrap
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: Diagnostics.checkedAt !== ""
                            text: I18n.strings["diag.checkedAt"]
                                      .arg(Fmt.day(Diagnostics.checkedAt))
                                      .arg(screen.clock(Diagnostics.checkedAt))
                                  + " · " + I18n.strings["diag.verdict." + (Diagnostics.verdict || "ready")]
                            color: Diagnostics.verdict === "blocked" ? Theme.errorFg : Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            wrapMode: Text.WordWrap
                        }
                    }
                    AppButton {
                        Layout.alignment: Qt.AlignTop
                        enabled: !Diagnostics.busy
                        text: Diagnostics.busy ? I18n.strings["diag.checking"]
                                               : I18n.strings["diag.recheck"]
                        onClicked: Diagnostics.refresh()
                    }
                }

                // --- проверки -----------------------------------------------
                Panel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: rows.implicitHeight - 1
                    visible: screen.checks.length > 0
                    clip: true

                    ColumnLayout {
                        id: rows
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.topMargin: -1      // у первой строки черта сверху не нужна
                        spacing: 0

                        // ffmpeg ---------------------------------------------
                        CheckRow {
                            id: ffmpegRow

                            readonly property var c: screen.check("ffmpeg") || {data: {}}
                            readonly property bool found: c.code === "FFMPEG_FOUND"
                            readonly property bool missing: c.code === "FFMPEG_MISSING"
                            readonly property bool failed_: !Deps.busy && Deps.error.code !== undefined

                            visible: screen.check("ffmpeg") !== null
                            level: Deps.busy ? "note" : (c.level || "ok")
                            title: c.code === "CHECK_FAILED" ? I18n.strings["diag.CHECK_FAILED"]
                                 : found ? I18n.strings["diag.FFMPEG_FOUND"].arg(c.data.version || "")
                                 : I18n.strings["diag.FFMPEG_MISSING"]
                            detail: c.code === "CHECK_FAILED" ? (c.data.reason || "")
                                  : Deps.busy ? I18n.strings["diag.ffmpegLoading"]
                                                    .arg(Fmt.fileSize(Deps.bytesDone))
                                                    .arg(Fmt.fileSize(Deps.bytesTotal))
                                  : failed_ ? I18n.strings["storage.failedFfmpeg"]
                                  : found ? (c.data.path || "")
                                  : I18n.strings["diag.FFMPEG_MISSING.detail"]
                                        .arg(Fmt.fileSize((Deps.ffmpegBuild.sizeMb || 0) * 1024 * 1024))
                            mono: found && !Deps.busy
                            busy: Deps.busy
                            progress: Deps.bytesTotal > 0 ? Deps.bytesDone / Deps.bytesTotal : 0

                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: ffmpegRow.found
                                text: I18n.strings["diag.reveal"]
                                onClicked: Shell.reveal(ffmpegRow.c.data.path)
                            }
                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: ffmpegRow.missing && !Deps.busy
                                primary: true
                                text: ffmpegRow.failed_ ? I18n.strings["storage.retry"]
                                                        : I18n.strings["storage.download"]
                                onClicked: Deps.getFfmpeg()
                            }
                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: ffmpegRow.missing && !Deps.busy
                                text: I18n.strings["diag.pickFfmpeg"]
                                onClicked: ffmpegPicker.open()
                            }
                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: Deps.busy
                                text: I18n.strings["storage.cancel"]
                                onClicked: Deps.cancel()
                            }
                        }

                        // видеокарта ----------------------------------------
                        CheckRow {
                            id: gpuRow

                            readonly property var c: screen.check("gpu") || {data: {}}
                            readonly property var d: c.data || {}

                            visible: screen.check("gpu") !== null
                            level: c.level || "ok"
                            title: c.code === "GPU_READY" ? I18n.strings["diag.GPU_READY"].arg(d.name || "")
                                 : Fmt.tr("diag." + c.code, c.code || "")
                            detail: c.code === "GPU_READY" ? I18n.strings["diag.GPU_READY.detail"].arg(d.driver || "")
                                  : c.code === "GPU_NO_CUDA"
                                    ? Fmt.tr("diag.GPU_NO_CUDA." + d.reason, "").arg(d.name || "")
                                  : c.code === "GPU_OLD_DRIVER"
                                    ? I18n.strings["diag.GPU_OLD_DRIVER.detail"].arg(d.name || "")
                                          .arg(d.driver || "").arg(d.required || "")
                                  : c.code === "GPU_SILENT"
                                    ? I18n.strings["diag.GPU_SILENT.detail"].arg(d.name || "").arg(d.driver || "")
                                  : Fmt.tr("diag." + c.code + ".detail", "")

                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: gpuRow.c.code === "GPU_OLD_DRIVER" || gpuRow.c.code === "GPU_SILENT"
                                primary: true
                                text: I18n.strings["diag.driverHelp"]
                                onClicked: Qt.openUrlExternally(screen.driverUrl)
                            }
                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: gpuRow.c.code === "GPU_NO_CUDA" && gpuRow.d.reason === "NO_CUDA_IN_BUILD"
                                primary: true
                                text: I18n.strings["diag.getBuild"]
                                onClicked: Qt.openUrlExternally(screen.releasesUrl)
                            }
                        }

                        // модели --------------------------------------------
                        CheckRow {
                            id: modelsRow

                            readonly property var c: screen.check("models") || {data: {}}
                            readonly property var d: c.data || {}
                            readonly property var ready: d.ready || []
                            readonly property var partial: d.partial || []
                            readonly property bool loading: Storage.downloading !== ""

                            visible: screen.check("models") !== null
                            level: loading ? "note" : (c.level || "ok")
                            title: c.code === "MODELS_READY"
                                   ? (ready.length === 1 ? I18n.strings["diag.MODELS_READY.one"].arg(ready[0])
                                                         : I18n.strings["diag.MODELS_READY.many"].arg(ready.join(", ")))
                                 : c.code === "MODEL_CHOSEN_MISSING"
                                   ? I18n.strings["diag.MODEL_CHOSEN_MISSING"].arg(d.chosen || "")
                                 : I18n.strings["diag.MODELS_NONE"]
                            detail: loading
                                    ? I18n.strings["diag.modelLoading"].arg(Storage.downloading)
                                          .arg(Fmt.fileSize(Storage.bytesDone)).arg(Fmt.fileSize(Storage.bytesTotal))
                                  : c.code === "MODELS_READY"
                                    ? I18n.strings["diag.MODELS_READY.detail"].arg(Fmt.fileSize(d.bytes))
                                          .arg(d.chosen || "")
                                      + (partial.length > 0
                                         ? " · " + I18n.strings["diag.partial"].arg(partial.join(", ")) : "")
                                  : c.code === "MODEL_CHOSEN_MISSING"
                                    ? I18n.strings["diag.MODEL_CHOSEN_MISSING.detail"]
                                          .arg(Fmt.fileSize(d.chosenBytes)).arg(ready.join(", "))
                                  : I18n.strings["diag.MODELS_NONE.detail"].arg(d.chosen || "")
                                          .arg(Fmt.fileSize(d.chosenBytes))
                            busy: loading
                            progress: Storage.bytesTotal > 0 ? Storage.bytesDone / Storage.bytesTotal : 0

                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: modelsRow.c.code !== "MODELS_READY" && !modelsRow.loading
                                primary: true
                                text: I18n.strings["storage.download"]
                                onClicked: Storage.downloadModel(modelsRow.d.chosen)
                            }
                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: modelsRow.loading
                                text: I18n.strings["storage.cancel"]
                                onClicked: Storage.cancel()
                            }
                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                text: I18n.strings["diag.openStorage"]
                                onClicked: screen.navigate("storage")
                            }
                        }

                        // временные файлы -----------------------------------
                        CheckRow {
                            id: tempRow

                            readonly property var c: screen.check("temp") || {data: {}}
                            readonly property var d: c.data || {}
                            readonly property bool piled: c.code === "TEMP_PILED"

                            visible: screen.check("temp") !== null
                            level: c.level || "ok"
                            title: piled ? I18n.strings["diag.TEMP_PILED"].arg(Fmt.fileSize(d.bytes))
                                         : I18n.strings["diag.TEMP_EMPTY"]
                            detail: piled ? I18n.strings["diag.TEMP_PILED.detail"]
                                                .arg(Fmt.plural(d.count, I18n.strings["storage.files"]))
                                          : I18n.strings["diag.TEMP_EMPTY.detail"]

                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: tempRow.piled
                                enabled: !Storage.locked
                                text: I18n.strings["storage.clearTemp"]
                                onClicked: Storage.clearTemp()
                            }
                        }

                        // место на диске ------------------------------------
                        CheckRow {
                            id: diskRow

                            readonly property var c: screen.check("disk") || {data: {}}
                            readonly property var d: c.data || {}
                            readonly property bool low: c.code === "DISK_LOW"

                            visible: screen.check("disk") !== null
                            level: c.level || "ok"
                            title: I18n.strings[low ? "diag.DISK_LOW" : "diag.DISK_OK"].arg(Fmt.fileSize(d.free))
                            detail: I18n.strings["diag.disk.need"].arg(Fmt.fileSize((d.need || 0) - (d.model || 0)))
                                    + (d.model > 0 ? I18n.strings["diag.disk.model"].arg(Fmt.fileSize(d.model)) : "")
                                    + (low ? I18n.strings["diag.disk.low"] : "")

                            AppButton {
                                Layout.alignment: Qt.AlignRight
                                visible: diskRow.low
                                text: I18n.strings["diag.openStorage"]
                                onClicked: screen.navigate("storage")
                            }
                        }
                    }
                }

                // --- журнал последнего запуска ------------------------------
                Panel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: logColumn.implicitHeight

                    ColumnLayout {
                        id: logColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        spacing: 0

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: 16
                            Layout.rightMargin: 8
                            Layout.topMargin: 6
                            Layout.bottomMargin: 6
                            spacing: 4

                            SectionTitle {
                                Layout.fillWidth: true
                                text: I18n.strings["diag.log"]
                            }
                            AppButton {
                                flat_: true
                                enabled: screen.logLines.length > 0
                                text: copied.running ? I18n.strings["diag.copied"] : I18n.strings["diag.copy"]
                                onClicked: {
                                    Diagnostics.copy(screen.logText)
                                    copied.restart()
                                }
                            }
                            AppButton {
                                flat_: true
                                enabled: screen.logLines.length > 0
                                text: saved.running ? I18n.strings["diag.saved"] : I18n.strings["diag.saveLog"]
                                onClicked: saver.open()
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: Theme.rowDivider
                        }

                        // Выделяется мышью: бывает нужна одна строка, а не весь журнал
                        TextEdit {
                            Layout.fillWidth: true
                            Layout.margins: 16
                            readOnly: true
                            selectByMouse: true
                            text: screen.logLines.length > 0 ? screen.logText : I18n.strings["diag.logEmpty"]
                            color: screen.logLines.length > 0 ? Theme.textBody : Theme.textMuted
                            selectionColor: Theme.accent
                            selectedTextColor: Theme.accentText
                            font.family: screen.logLines.length > 0 ? Theme.monoFamily : Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            wrapMode: TextEdit.Wrap
                        }
                    }
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
                text: Diagnostics.checkedAt === "" ? I18n.strings["diag.checking"]
                      : I18n.strings["diag.status"].arg(screen.clock(Diagnostics.checkedAt))
                        + " · " + screen.statusText
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }
    }
}
