import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme

Item {
    id: root
    
    // --- Internal State ---
    property string lastImagePath: ""
    
    // --- Signal Connections ---
    Connections {
        target: backend
        function onGenerationFinished(path) {
            console.log("View received image: " + path)
            root.lastImagePath = "file://" + path // QML needs file:// prefix
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 20

        // --- LEFT COLUMN: Parameters ---
        Rectangle {
            Layout.preferredWidth: 400
            Layout.fillHeight: true
            color: "transparent" // Use parent background
            
            ScrollView {
                anchors.fill: parent
                contentWidth: parent.width
                
                ColumnLayout {
                    width: parent.width
                    spacing: 15
                    
                    Text { text: "Prompt"; color: Theme.TEXT; font.bold: true }
                    TextArea {
                        id: txtPrompt
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        placeholderText: "A majestic lion in the sunset..."
                        wrapMode: TextEdit.Wrap
                        background: Rectangle {
                            color: Theme.MANTLE
                            border.color: Theme.SURFACE0
                            radius: Theme.BORDER_RADIUS
                        }
                        color: Theme.TEXT
                        font.pixelSize: 14
                    }
                    
                    Text { text: "Negative Prompt"; color: Theme.TEXT; font.bold: true }
                    TextArea {
                        id: txtNeg
                        Layout.fillWidth: true
                        Layout.preferredHeight: 60
                        placeholderText: "ugly, blurry, low quality..."
                        wrapMode: TextEdit.Wrap
                        background: Rectangle {
                            color: Theme.MANTLE
                            border.color: Theme.SURFACE0
                            radius: Theme.BORDER_RADIUS
                        }
                        color: Theme.TEXT
                        font.pixelSize: 14
                    }
                    
                    // Spacer
                    Item { height: 10 }
                    
                    // Steps Slider
                    RowLayout {
                        Text { text: "Steps: " + sliderSteps.value; color: Theme.TEXT }
                        Layout.fillWidth: true
                    }
                    Slider {
                        id: sliderSteps
                        from: 1; to: 50; stepSize: 1
                        value: 30
                        Layout.fillWidth: true
                    }
                    
                    // CFG Slider
                    RowLayout {
                        Text { text: "CFG Scale: " + sliderCfg.value.toFixed(1); color: Theme.TEXT }
                        Layout.fillWidth: true
                    }
                    Slider {
                        id: sliderCfg
                        from: 1.0; to: 20.0; stepSize: 0.5
                        value: 7.0
                        Layout.fillWidth: true
                    }
                    
                    // Seed
                    Text { text: "Seed (Empty = Random)"; color: Theme.TEXT }
                    TextField {
                        id: txtSeed
                        Layout.fillWidth: true
                        placeholderText: "123456789"
                        background: Rectangle {
                            color: Theme.MANTLE
                            border.color: Theme.SURFACE0
                            radius: Theme.BORDER_RADIUS
                        }
                        color: Theme.TEXT
                    }
                    
                    // Refiner Checkbox
                    CheckBox {
                        id: chkRefiner
                        text: "Enable Refiner"
                        
                        contentItem: Text {
                            text: parent.text
                            font: parent.font
                            color: Theme.TEXT
                            leftPadding: parent.indicator.width + parent.spacing
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    
                    Item { Layout.fillHeight: true } // Spacer pushes button down
                    
                    Button {
                        text: "GENERATE"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 50
                        
                        background: Rectangle {
                            color: parent.down ? Theme.TEAL : Theme.BLUE
                            radius: Theme.BORDER_RADIUS
                        }
                        contentItem: Text {
                            text: parent.text
                            font.bold: true
                            font.pixelSize: 16
                            color: Theme.BASE
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        
                        onClicked: {
                            backend.generate(
                                txtPrompt.text,
                                txtNeg.text,
                                sliderSteps.value,
                                sliderCfg.value,
                                txtSeed.text,
                                chkRefiner.checked
                            )
                        }
                    }
                }
            }
        }

        // --- RIGHT COLUMN: Preview ---
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.MANTLE
            radius: Theme.BORDER_RADIUS
            border.color: Theme.SURFACE0
            border.width: 2
            
            Image {
                id: previewImage
                anchors.fill: parent
                anchors.margins: 10
                fillMode: Image.PreserveAspectFit
                source: root.lastImagePath
                asynchronous: true
                cache: false // Ensure reload if path is same but file changed
                
                // Placeholder if no image
                Text {
                    anchors.centerIn: parent
                    text: "No Image Generated"
                    color: Theme.SUBTEXT0
                    visible: parent.status !== Image.Ready
                }
            }
            
            // Loading Indicator (Simple overlay)
            Rectangle {
                anchors.centerIn: parent
                width: 150; height: 50
                color: Theme.BASE
                radius: 10
                visible: false // To be connected to backend status later
                border.color: Theme.BLUE
                
                Text {
                    anchors.centerIn: parent
                    text: "Generating..."
                    color: Theme.TEXT
                }
            }
        }
    }
}
