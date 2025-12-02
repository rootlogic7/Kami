import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "Theme.js" as Theme

ApplicationWindow {
    id: root
    visible: true
    width: 1400
    height: 900
    title: "Kami - Local SDXL Station"
    color: Theme.BASE

    // --- Properties ---
    property int currentViewIndex: 0

    // --- Main Layout (Sidebar + Content) ---
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Sidebar Navigation
        Rectangle {
            Layout.preferredWidth: 250
            Layout.fillHeight: true
            color: Theme.MANTLE
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 15

                // Header / Logo
                Text {
                    text: "KAMI"
                    color: Theme.LAVENDER
                    font.pixelSize: 28
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                    Layout.bottomMargin: 20
                }

                // Nav Buttons (Icon property renamed to iconText)
                NavButton { 
                    text: "Generate"
                    iconText: "✨" 
                    isActive: root.currentViewIndex === 0
                    onClicked: root.currentViewIndex = 0
                }
                
                NavButton { 
                    text: "Settings" 
                    iconText: "⚙️"
                    isActive: root.currentViewIndex === 1
                    onClicked: root.currentViewIndex = 1
                }

                NavButton { 
                    text: "Gallery" 
                    iconText: "📂"
                    isActive: root.currentViewIndex === 2
                    onClicked: root.currentViewIndex = 2
                }

                Item { Layout.fillHeight: true } // Spacer

                // Status Indicator
                Text {
                    text: "System Ready"
                    color: Theme.GREEN
                    font.pixelSize: 12
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // 2. Content Area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.BASE
            
            StackLayout {
                id: contentStack
                anchors.fill: parent
                anchors.margins: 20
                currentIndex: root.currentViewIndex

		// View 0: Generator (Real View)
                GenerationView {
                    id: genView
                }

                // View 1: Settings (Placeholder)
                Rectangle {
                    color: "transparent"
                    Text { 
                        text: "System Configuration" 
                        color: Theme.TEXT
                        anchors.centerIn: parent
                        font.pixelSize: 24
                    }
                }

                // View 2: Gallery (Placeholder)
                Rectangle {
                    color: "transparent"
                    Text { 
                        text: "Image Gallery" 
                        color: Theme.TEXT
                        anchors.centerIn: parent
                        font.pixelSize: 24
                    }
                }
            }
        }
    }

    // --- Inline Component: NavButton ---
    component NavButton: Button {
        id: btn
        property bool isActive: false
        property string iconText: ""  // RENAMED from 'icon' to 'iconText'
        
        Layout.fillWidth: true
        height: 50
        
        background: Rectangle {
            color: btn.isActive ? Theme.SURFACE0 : (btn.hovered ? Theme.CRUST : "transparent")
            radius: Theme.BORDER_RADIUS
            border.width: btn.isActive ? 1 : 0
            border.color: Theme.MAUVE
            
            // Left active indicator
            Rectangle {
                visible: btn.isActive
                width: 4
                height: 20
                color: Theme.MAUVE
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 8
                radius: 2
            }
        }

        contentItem: RowLayout {
            spacing: 15
            Text {
                text: btn.iconText // Use new property name
                font.pixelSize: 18
                Layout.leftMargin: 20
            }
            Text {
                text: btn.text
                color: btn.isActive ? Theme.MAUVE : Theme.SUBTEXT0
                font.pixelSize: 16
                font.bold: btn.isActive
                Layout.fillWidth: true
            }
        }
        
        // Remove default padding
        leftPadding: 0; rightPadding: 0
        
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: btn.clicked()
        }
    }
}
