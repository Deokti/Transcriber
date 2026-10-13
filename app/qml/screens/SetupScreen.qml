import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import Transcriber
import "../components"

// Первый запуск: нет ffmpeg или ни одной модели — объясняем, что нужно
// скачать, сколько это весит и куда ляжет, и качаем (FR-24, FR-26). Как в
// макете Artboards 3 (1m).
//
// Экран не запирает человека: «Позже» ведёт на главный, где готовность
// по-прежнему видна, а загрузка, если начата, продолжается сама.
Item {
    id: screen

    signal done()

    readonly property real mb: 1024 * 1024

    readonly property var chosen: Storage.models.find(function (m) { return m.id === Task.model }) || ({})
    readonly property bool ffmpegReady: Env.ffmpegOk
    readonly property bool modelReady: chosen.state === "ready"
    readonly property bool allReady: ffmpegReady && modelReady

    readonly property bool ffmpegLoading: Deps.busy
    readonly property bool modelLoading: Storage.downloading !== "" && Storage.downloading === Task.model
    readonly property bool busy: ffmpegLoading || modelLoading

    readonly property bool ffmpegFailed: !Deps.busy && Deps.error.code !== undefined && !ffmpegReady
    readonly property bool modelFailed: !modelLoading && Storage.error.model === Task.model

    readonly property real ffmpegBytes: Deps.bytesTotal > 0 ? Deps.bytesTotal
                                                             : (Deps.ffmpegBuild.sizeMb || 0) * mb
    readonly property real modelBytes: (chosen.sizeMb || 0) * mb

    // Что качаем — запоминается, когда экран открылся: иначе скачанное
    // выпадало бы из «Скачано X из Y», и итог уменьшался бы по ходу дела.
    property bool planFfmpeg: false
    property bool planModel: false

    function plan() {
        if (busy)
            return
        planFfmpeg = !ffmpegReady
        planModel = !modelReady
    }
    Component.onCompleted: plan()
    onVisibleChanged: if (visible) plan()

    readonly property real total: (planFfmpeg ? ffmpegBytes : 0) + (planModel ? modelBytes : 0)
    readonly property real reached:
        (planFfmpeg ? (ffmpegReady ? ffmpegBytes : ffmpegLoading ? Deps.bytesDone : 0) : 0)
        + (planModel ? (modelReady ? modelBytes
                        : modelLoading ? Storage.bytesDone
                        : chosen.state === "partial" ? (chosen.bytes || 0) : 0) : 0)
    // Сколько ещё ляжет на диск — с этим сравниваем свободное место
    readonly property real remaining: Math.max(0, total - reached)

    function start() {
        if (!ffmpegReady && !Deps.busy)
            Deps.getFfmpeg()
        if (!modelReady && Storage.downloading === "")
            Storage.downloadModel(Task.model)
    }

    // Приостановить: обрывок модели остаётся, «Скачать» продолжит с места
    function pause() {
        if (Deps.busy)
            Deps.cancel()
        if (modelLoading)
            Storage.pause()
    }

    function percent(done, total) {
        return total > 0 ? Math.round(100 * done / total) : 0
    }

    FolderDialog {
        id: picker
        title: I18n.strings["action.choose"]
        onAccepted: {
            Settings.setModelsDir(selectedFolder)
            Settings.save()
            Storage.refresh()
            screen.plan()
        }
    }

    // --- строка «что качаем» ---------------------------------------------------
    component SetupItem: Rectangle {
        id: item

        property string icon: "download"
        property string title: ""
        property string about: ""
        property string detail: ""
        property bool failed: false
        property bool busy: false
        property real progress: 0

        Layout.fillWidth: true
        implicitHeight: line.implicitHeight + 36
        color: failed ? Theme.errorBg : "transparent"

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: Theme.rowDivider
        }

        RowLayout {
            id: line
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: 18
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 16

            StatusIcon {
                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 3
                level: item.failed ? "fail" : item.icon
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Text {
                    Layout.fillWidth: true
                    text: item.title
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontMessage
                    font.weight: Theme.weightSemiBold
                    wrapMode: Text.WordWrap
                }
                Text {
                    Layout.fillWidth: true
                    Layout.maximumWidth: Theme.textWidth
                    text: item.about
                    color: Theme.textBody
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    wrapMode: Text.WordWrap
                    lineHeight: 1.15
                }
                ProgressBar {
                    Layout.topMargin: 4
                    Layout.preferredWidth: Math.min(520, parent.width)
                    visible: item.busy || (item.progress > 0 && item.progress < 1)
                    value: item.progress
                    known: item.progress > 0
                }
                Text {
                    Layout.fillWidth: true
                    visible: text !== ""
                    text: item.detail
                    color: item.failed ? Theme.errorFg
                         : item.icon === "ok" ? Theme.okFg : Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: page.implicitHeight + Theme.padFirst * 2
            boundsBehavior: Flickable.StopAtBounds
            clip: true

            ColumnLayout {
                id: page
                x: Theme.padFirst
                y: Theme.padFirst
                width: parent.width - Theme.padFirst * 2
                spacing: Theme.gapPanels

                Text {
                    Layout.fillWidth: true
                    text: screen.allReady ? I18n.strings["setup.title.ready"]
                        : screen.planFfmpeg && screen.planModel ? I18n.strings["setup.title.both"]
                        : screen.planFfmpeg ? I18n.strings["setup.title.ffmpeg"]
                        : I18n.strings["setup.title.model"]
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontTitle
                    font.weight: Theme.weightSemiBold
                    wrapMode: Text.WordWrap
                }
                Text {
                    Layout.fillWidth: true
                    Layout.maximumWidth: Theme.textWidth + 120
                    text: screen.allReady ? I18n.strings["setup.introReady"]
                                          : I18n.strings["setup.intro"].arg(Fmt.fileSize(screen.total))
                    color: Theme.textBody
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    wrapMode: Text.WordWrap
                    lineHeight: 1.2
                }

                // --- что качаем ---------------------------------------------
                Panel {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    Layout.preferredHeight: items.implicitHeight - 1
                    clip: true

                    ColumnLayout {
                        id: items
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.topMargin: -1
                        spacing: 0

                        SetupItem {
                            icon: screen.ffmpegReady ? "ok" : "download"
                            title: I18n.strings["setup.ffmpeg"] + (Env.ffmpegVersion !== "" ? " " + Env.ffmpegVersion : "")
                            about: I18n.strings["setup.ffmpegAbout"]
                            failed: screen.ffmpegFailed
                            busy: screen.ffmpegLoading
                            progress: Deps.bytesTotal > 0 ? Deps.bytesDone / Deps.bytesTotal : 0
                            detail: screen.ffmpegReady ? I18n.strings["setup.inPlace"]
                                  : screen.ffmpegFailed ? I18n.strings["storage.failedFfmpeg"]
                                  : screen.ffmpegLoading
                                    ? I18n.strings["setup.progress"].arg(Fmt.fileSize(Deps.bytesDone))
                                          .arg(Fmt.fileSize(screen.ffmpegBytes))
                                  : I18n.strings["setup.waiting"].arg(Fmt.fileSize(screen.ffmpegBytes))
                        }

                        SetupItem {
                            readonly property real speed: Storage.speed

                            icon: screen.modelReady ? "ok" : "download"
                            title: I18n.strings["setup.model"].arg(Task.model)
                            about: screen.chosen.multilingual === false ? I18n.strings["setup.modelAbout.en"]
                                                                        : I18n.strings["setup.modelAbout.multi"]
                            failed: screen.modelFailed
                            busy: screen.modelLoading
                            progress: screen.modelLoading
                                      ? (Storage.bytesTotal > 0 ? Storage.bytesDone / Storage.bytesTotal : 0)
                                      : screen.chosen.state === "partial" && screen.modelBytes > 0
                                        ? (screen.chosen.bytes || 0) / screen.modelBytes : 0
                            detail: screen.modelReady ? I18n.strings["setup.inPlace"]
                                  : screen.modelFailed
                                    ? (Storage.error.reason === "network" ? I18n.strings["storage.failedNetwork"]
                                                                          : I18n.strings["storage.failedOther"])
                                          .arg(Fmt.fileSize(Storage.error.bytes || 0))
                                  : screen.modelLoading
                                    ? [I18n.strings["setup.progress"].arg(Fmt.fileSize(Storage.bytesDone))
                                           .arg(Fmt.fileSize(Storage.bytesTotal))]
                                      .concat(speed > 0 ? [I18n.strings["setup.speed"].arg(Fmt.fileSize(speed)),
                                                           I18n.strings["setup.left"].arg(Fmt.roughDuration(
                                                               (Storage.bytesTotal - Storage.bytesDone) / speed))]
                                                        : [])
                                      .join(" · ")
                                  : screen.chosen.state === "partial"
                                    ? I18n.strings["storage.partialDetail"].arg(Fmt.fileSize(screen.chosen.bytes || 0))
                                  : I18n.strings["setup.waiting"].arg(Fmt.fileSize(screen.modelBytes))
                        }
                    }
                }

                // --- куда положить ------------------------------------------
                FolderRow {
                    Layout.fillWidth: true
                    Layout.topMargin: 6
                    enabled: !screen.busy
                    label: I18n.strings["setup.where"]
                    value: Settings.modelsDir
                    placeholder: Settings.defaultModelsDir
                    hint: Storage.freeBytes > 0 && Storage.freeBytes < screen.remaining
                          ? I18n.strings["setup.freeLow"].arg(Fmt.fileSize(Storage.freeBytes))
                                .arg(Fmt.fileSize(screen.remaining))
                          : I18n.strings["setup.free"].arg(Fmt.fileSize(Storage.freeBytes))
                    onChoose: picker.open()
                    onReset: {
                        Settings.setModelsDir("")
                        Settings.save()
                        Storage.refresh()
                        screen.plan()
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: !screen.ffmpegReady
                    text: I18n.strings["setup.ffmpegHome"].arg(Storage.dataDir)
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: 10
                    Layout.maximumWidth: Theme.textWidth + 120
                    visible: !screen.modelReady && (screen.chosen.repo || "") !== ""
                    text: I18n.strings["setup.manual"].arg(screen.chosen.repo || "").arg(screen.chosen.home || "")
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    wrapMode: Text.WordWrap
                    lineHeight: 1.15
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

                Text {
                    Layout.fillWidth: true
                    text: screen.total <= 0 ? ""
                        : screen.reached > 0 ? I18n.strings["setup.done"].arg(Fmt.fileSize(screen.reached))
                                                   .arg(Fmt.fileSize(screen.total))
                        : I18n.strings["setup.total"].arg(Fmt.fileSize(screen.total))
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    elide: Text.ElideRight
                }

                AppButton {
                    visible: !screen.allReady
                    text: I18n.strings["setup.later"]
                    onClicked: screen.done()
                }
                AppButton {
                    visible: screen.busy
                    text: I18n.strings["storage.pause"]
                    onClicked: screen.pause()
                }
                AppButton {
                    visible: !screen.busy && !screen.allReady
                    primary: true
                    text: screen.ffmpegFailed || screen.modelFailed ? I18n.strings["storage.retry"]
                        : screen.chosen.state === "partial" ? I18n.strings["storage.resume"]
                        : I18n.strings["setup.download"]
                    onClicked: screen.start()
                }
                AppButton {
                    visible: screen.allReady
                    primary: true
                    text: I18n.strings["setup.continue"]
                    onClicked: screen.done()
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
                text: (screen.modelLoading
                       ? I18n.strings["setup.status.model"].arg(screen.percent(Storage.bytesDone, Storage.bytesTotal)) + " · "
                       : screen.ffmpegLoading
                       ? I18n.strings["setup.status.ffmpeg"].arg(screen.percent(Deps.bytesDone, Deps.bytesTotal)) + " · "
                       : screen.allReady ? I18n.strings["setup.status.ready"] + " · " : "")
                      + I18n.strings["setup.status.private"]
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }
    }
}
