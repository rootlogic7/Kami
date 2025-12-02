import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    visible: true
    width: 1200
    height: 800
    title: "Kami - Hybrid Workstation"
    color: "#1e1e2e" // Catppuccin Base

    // Define a signal so Python can update the status text
    signal statusUpdated(string msg)

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 20

        Text {
            text: "Kami Hybrid Architecture"
            color: "#cdd6f4" // Catppuccin Text
            font.pixelSize: 32
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            id: statusLabel
            text: "Ready to generate."
            color: "#a6adc8" // Catppuccin Subtext
            font.pixelSize: 18
            Layout.alignment: Qt.AlignHCenter
        }

        Button {
            text: "Test Generation (Backend)"
            font.pixelSize: 16
            Layout.preferredWidth: 250
            Layout.preferredHeight: 50
            Layout.alignment: Qt.AlignHCenter

            contentItem: Text {
                text: parent.text
                font: parent.font
                color: "#1e1e2e"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            background: Rectangle {
                color: parent.down ? "#94e2d5" : "#89b4fa" // Teal/Blue
                radius: 8
            }

            onClicked: {
                statusLabel.text = "Request sent to backend..."
                // Calling the Python function exposed as 'backend'
                backend.generate_test("A futuristic city with glowing neon lights")
            }
        }
        
        Text {
            text: "Remote Access: http://localhost:8000"
            color: "#585b70" 
            font.pixelSize: 14
            Layout.alignment: Qt.AlignHCenter
        }
    }
    
    // Connection to handle signals from Python
    Connections {
        target: backend
        
        function onGenerationFinished(path) {
            statusLabel.text = "Success! Image saved to: " + path
            console.log("Image generated at: " + path)
        }
        
        function onErrorOccurred(msg) {
            statusLabel.text = "Error: " + msg
        }
    }
}
