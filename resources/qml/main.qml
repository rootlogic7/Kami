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
            Layout.preferredWidth: 260
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
                    font.pixelSize: 32
                    font.bold: true
                    font.family: Theme.FONT_FAMILY
                    Layout.alignment: Qt.AlignHCenter
                    Layout.bottomMargin: 30
                }

                // --- Navigation Menu ---
                
                NavButton { 
                    text: "Home"
                    iconText: "🏠" 
                    isActive: root.currentViewIndex === 0
                    onClicked: root.currentViewIndex = 0
                }
                
                NavButton { 
                    text: "Generate" 
                    iconText: "✨"
                    isActive: root.currentViewIndex === 1
                    onClicked: root.currentViewIndex = 1
                }

                NavButton { 
                    text: "Collection" 
                    iconText: "📚" // Changed from folder to books/library style
                    isActive: root.currentViewIndex === 2
                    onClicked: root.currentViewIndex = 2
                }

                NavButton { 
                    text: "Settings" 
                    iconText: "⚙️"
                    isActive: root.currentViewIndex === 3
                    onClicked: root.currentViewIndex = 3
                }

                Item { Layout.fillHeight: true } // Spacer

                // Status Footer
                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.SURFACE0
                }
                
                RowLayout {
                    Layout.topMargin: 10
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 10
                    
                    Text {
                        text: "🟢 System Ready"
                        color: Theme.GREEN
                        font.pixelSize: 12
                    }
                }
            }
        }

        // 2. Content Area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.BASE
            
            // Defines the view container
            StackLayout {
                id: contentStack
                anchors.fill: parent
                anchors.margins: 20
                currentIndex: root.currentViewIndex

                // Index 0: Home
                HomeView { id: viewHome }

                // Index 1: Generate (Reuse our existing GenerationView)
                GenerationView { id: viewGen }

                // Index 2: Collection
                CollectionView { 
                    id: viewCollection 
                    
                    onRestoreParameters: (prompt, neg, steps, cfg, seed, model, lora, loraScale) => {
                        console.log("Restoring params for: " + prompt)
                        // 1. Switch to Generate View
                        root.currentViewIndex = 1
                        // 2. Set Params
                        viewGen.setParameters(prompt, neg, steps, cfg, seed, model, lora, loraScale)
                    }
                }
                // Index 3: Settings
                SettingsView { id: viewSettings }
            }
        }
    }

    // --- Inline Component: NavButton ---
    component NavButton: Button {
        id: btn
        property bool isActive: false
        property string iconText: ""
        
        Layout.fillWidth: true
        height: 54
        
        background: Rectangle {
            color: btn.isActive ? Theme.SURFACE0 : (btn.hovered ? Theme.CRUST : "transparent")
            radius: Theme.BORDER_RADIUS
            border.width: btn.isActive ? 1 : 0
            border.color: Theme.MAUVE
            
            // Active Indicator (Left Bar)
            Rectangle {
                visible: btn.isActive
                width: 4
                height: 24
                color: Theme.MAUVE
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 12
                radius: 2
            }
        }

        contentItem: RowLayout {
            spacing: 15
            Text {
                text: btn.iconText
                font.pixelSize: 20
                Layout.leftMargin: 24
                color: btn.isActive ? Theme.TEXT : Theme.SUBTEXT1
            }
            Text {
                text: btn.text
                color: btn.isActive ? Theme.TEXT : Theme.SUBTEXT0
                font.pixelSize: 16
                font.bold: btn.isActive
                font.family: Theme.FONT_FAMILY
                Layout.fillWidth: true
            }
        }
        
        leftPadding: 0; rightPadding: 0
        
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: btn.clicked()
        }
    }
}
