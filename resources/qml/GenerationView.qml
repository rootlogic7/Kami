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
            root.lastImagePath = "file://" + path 
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 20

        // --- LEFT COLUMN: Parameters ---
        Rectangle {
            Layout.preferredWidth: 400
            Layout.fillHeight: true
            color: "transparent"
            
            ScrollView {
                anchors.fill: parent
                contentWidth: parent.width
                clip: true
                
                ColumnLayout {
                    width: parent.width
                    spacing: 15
                    
                    // --- Model Selection Section ---
                    Text { text: "Base Model"; color: Theme.TEXT; font.bold: true }
                    ComboBox {
                        id: comboModel
                        Layout.fillWidth: true
                        model: [] // Populated dynamically
                        
                        background: Rectangle {
                            color: Theme.MANTLE
                            border.color: Theme.SURFACE0
                            radius: Theme.BORDER_RADIUS
                        }
                        contentItem: Text {
                            leftPadding: 10
                            text: comboModel.currentText
                            color: Theme.TEXT
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        
                        Component.onCompleted: {
                            comboModel.model = backend.get_models()
                            comboModel.currentIndex = 0
                        }
                    }

                    Text { text: "LoRA Network"; color: Theme.TEXT; font.bold: true }
                    ComboBox {
                        id: comboLora
                        Layout.fillWidth: true
                        model: [] // Populated dynamically
                        
                        background: Rectangle {
                            color: Theme.MANTLE
                            border.color: Theme.SURFACE0
                            radius: Theme.BORDER_RADIUS
                        }
                        contentItem: Text {
                            leftPadding: 10
                            text: comboLora.currentText
                            color: Theme.TEXT
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        
                        Component.onCompleted: {
                            comboLora.model = backend.get_loras()
                            comboLora.currentIndex = 0
                        }
                    }
                    
                    // LoRA Scale Slider (Only visible if LoRA is selected)
                    ColumnLayout {
                        visible: comboLora.currentText !== "None"
                        Layout.fillWidth: true
                        spacing: 5
                        
                        RowLayout {
                            Text { text: "LoRA Strength: " + sliderLoraScale.value.toFixed(1); color: Theme.TEXT }
                            Layout.fillWidth: true
                        }
                        Slider {
                            id: sliderLoraScale
                            from: 0.0; to: 2.0; stepSize: 0.1
                            value: 0.8
                            Layout.fillWidth: true
                        }
                    }

                    // --- Prompt Section ---
                    Item { height: 10 } // Spacer
                    
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
                    
                    // --- Settings Section ---
                    Item { height: 10 } 
                    
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
                    
                    CheckBox {
                        id: chkRefiner
                        text: "Enable Refiner Pipeline"
                        contentItem: Text {
                            text: parent.text
                            font: parent.font
                            color: Theme.TEXT
                            leftPadding: parent.indicator.width + parent.spacing
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    
                    Item { Layout.fillHeight: true } // Spacer
                    
                    Button {
                        text: "GENERATE"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 50
                        Layout.bottomMargin: 20
                        
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
                            // Call updated backend method with all 9 arguments
                            backend.generate(
                                txtPrompt.text,
                                txtNeg.text,
                                sliderSteps.value,
                                sliderCfg.value,
                                txtSeed.text,
                                chkRefiner.checked,
                                comboModel.currentText,
                                comboLora.currentText,
                                sliderLoraScale.value
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
                cache: false 
                
                Text {
                    anchors.centerIn: parent
                    text: "No Image Generated"
                    color: Theme.SUBTEXT0
                    visible: parent.status !== Image.Ready
                }
            }
        }
    }
}
