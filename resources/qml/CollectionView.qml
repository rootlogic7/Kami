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
            text: "Collection"
            color: Theme.MAUVE
            font.pixelSize: 32
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: "Manage your gallery, styles, and prompt templates here."
            color: Theme.TEXT
            font.pixelSize: 16
            Layout.alignment: Qt.AlignHCenter
        }
        
        // Placeholder for Tabs (Gallery | Styles | Prompts)
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 10
            
            Repeater {
                model: ["Gallery", "Styles", "Prompts"]
                delegate: Rectangle {
                    width: 120; height: 40
                    color: Theme.SURFACE0
                    radius: Theme.BORDER_RADIUS
                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        color: Theme.TEXT
                    }
                }
            }
        }
    }
}
