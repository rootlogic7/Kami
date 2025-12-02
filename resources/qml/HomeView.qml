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
            text: "Welcome back, Traveler."
            color: Theme.LAVENDER
            font.pixelSize: 32
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: "What would you like to create today?"
            color: Theme.SUBTEXT0
            font.pixelSize: 18
            Layout.alignment: Qt.AlignHCenter
        }

        // Placeholder for IOTD (Image of the Day)
        Rectangle {
            Layout.preferredWidth: 400
            Layout.preferredHeight: 250
            Layout.alignment: Qt.AlignHCenter
            color: Theme.CRUST
            radius: Theme.BORDER_RADIUS
            border.color: Theme.SURFACE0
            border.width: 2

            Text {
                anchors.centerIn: parent
                text: "🎲 Image of the Day\n(Coming Soon)"
                color: Theme.OVERLAY0
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}
