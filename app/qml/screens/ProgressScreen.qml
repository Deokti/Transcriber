import QtQuick
import QtQuick.Layouts
import Transcriber
import "../components"

// Ход работы: три числа — что происходит, сколько процентов, сколько осталось.
// «Крутилка» без цифр на восьмидесяти минутах — издевательство, поэтому
// процент крупный, а рядом всегда стадия и оценка времени.
//
// Модальных окон здесь нет по требованию: человек ушёл пить чай, и спросить
// его не у кого. Всё, что можно было спросить, спросили до запуска.
Item {
    id: screen

    signal done()

    readonly property bool working: Run.running
    // Экран открыли, ничего не запуская: показывать нечего, и притворяться
    // тоже незачем — пустое состояние объясняет, что тут будет.
    readonly property bool never: Run.fileTotal === 0
    readonly property bool stopping: Run.state === "stopping"
    readonly property bool cancelling: Run.state === "cancelling"

    // Сколько ждём остановку. Отмена доходит до ядра сразу, но встать оно
    // может только в безопасном месте — между сегментами. Пока модель
    // грузится, безопасного места нет, и ждать приходится до минуты.
    // Молчащая кнопка в это время выглядит зависшей, поэтому считаем вслух.
    property int cancelSeconds: 0

    Timer {
        running: screen.cancelling
        repeat: true
        interval: 1000
        onRunningChanged: screen.cancelSeconds = 0
        onTriggered: screen.cancelSeconds++
    }

    // Показываем не всё подряд: замечания и ошибки, плюс несколько важных
    // сообщений об остановке. Поток «модель загружена, язык определён»
    // человеку во время работы не нужен.
    readonly property var loudCodes: ["STOP_REQUESTED", "STOP_UNDONE",
                                      "CANCEL_REQUESTED", "PARTIAL_SAVED"]

    function visibleNotices() {
        return Run.notices.filter(function (n) {
            return n.kind !== "info" || screen.loudCodes.indexOf(n.code) >= 0
        }).slice(-6).reverse()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // --- полоса инструментов ---------------------------------------
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

                SectionTitle {
                    text: I18n.strings["run.title"]
                    font.pixelSize: Theme.fontMessage
                }

                Item { Layout.fillWidth: true }

                AppButton { text: I18n.strings["nav.storage"]; flat_: true }
                AppButton { text: I18n.strings["nav.diagnostics"]; flat_: true }
            }
        }

        // --- рабочая область --------------------------------------------
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.padScreen
            spacing: Theme.gapPanels

            Panel {
                Layout.fillWidth: true
                // Панель — просто прямоугольник и своей высоты не знает:
                // содержимое прибито якорями, а якоря размер не задают.
                // Считаем высоту по содержимому сами.
                Layout.preferredHeight: head.implicitHeight + Theme.padPanel * 2

                ColumnLayout {
                    id: head
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.padPanel
                    spacing: Theme.padPanel

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.gapButtons

                        SectionTitle {
                            Layout.fillWidth: true
                            text: screen.never ? I18n.strings["run.never"]
                                : screen.working && Run.fileName !== ""
                                ? Run.fileName : I18n.strings["run.finished"]
                            font.pixelSize: Theme.fontSection
                            elide: Text.ElideMiddle
                        }
                        Text {
                            visible: screen.working
                            text: I18n.strings["run.fileOf"].arg(Run.fileNumber).arg(Run.fileTotal)
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: !screen.never
                        spacing: Theme.padPanel

                        // Число видно с другого конца комнаты — правило из брифа
                        Text {
                            // Доли пока нет — честнее прочерк, чем ноль или
                            // застывший процент прошлой стадии.
                            text: Run.hasPercent ? Math.round(Run.percent * 100) + "%" : "—"
                            color: Run.hasPercent ? Theme.text : Theme.textIdle
                            font.family: Theme.fontFamily
                            // Прочерк во всю высоту процента читается как
                            // случайная черта, поэтому он мельче.
                            font.pixelSize: Run.hasPercent ? Theme.fontHuge : Theme.fontTitle
                            font.weight: Theme.weightSemiBold
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: Theme.gapLabel

                            Text {
                                text: Run.stage !== ""
                                    ? Fmt.tr("stage." + Run.stage, Run.stage)
                                    : screen.summaryText()
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontMessage
                                font.weight: Theme.weightSemiBold
                            }
                            Text {
                                // Первые секунды оценки ещё нет — так и пишем,
                                // вместо бодрого «осталось 0 минут».
                                visible: screen.working
                                text: Run.stage === "download"
                                    ? I18n.strings["run.downloaded"]
                                          .arg(Fmt.fileSize(Run.bytesDone))
                                          .arg(Fmt.fileSize(Run.bytesTotal))
                                      + (Run.eta > 0 ? " · " + I18n.strings["run.eta"]
                                                           .arg(Fmt.roughDuration(Run.eta)) : "")
                                    : Run.loadingModel !== ""
                                    ? I18n.strings["run.loadingModel"].arg(Run.loadingModel)
                                    : Run.eta > 0
                                    ? I18n.strings["run.eta"].arg(Fmt.roughDuration(Run.eta))
                                    : I18n.strings["run.etaSoon"]
                                color: Theme.textMuted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                            }
                        }
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        visible: !screen.never
                        value: Run.percent
                        known: Run.hasPercent
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.gapPanels

                // --- стадии и очередь --------------------------------------
                ColumnLayout {
                    // Раскладка внутри раскладки растягивается по умолчанию —
                    // и выдавливает соседа за край окна. Ширину держим сами.
                    Layout.fillWidth: false
                    Layout.preferredWidth: 320
                    Layout.fillHeight: true
                    spacing: Theme.gapPanels

                    Panel {
                        Layout.fillWidth: true
                        visible: !screen.never
                        Layout.preferredHeight: stageList.implicitHeight + Theme.padPanel * 2

                        ColumnLayout {
                            id: stageList
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.padPanel
                            spacing: Theme.gapButtons

                            Repeater {
                                model: Run.stages
                                StageRow {
                                    Layout.fillWidth: true
                                    state_: modelData.state
                                    label: Fmt.tr("stage." + modelData.code, modelData.code)
                                }
                            }
                        }
                    }

                    // Вся очередь целиком: видно, что позади, что впереди и
                    // на чём споткнулись. Ошибка одного файла её не прерывает.
                    Panel {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        visible: !screen.never

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.padPanel
                            spacing: Theme.gapButtons

                            SectionTitle { text: I18n.strings["queue.title"] }

                            Repeater {
                                model: Run.files
                                StageRow {
                                    Layout.fillWidth: true
                                    state_: modelData.state
                                    label: modelData.name
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }
                }

                // --- что происходило --------------------------------------
                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.padPanel
                        spacing: Theme.gapButtons

                        SectionTitle { text: I18n.strings["run.notices"] }

                        Text {
                            Layout.fillWidth: true
                            visible: screen.visibleNotices().length === 0
                            text: I18n.strings["run.noticesEmpty"]
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            wrapMode: Text.WordWrap
                        }

                        Repeater {
                            model: screen.visibleNotices()

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.gapButtons

                                Rectangle {
                                    Layout.alignment: Qt.AlignTop
                                    Layout.topMargin: 5
                                    width: 6
                                    height: 6
                                    radius: 3
                                    color: modelData.kind === "failed" ? Theme.errorFg
                                         : modelData.kind === "warning" ? Theme.warnFg
                                         : Theme.textIdle
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: Fmt.noticeText(modelData)
                                    wrapMode: Text.WordWrap
                                    color: modelData.kind === "failed" ? Theme.errorText
                                         : modelData.kind === "warning" ? Theme.warnText
                                         : Theme.textBody
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }

        // --- подвал: две остановки --------------------------------------
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
                    text: screen.cancelling
                            ? (Run.loadingModel !== ""
                                ? I18n.strings["run.cancellingLoad"]
                                : I18n.strings["run.cancellingFor"])
                              .arg(Fmt.roughDuration(screen.cancelSeconds))
                        : screen.stopping ? I18n.strings["run.stopping"]
                        : !screen.working ? screen.summaryText()
                        : I18n.strings["run.queueLeft"].arg(
                              Math.max(0, Run.fileTotal - Run.fileNumber))
                    elide: Text.ElideRight
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                }

                // Мягкая остановка: доработать текущий файл и встать.
                // Пока она не случилась, её можно передумать.
                AppButton {
                    visible: screen.working
                    enabled: !screen.cancelling
                    text: screen.stopping ? I18n.strings["run.continue"]
                                          : I18n.strings["run.stopAfter"]
                    onClicked: screen.stopping ? Run.undoStop() : Run.stopAfterCurrent()
                }

                // Жёсткая: бросить сейчас. Посчитанное сохранит ядро (D-7).
                AppButton {
                    visible: screen.working
                    enabled: !screen.cancelling
                    text: I18n.strings["run.cancelAll"]
                    onClicked: Run.cancelAll()
                }

                AppButton {
                    visible: !screen.working
                    text: I18n.strings["run.toMain"]
                    primary: true
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
                text: [Task.model, Fmt.deviceText({"id": Task.device})].join(" · ")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }
    }

    function summaryText() {
        const s = Run.summary
        if (!s || s.total === undefined)
            return ""
        let parts = [I18n.strings["run.doneCount"].arg(s.done)]
        if (s.failed)
            parts.push(I18n.strings["run.failedCount"].arg(s.failed))
        if (s.cancelled)
            parts.push(I18n.strings["run.cancelledCount"].arg(s.cancelled))
        if (s.skipped)
            parts.push(I18n.strings["run.skippedCount"].arg(s.skipped))
        return parts.join(" · ")
    }
}
