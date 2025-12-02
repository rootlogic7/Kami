import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme

Item {
    id: root

    // --- Data Loading ---
    function loadSettings() {
        var cfg = backend.get_config()
        
        // Update UI elements without triggering onValueChanged loops immediately
        sliderDefaultSteps.value = cfg.steps
        sliderDefaultCfg.value = cfg.guidance
        txtDefaultNeg.text = cfg.neg_prompt
        switchPony.checked = cfg.pony_mode
        switchFreeU.checked = cfg.use_freeu
        
        console.log("Settings loaded.")
    }

    Component.onCompleted: loadSettings()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 40
        spacing: 20

        // Header
        Text {
            text: "Global Settings"
            color: Theme.BLUE
            font.pixelSize: 32
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }
        
        Rectangle {
            Layout.fillWidth: true; height: 1; color: Theme.SURFACE0
            Layout.bottomMargin: 20
        }

        // --- Settings Form ---
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            
            ColumnLayout {
                width: Math.min(600, parent.width)
                Layout.alignment: Qt.AlignHCenter
                spacing: 25

                // 1. Defaults Section
                Text { text: "Default Generation Parameters"; color: Theme.LAVENDER; font.bold: true; font.pixelSize: 18 }
                
                // Steps
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    RowLayout {
                        Text { text: "Default Steps"; color: Theme.TEXT; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text { text: sliderDefaultSteps.value; color: Theme.SUBTEXT0 }
                    }
                    Slider {
                        id: sliderDefaultSteps
                        from: 1; to: 100; stepSize: 1
                        Layout.fillWidth: true
                        onMoved: backend.set_config_value("steps", value)
                    }
                }

                // CFG
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    RowLayout {
                        Text { text: "Default CFG Scale"; color: Theme.TEXT; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text { text: sliderDefaultCfg.value.toFixed(1); color: Theme.SUBTEXT0 }
                    }
                    Slider {
                        id: sliderDefaultCfg
                        from: 1.0; to: 20.0; stepSize: 0.5
                        Layout.fillWidth: true
                        onMoved: backend.set_config_value("guidance", value)
                    }
                }

                // Negative Prompt
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text { text: "Default Negative Prompt"; color: Theme.TEXT; font.bold: true }
                    TextArea {
                        id: txtDefaultNeg
                        Layout.fillWidth: true
                        Layout.preferredHeight: 80
                        wrapMode: TextEdit.Wrap
                        color: Theme.TEXT
                        background: Rectangle {
                            color: Theme.MANTLE
                            border.color: Theme.SURFACE0
                            radius: Theme.BORDER_RADIUS
                        }
                        // Save on focus loss or explicit action (to avoid spamming IO on every keystroke)
                        onEditingFinished: backend.set_config_value("neg_prompt", text)
                    }
                    Text { text: "Press TAB or click outside to save."; color: Theme.OVERLAY0; font.pixelSize: 12 }
                }

                // 2. Advanced Section
                Item { height: 10 }
                Text { text: "Advanced Pipelines"; color: Theme.LAVENDER; font.bold: true; font.pixelSize: 18 }
                
                // Pony Mode
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Text { text: "🦄 Pony Diffusion Mode"; color: Theme.TEXT; font.bold: true; font.pixelSize: 16 }
                        Text { 
                            text: "Automatically adds score tags (score_9, score_8_up...) and anime source tags."
                            color: Theme.SUBTEXT0; font.pixelSize: 12 
                            Layout.maximumWidth: 400
                            wrapMode: Text.WordWrap
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Switch {
                        id: switchPony
                        onToggled: backend.set_config_value("pony_mode", checked)
                    }
                }

                // FreeU
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Text { text: "⚡ FreeU (Quality Boost)"; color: Theme.TEXT; font.bold: true; font.pixelSize: 16 }
                        Text { 
                            text: "Improves image quality (texture/details) at no extra cost using U-Net re-weighting."
                            color: Theme.SUBTEXT0; font.pixelSize: 12 
                            Layout.maximumWidth: 400
                            wrapMode: Text.WordWrap
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Switch {
                        id: switchFreeU
                        onToggled: backend.set_config_value("use_freeu", checked)
                    }
                }
            }
        }
    }
}
