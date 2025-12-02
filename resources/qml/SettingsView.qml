import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme

Item {
    id: root

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 20

        Text {
            text: "Global Settings"
            color: Theme.BLUE
            font.pixelSize: 32
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: "Configure output paths, default parameters, and system preferences."
            color: Theme.TEXT
            font.pixelSize: 16
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
