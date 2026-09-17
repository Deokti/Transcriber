import QtQuick
import QtQuick.Layouts
import Transcriber
import "../components"

// Результат: что получилось, чем это подтверждается и где оно лежит.
//
// Главное здесь — числа, а не восклицания: «1907 сегментов, 6983 слова,
// в 14 раз быстрее записи» человеку полезнее, чем «успешно завершено».
// Вердикт проверки на повторы стоит рядом с файлом, а не в общей ленте:
// это итог работы, а не замечание по ходу.
Item {
    id: screen

    signal again()

    readonly property var results: Run.results
    readonly property var summary: Run.summary

    readonly property bool anyBroken: (summary.failed || 0) > 0
    readonly property bool anyStopped: (summary.cancelled || 0) > 0
    readonly property bool anyWarned: results.some(function (r) {
        return r.verdict === "QUALITY_STUCK" || r.verdict === "QUALITY_MINOR" || r.partial
    })

    function title() {
        if (anyBroken && !(summary.done || 0))
            return I18n.strings["result.failed"]
        if (anyStopped)
            return I18n.strings["result.stopped"]
        if (anyBroken || anyWarned)
            return I18n.strings["result.warned"]
        return I18n.strings["result.done"]
    }

    // Строка под заголовком: сколько сделано и сколько это заняло.
    function counts() {
        const parts = [I18n.strings["run.doneCount"].arg(summary.done || 0)]
        if (summary.failed)
            parts.push(I18n.strings["run.failedCount"].arg(summary.failed))
        if (summary.cancelled)
            parts.push(I18n.strings["run.cancelledCount"].arg(summary.cancelled))
        if (summary.skipped)
            parts.push(I18n.strings["run.skippedCount"].arg(summary.skipped))
        if (summary.seconds)
            parts.push(Fmt.roughDuration(summary.seconds))
        return parts.join(" · ")
    }

    // Что показать про файл: вердикт проверки, спасённое после обрыва или
    // причину, по которой не вышло.
    function verdictText(item) {
        if (item.state === "failed")
            return Fmt.tr("error." + item.code, item.code)
        if (item.state === "cancelled")
            return I18n.strings["result.cancelled"]
        if (item.skipped)
            return I18n.strings["result.skipped"]
        if (item.audioFile !== undefined && item.verdict === undefined)
            return I18n.strings["result.audioSaved"]
        if (item.verdict === "QUALITY_STUCK")
            return I18n.strings["verdict.stuck"].arg(item.places || 0)
        if (item.verdict === "QUALITY_MINOR")
            return I18n.strings["verdict.minor"]
        if (item.verdict === "QUALITY_CLEAN")
            return I18n.strings["verdict.clean"]
        return ""
    }

    function verdictColor(item) {
        if (item.state === "failed")
            return Theme.errorFg
        if (item.state === "cancelled" || item.verdict === "QUALITY_STUCK" || item.partial)
            return Theme.warnFg
        return Theme.okFg
    }

    // Числа под именем файла — разные у текста и у звука.
    function numbers(item) {
        const parts = []
        if (item.duration)
            parts.push(Fmt.duration(item.duration))
        if (item.audioFile !== undefined) {
            parts.push(Fmt.tr("audio." + item.audioFile.format, item.audioFile.format))
            parts.push(Fmt.fileSize(item.audioFile.size))
        }
        if (item.segments)
            parts.push(I18n.strings["result.segments"].arg(item.segments))
        if (item.words)
            parts.push(I18n.strings["result.words"].arg(item.words))
        if (item.speed)
            parts.push("×" + Number(item.speed).toFixed(1))
        if (item.spent)
            parts.push(I18n.strings["result.spent"].arg(Fmt.roughDuration(item.spent)))
        return parts.join(" · ")
    }

    function document(item) {
        const made = item.artifacts || {}
        for (const key of ["docx", "txt", "md", "srt"])
            if (made[key] !== undefined)
                return made[key]
        return ""
    }

    function sound(item) {
        return item.audioFile !== undefined ? item.audioFile.path : ""
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
                    text: I18n.strings["result.title"]
                    font.pixelSize: Theme.fontMessage
                }

                Item { Layout.fillWidth: true }

                // Экраны «Хранилище» и «Диагностика» ещё не написаны — кнопки
                // вернутся вместе с ними (M4). Кнопка, ведущая в никуда,
                // хуже её отсутствия.
                // AppButton { text: I18n.strings["nav.storage"]; flat_: true }
                // AppButton { text: I18n.strings["nav.diagnostics"]; flat_: true }
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
                Layout.preferredHeight: head.implicitHeight + Theme.padPanel * 2

                ColumnLayout {
                    id: head
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.padPanel
                    spacing: Theme.gapLabel

                    Text {
                        text: screen.title()
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontTitle
                        font.weight: Theme.weightSemiBold
                    }
                    Text {
                        text: screen.counts()
                        color: Theme.textMuted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                    }
                }
            }

            // --- по карточке на файл -------------------------------------
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: Theme.gapPanels
                model: screen.results
                boundsBehavior: Flickable.StopAtBounds

                delegate: Panel {
                    width: ListView.view.width
                    height: card.implicitHeight + Theme.padPanel * 2

                    ColumnLayout {
                        id: card
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.padPanel
                        spacing: Theme.gapLabel

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.gapButtons

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                elide: Text.ElideMiddle
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontStrong
                                font.weight: Theme.weightSemiBold
                            }
                            Text {
                                text: screen.verdictText(modelData)
                                color: screen.verdictColor(modelData)
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: text !== ""
                            text: screen.numbers(modelData)
                            wrapMode: Text.WordWrap
                            color: Theme.textMuted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                        }

                        // Что именно сломалось. Без этой строки на карточке
                        // остаётся один код, и человеку нечего рассказать о том,
                        // что случилось: текст ошибки знает только ядро.
                        Text {
                            Layout.fillWidth: true
                            visible: text !== ""
                            text: modelData.state === "failed" && modelData.reason !== undefined
                                  ? String(modelData.reason) : ""
                            wrapMode: Text.WrapAnywhere
                            maximumLineCount: 3
                            elide: Text.ElideRight
                            color: Theme.errorFg
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                        }

                        // Сохранённое после обрыва — не то же самое, что готовое,
                        // и человек должен узнать об этом здесь, а не в журнале.
                        Text {
                            Layout.fillWidth: true
                            visible: modelData.partial === true
                            text: I18n.strings["result.partial"]
                            wrapMode: Text.WordWrap
                            color: Theme.warnFg
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.topMargin: Theme.gapLabel
                            spacing: Theme.gapButtons
                            visible: screen.document(modelData) !== ""
                                     || screen.sound(modelData) !== ""

                            AppButton {
                                visible: screen.document(modelData) !== ""
                                text: I18n.strings["result.openDocument"]
                                Layout.preferredHeight: Theme.hRowButton
                                onClicked: Shell.open(screen.document(modelData))
                            }
                            AppButton {
                                visible: screen.sound(modelData) !== ""
                                text: I18n.strings["result.openSound"]
                                Layout.preferredHeight: Theme.hRowButton
                                onClicked: Shell.open(screen.sound(modelData))
                            }
                            AppButton {
                                text: I18n.strings["result.showFolder"]
                                flat_: true
                                Layout.preferredHeight: Theme.hRowButton
                                onClicked: Shell.reveal(screen.document(modelData)
                                                        || screen.sound(modelData))
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }
        }

        // --- подвал ------------------------------------------------------
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
                    text: screen.results.length > 0
                        ? I18n.strings["result.where"].arg(
                              Fmt.folderOf(screen.document(screen.results[0])
                                           || screen.sound(screen.results[0])))
                        : ""
                    elide: Text.ElideMiddle
                    color: Theme.textMuted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                }

                AppButton {
                    text: I18n.strings["result.again"]
                    primary: true
                    onClicked: screen.again()
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
                // Модель в строке состояния уместна, только если она работала
                text: (Task.needsText
                       ? [Task.model, Fmt.deviceText({"id": Task.device})]
                       : [Fmt.tr("audio." + Task.audioFormat, Task.audioFormat)]).join(" · ")
                color: Theme.textMuted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }
    }
}
