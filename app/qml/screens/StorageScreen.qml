import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import Transcriber
import "../components"

// Хранилище: что программа держит на диске, сколько это весит, что удалить
// (FR-25, решение D-5). Таблица «что скачано · размер · состояние» — как в
// макете Artboards 3. На маке «перетащил программу в корзину — исчезли все
// три гигабайта» не бывает, и честный ответ на это — экран внутри программы.
//
// Состояния из брифа: ничего не скачано · идёт загрузка · загрузка сорвалась.
Item {
    id: screen

    property string origin: "main"

    signal home()
    signal navigate(string name)

    // Опрос по требованию: подсчёт быстрый, но смотреть на устаревшие числа
    // после удаления в проводнике было бы странно.
    onVisibleChanged: if (visible) Storage.refresh()

    readonly property bool nothing: Storage.downloadedBytes <= 0
    readonly property real actionWidth: Math.max(longest.width, 92) + 28

    // Кнопки строк одной ширины — по самой длинной надписи на текущем языке.
    // Иначе «Удалить» с запасом под «Точно удалить?» шире «Скачать», и правый
    // край таблицы гуляет от строки к строке.
    TextMetrics {
        id: longest
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBase
        text: ["storage.confirm", "storage.download", "storage.resume", "storage.retry",
               "storage.pause", "storage.cancel", "storage.drop"]
              .map(function (key) { return I18n.strings[key] || "" })
              .reduce(function (a, b) { return a.length >= b.length ? a : b })
    }

    FolderDialog {
        id: picker
        title: I18n.strings["action.choose"]
        onAccepted: {
            Settings.setModelsDir(selectedFolder)
            Settings.save()
            Storage.refresh()
        }
    }

    function modelState(m) {
        if (Storage.downloading === m.id) return "downloading"
        if (Storage.error.model === m.id) return "failed"
        return m.state
    }

    function percent(done, total) {
        return total > 0 ? Math.round(100 * done / total) : 0
    }

    // --- строка таблицы ------------------------------------------------------
    // Колонки одинаковой ширины во всех строках: размер и состояние читаются
    // столбиком, а не вразнобой. У постоянных колонок наименьшая ширина равна
    // обычной: в узком окне раскладка ужимает всё, что ей позволено, и
    // строка с длинным описанием сдвигала бы их сильнее короткой.
    component TableRow: Rectangle {
        id: row

        property string title: ""
        property string detail: ""
        property string size: ""
        property string state_: ""
        property color stateColor: Theme.textMuted
        property bool ok: false
        property bool failed: false
        property bool busy: false
        property real progress: 0
        default property alias actions: actionsRow.data

        Layout.fillWidth: true
        implicitHeight: content.implicitHeight + 20
        color: failed ? Theme.errorBg : "transparent"

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: Theme.rowDivider
        }

        RowLayout {
            id: content
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3

                RowLayout {
                    spacing: 6
                    // Знаки рисованные, а не символы шрифта: «✓» и «✕» есть
                    // не в каждом шрифте, и без замены выходит квадратик.
                    StatusIcon {
                        visible: row.failed
                        level: "fail"
                    }
                    Text {
                        text: row.title
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                    }
                }
                ProgressBar {
                    Layout.preferredWidth: 280
                    visible: row.busy
                    value: row.progress
                    known: row.progress > 0
                }
                Text {
                    Layout.fillWidth: true
                    visible: text !== ""
                    text: row.detail
                    color: row.failed ? Theme.errorFg : Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    wrapMode: Text.WordWrap
                }
            }
            Text {
                objectName: "sizeCell"       // по нему тест сверяет столбец
                Layout.preferredWidth: 90
                Layout.minimumWidth: 90
                text: row.size
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
            }
            RowLayout {
                Layout.preferredWidth: 130
                Layout.minimumWidth: 130
                Layout.maximumWidth: 130
                spacing: 7
                CheckMark {
                    visible: row.ok
                    width: 11
                    height: 11
                    color: row.stateColor
                }
                Text {
                    Layout.fillWidth: true
                    text: row.state_
                    color: row.stateColor
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    elide: Text.ElideRight
                }
            }
            // Колонка кнопок держит ширину и пустой: раскладка сжимает
            // RowLayout без видимых детей в ноль, и размер с состоянием
            // в такой строке уезжали влево от столбца.
            Item {
                Layout.preferredWidth: screen.actionWidth * 2 + Theme.gapButtons
                Layout.minimumWidth: screen.actionWidth * 2 + Theme.gapButtons
                implicitHeight: actionsRow.implicitHeight

                RowLayout {
                    id: actionsRow
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    layoutDirection: Qt.RightToLeft
                    spacing: Theme.gapButtons
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ServiceBar {
            Layout.fillWidth: true
            current: "storage"
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
                            text: screen.nothing
                                  ? I18n.strings["storage.nothing"]
                                  : I18n.strings["storage.downloaded"].arg(
                                        Fmt.fileSize(Storage.downloadedBytes))
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSection + 3
                            font.weight: Theme.weightSemiBold
                        }
                        Text {
                            Layout.fillWidth: true
                            text: Storage.dataDir + " · " + I18n.strings["storage.free"]
                                  .arg(Fmt.fileSize(Storage.freeBytes))
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            elide: Text.ElideMiddle
                        }
                        // Модели лежат не в папке данных — значит, человек указал
                        // свою, часто общий кеш HuggingFace. Чужое там не трогаем,
                        // и это стоит сказать: иначе непонятно, почему папка в
                        // проводнике весит больше, чем здесь.
                        Text {
                            Layout.fillWidth: true
                            visible: Storage.modelsDir.indexOf(Storage.dataDir) !== 0
                            text: I18n.strings["storage.modelsElsewhere"].arg(Storage.modelsDir)
                                  + (Storage.foreign > 0
                                     ? " " + I18n.strings["storage.shared"].arg(Storage.foreign) : "")
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            wrapMode: Text.WordWrap
                        }
                    }
                    AppButton {
                        Layout.alignment: Qt.AlignTop
                        text: I18n.strings["storage.openFolder"]
                        onClicked: Shell.open(Storage.dataDir)
                    }
                    AppButton {
                        Layout.alignment: Qt.AlignTop
                        text: I18n.strings["storage.changeFolder"]
                        enabled: !Storage.locked && Storage.downloading === ""
                        onClicked: picker.open()
                    }
                }

                // Пустое состояние объясняет, что тут будет и с чего начать
                // (раздел 7 брифа), а не показывает пустую таблицу.
                Rectangle {
                    Layout.fillWidth: true
                    visible: screen.nothing
                    implicitHeight: emptyText.implicitHeight + 28
                    color: "transparent"
                    border.color: Theme.panelBorder
                    border.width: 1
                    radius: Theme.radiusPanel
                    Text {
                        id: emptyText
                        anchors.fill: parent
                        anchors.margins: 14
                        text: I18n.strings["storage.empty"]
                        color: Theme.textBody
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        wrapMode: Text.WordWrap
                    }
                }

                // Работа идёт — удалять нельзя: движок держит модель открытой.
                Text {
                    Layout.fillWidth: true
                    visible: Storage.locked
                    text: I18n.strings["storage.locked"]
                    color: Theme.warnFg
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    wrapMode: Text.WordWrap
                }

                // --- таблица ------------------------------------------------
                Panel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: table.implicitHeight

                    ColumnLayout {
                        id: table
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        spacing: 0

                        // шапка
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: 14
                            Layout.rightMargin: 14
                            Layout.topMargin: 10
                            Layout.bottomMargin: 8
                            spacing: 12
                            Text {
                                Layout.fillWidth: true
                                text: I18n.strings["storage.colWhat"]
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                            }
                            Text {
                                objectName: "sizeCell"
                                Layout.preferredWidth: 90
                                Layout.minimumWidth: 90
                                text: I18n.strings["storage.colSize"]
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                            }
                            Text {
                                Layout.preferredWidth: 130
                                Layout.minimumWidth: 130
                                text: I18n.strings["storage.colState"]
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                            }
                            Item {
                                Layout.preferredWidth: screen.actionWidth * 2 + Theme.gapButtons
                                Layout.minimumWidth: screen.actionWidth * 2 + Theme.gapButtons
                            }
                        }

                        // --- ffmpeg --------------------------------------------
                        TableRow {
                            readonly property var tool: Storage.ffmpeg
                            readonly property bool failed_: !Deps.busy && Deps.error.code !== undefined

                            title: "ffmpeg" + (tool.found ? " " + Env.ffmpegVersion : "")
                            detail: Deps.busy
                                    ? I18n.strings["storage.progress"]
                                          .arg(Fmt.fileSize(Deps.bytesDone))
                                          .arg(Fmt.fileSize(Deps.bytesTotal))
                                    : failed_ ? I18n.strings["storage.failedFfmpeg"]
                                    : tool.ours ? I18n.strings["storage.ffmpegNeeded"] + " · "
                                                  + I18n.strings["storage.ffmpegDate"]
                                                    .arg(Fmt.day(tool.date))
                                    : tool.found ? I18n.strings["storage.ffmpegNeeded"] + " · "
                                                   + I18n.strings["storage.ffmpegSystem"]
                                                     .arg(Fmt.folderOf(tool.path))
                                    : I18n.strings["storage.ffmpegNeeded"]
                            size: tool.ours ? Fmt.fileSize(tool.bytes)
                                  : tool.found ? "—"
                                  : Fmt.fileSize((Deps.ffmpegBuild.sizeMb || 0) * 1024 * 1024)
                            ok: tool.found === true && !Deps.busy
                            failed: failed_
                            busy: Deps.busy
                            progress: Deps.bytesTotal > 0 ? Deps.bytesDone / Deps.bytesTotal : 0
                            state_: Deps.busy
                                    ? I18n.strings["storage.downloading"]
                                          .arg(screen.percent(Deps.bytesDone, Deps.bytesTotal))
                                    : failed_ ? I18n.strings["storage.noNetwork"]
                                    : tool.found ? I18n.strings["storage.present"]
                                    : I18n.strings["storage.absentFfmpeg"]
                            stateColor: tool.found && !Deps.busy ? Theme.okFg
                                        : failed_ ? Theme.errorFg
                                        : Deps.busy ? Theme.text : Theme.textMuted

                            ConfirmButton {
                                Layout.preferredWidth: screen.actionWidth
                                visible: Storage.ffmpeg.ours === true && !Deps.busy
                                enabled: !Storage.locked
                                text: I18n.strings["storage.remove"]
                                confirmText: I18n.strings["storage.confirm"]
                                onConfirmed: Storage.removeFfmpeg()
                            }
                            AppButton {
                                Layout.preferredWidth: screen.actionWidth
                                visible: !Storage.ffmpeg.found && !Deps.busy
                                primary: true
                                text: Deps.error.code !== undefined ? I18n.strings["storage.retry"]
                                                                    : I18n.strings["storage.download"]
                                onClicked: Deps.getFfmpeg()
                            }
                            AppButton {
                                Layout.preferredWidth: screen.actionWidth
                                visible: Deps.busy
                                text: I18n.strings["storage.cancel"]
                                onClicked: Deps.cancel()
                            }
                        }

                        // --- модели --------------------------------------------
                        Repeater {
                            model: Storage.models

                            delegate: TableRow {
                                required property var modelData
                                readonly property string mode: screen.modelState(modelData)
                                readonly property string blurb:
                                    I18n.strings["model.blurb." + modelData.id] || ""

                                title: I18n.strings["storage.model"].arg(modelData.id)
                                detail: mode === "downloading"
                                        ? I18n.strings["storage.progress"]
                                              .arg(Fmt.fileSize(Storage.bytesDone))
                                              .arg(Fmt.fileSize(Storage.bytesTotal))
                                          + (Storage.speed > 0
                                             ? " · " + Fmt.fileSize(Storage.speed)
                                               + I18n.strings["unit.perSec"] : "")
                                        : mode === "failed"
                                        ? (Storage.error.reason === "network"
                                           ? I18n.strings["storage.failedNetwork"]
                                           : I18n.strings["storage.failedOther"])
                                              .arg(Fmt.fileSize(Storage.error.bytes || 0))
                                        : mode === "partial"
                                        ? I18n.strings["storage.partialDetail"]
                                              .arg(Fmt.fileSize(modelData.bytes))
                                        : mode === "ready" && modelData.date
                                        ? blurb + " · " + I18n.strings["storage.modelDate"]
                                                          .arg(Fmt.day(modelData.date))
                                        : blurb
                                size: Fmt.fileSize(mode === "ready" ? modelData.bytes
                                                                    : modelData.sizeMb * 1024 * 1024)
                                ok: mode === "ready"
                                failed: mode === "failed"
                                busy: mode === "downloading"
                                progress: Storage.bytesTotal > 0
                                          ? Storage.bytesDone / Storage.bytesTotal : 0
                                state_: mode === "ready" ? I18n.strings["storage.present"]
                                        : mode === "downloading"
                                        ? I18n.strings["storage.downloading"]
                                              .arg(screen.percent(Storage.bytesDone, Storage.bytesTotal))
                                        : mode === "failed"
                                        ? (Storage.error.reason === "network"
                                           ? I18n.strings["storage.noNetwork"]
                                           : I18n.strings["storage.error"])
                                        : mode === "partial" ? I18n.strings["storage.paused"]
                                        : I18n.strings["storage.absent"]
                                stateColor: mode === "ready" ? Theme.okFg
                                            : mode === "failed" ? Theme.errorFg
                                            : mode === "partial" ? Theme.warnFg
                                            : mode === "downloading" ? Theme.text
                                            : Theme.textMuted

                                // ready: удалить
                                ConfirmButton {
                                    Layout.preferredWidth: screen.actionWidth
                                    visible: mode === "ready"
                                    enabled: !Storage.locked
                                    text: I18n.strings["storage.remove"]
                                    confirmText: I18n.strings["storage.confirm"]
                                    onConfirmed: Storage.removeModel(modelData.id)
                                }
                                // нет на диске: скачать. Главной кнопкой — только
                                // ту модель, что выбрана для работы: семь оранжевых
                                // кнопок подряд спорили бы за внимание (правило 1).
                                AppButton {
                                    Layout.preferredWidth: screen.actionWidth
                                    visible: mode === "absent"
                                    enabled: Storage.downloading === ""
                                    primary: modelData.id === Task.model
                                    text: I18n.strings["storage.download"]
                                    onClicked: Storage.downloadModel(modelData.id)
                                }
                                // качается: приостановить или отменить совсем
                                AppButton {
                                    Layout.preferredWidth: screen.actionWidth
                                    visible: mode === "downloading"
                                    text: I18n.strings["storage.cancel"]
                                    onClicked: Storage.cancel()
                                }
                                AppButton {
                                    Layout.preferredWidth: screen.actionWidth
                                    visible: mode === "downloading"
                                    text: I18n.strings["storage.pause"]
                                    onClicked: Storage.pause()
                                }
                                // оборвалась или приостановлена: продолжить с места
                                // или убрать скачанную часть
                                ConfirmButton {
                                    Layout.preferredWidth: screen.actionWidth
                                    visible: mode === "failed" || mode === "partial"
                                    enabled: !Storage.locked
                                    text: I18n.strings["storage.drop"]
                                    confirmText: I18n.strings["storage.confirm"]
                                    onConfirmed: Storage.removeModel(modelData.id)
                                }
                                AppButton {
                                    Layout.preferredWidth: screen.actionWidth
                                    visible: mode === "failed" || mode === "partial"
                                    enabled: Storage.downloading === ""
                                    primary: true
                                    text: mode === "failed" ? I18n.strings["storage.retry"]
                                                            : I18n.strings["storage.resume"]
                                    onClicked: Storage.downloadModel(modelData.id)
                                }
                            }
                        }
                    }
                }

                // --- временные файлы ----------------------------------------
                Panel {
                    Layout.fillWidth: true
                    visible: Storage.tempCount > 0
                    Layout.preferredHeight: tempColumn.implicitHeight + Theme.padPanel * 2

                    RowLayout {
                        id: tempColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.padPanel
                        spacing: Theme.gapButtons

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            SectionTitle { text: I18n.strings["storage.temp"] }
                            Text {
                                Layout.fillWidth: true
                                text: I18n.strings["storage.tempDetail"]
                                      .arg(Fmt.plural(Storage.tempCount, I18n.strings["storage.files"]))
                                      .arg(Fmt.fileSize(Storage.tempBytes))
                                color: Theme.textBody
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                wrapMode: Text.WordWrap
                            }
                        }
                        AppButton {
                            enabled: !Storage.locked
                            text: I18n.strings["storage.clearTemp"]
                            onClicked: Storage.clearTemp()
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: I18n.strings["storage.footnote"]
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    wrapMode: Text.WordWrap
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
                // Пустые временные не упоминаем: «0 КБ» — шум, а не сведения
                text: [I18n.strings["storage.statusDownloaded"].arg(Fmt.fileSize(Storage.downloadedBytes))]
                      .concat(Storage.tempCount > 0
                              ? [I18n.strings["storage.statusTemp"].arg(Fmt.fileSize(Storage.tempBytes))] : [])
                      .concat([I18n.strings["storage.free"].arg(Fmt.fileSize(Storage.freeBytes))])
                      .join(" · ")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }
    }
}
