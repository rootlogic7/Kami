import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme

Item {
    id: root
    
    // --- Internal State ---
    property string lastImagePath: ""
    property bool isGenerating: false
    property int currentStep: 0
    property int totalSteps: 1
    
    // --- Data Loading ---
    function loadDefaults() {
        var cfg = backend.get_config()
        sliderSteps.value = cfg.steps
        sliderCfg.value = cfg.guidance
        txtNeg.text = cfg.neg_prompt
        chkRefiner.checked = cfg.use_refiner
        
        comboModel.model = backend.get_models()
        var mIdx = comboModel.find(cfg.model_path)
        if (mIdx !== -1) comboModel.currentIndex = mIdx
        
        comboLora.model = backend.get_loras()
        console.log("Generation defaults loaded.")
    }

    Component.onCompleted: loadDefaults()
    
    // --- Signal Connections ---
    Connections {
        target: backend
        function onGenerationFinished(path) {
            console.log("Finished: " + path)
            root.isGenerating = false
            if (path !== "") root.lastImagePath = "file://" + path 
        }
        
        function onProgressChanged(step, total) {
            root.isGenerating = true
            root.currentStep = step
            root.totalSteps = total
        }
        
        function onErrorOccurred(msg) {
            root.isGenerating = false
        }
    }
    
    function setParameters(prompt, neg, steps, cfg, seed, model, lora, loraScale) {
        txtPrompt.text = prompt
        txtNeg.text = neg
        sliderSteps.value = steps
        sliderCfg.value = cfg
        txtSeed.text = seed
        
        var modelIdx = comboModel.find(model)
        if (modelIdx !== -1) comboModel.currentIndex = modelIdx
        
        if (lora && lora !== "None") {
            var loraIdx = comboLora.find(lora)
            if (loraIdx !== -1) comboLora.currentIndex = loraIdx
            sliderLoraScale.value = loraScale
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 20

        // --- LEFT COLUMN: Parameters ---
        Rectangle {
            Layout.preferredWidth: 450
            Layout.fillHeight: true
            color: "transparent"
            
            ScrollView {
                anchors.fill: parent
                contentWidth: parent.width
                clip: true
                
                ColumnLayout {
                    width: parent.width
                    spacing: 15
                    
                    // --- Model Selection ---
                    Text { text: "Base Model"; color: Theme.TEXT; font.bold: true }
                    ComboBox {
                        id: comboModel
                        Layout.fillWidth: true
                        model: [] 
                        background: Rectangle { color: Theme.MANTLE; border.color: Theme.SURFACE0; radius: Theme.BORDER_RADIUS }
                        contentItem: Text { leftPadding: 10; text: comboModel.currentText; color: Theme.TEXT; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                    }

                    Text { text: "LoRA Network"; color: Theme.TEXT; font.bold: true }
                    ComboBox {
                        id: comboLora
                        Layout.fillWidth: true
                        model: [] 
                        background: Rectangle { color: Theme.MANTLE; border.color: Theme.SURFACE0; radius: Theme.BORDER_RADIUS }
                        contentItem: Text { leftPadding: 10; text: comboLora.currentText; color: Theme.TEXT; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                    }
                    
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

                    Item { height: 10 } 
                    
                    // --- Prompt ---
                    Text { text: "Prompt"; color: Theme.TEXT; font.bold: true }
                    TextArea {
                        id: txtPrompt
                        Layout.fillWidth: true
                        Layout.preferredHeight: 300 // VERDOPPELT
                        placeholderText: "A majestic lion in the sunset..."
                        placeholderTextColor: Theme.OVERLAY1 
                        wrapMode: TextEdit.Wrap
                        background: Rectangle { color: Theme.MANTLE; border.color: Theme.SURFACE0; radius: Theme.BORDER_RADIUS }
                        color: Theme.TEXT
                        font.pixelSize: 14
                        selectByMouse: true
                    }
                    
                    Text { text: "Negative Prompt"; color: Theme.TEXT; font.bold: true }
                    TextArea {
                        id: txtNeg
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160 // VERDOPPELT
                        placeholderText: "ugly, blurry, low quality..."
                        placeholderTextColor: Theme.OVERLAY1
                        wrapMode: TextEdit.Wrap
                        background: Rectangle { color: Theme.MANTLE; border.color: Theme.SURFACE0; radius: Theme.BORDER_RADIUS }
                        color: Theme.TEXT
                        font.pixelSize: 14
                        selectByMouse: true
                    }
                    
                    Item { height: 10 } 
                    
                    // --- Params ---
                    RowLayout {
                        Text { text: "Steps: " + sliderSteps.value; color: Theme.TEXT }
                        Layout.fillWidth: true
                    }
                    Slider {
                        id: sliderSteps
                        from: 1; to: 100; stepSize: 1
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
                        placeholderTextColor: Theme.OVERLAY1
                        background: Rectangle { color: Theme.MANTLE; border.color: Theme.SURFACE0; radius: Theme.BORDER_RADIUS }
                        color: Theme.TEXT
                        selectByMouse: true
                    }
                    
                    CheckBox {
                        id: chkRefiner
                        text: "Enable Refiner Pipeline"
                        contentItem: Text { text: parent.text; font: parent.font; color: Theme.TEXT; leftPadding: parent.indicator.width + parent.spacing; verticalAlignment: Text.AlignVCenter }
                    }
                    
                    Item { Layout.fillHeight: true } 
                    
                    Button {
                        text: root.isGenerating ? "GENERATING..." : "GENERATE"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 50
                        Layout.bottomMargin: 20
                        enabled: !root.isGenerating // Disable main button during gen
                        
                        background: Rectangle {
                            color: parent.enabled ? (parent.down ? Theme.TEAL : Theme.BLUE) : Theme.SURFACE0
                            radius: Theme.BORDER_RADIUS
                        }
                        contentItem: Text {
                            text: parent.text
                            font.bold: true
                            font.pixelSize: 16
                            color: parent.enabled ? Theme.BASE : Theme.SUBTEXT0
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        
                        onClicked: {
                            root.isGenerating = true // Set immediately for UI feedback
                            root.currentStep = 0
                            backend.generate(
                                txtPrompt.text, txtNeg.text, sliderSteps.value, sliderCfg.value,
                                txtSeed.text, chkRefiner.checked, comboModel.currentText,
                                comboLora.currentText, sliderLoraScale.value
                            )
                        }
                    }
                }
            }
        }

        // --- RIGHT COLUMN: Preview & Progress ---
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.MANTLE
            radius: Theme.BORDER_RADIUS
            border.color: Theme.SURFACE0
            border.width: 2
            clip: true
            
            Image {
                id: previewImage
                anchors.fill: parent
                anchors.margins: 10
                fillMode: Image.PreserveAspectFit
                source: root.lastImagePath
                asynchronous: true
                cache: false 
                visible: !root.isGenerating // Hide old image during generation
                
                Text {
                    anchors.centerIn: parent
                    text: "No Image Generated"
                    color: Theme.SUBTEXT0
                    visible: parent.status !== Image.Ready && root.lastImagePath === ""
                }
            }
            
            // --- PROGRESS OVERLAY ---
            Rectangle {
                anchors.fill: parent
                color: Theme.BASE
                visible: root.isGenerating
                
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 20
                    width: Math.min(400, parent.width - 40)
                    
                    // Spinner / Icon
                    Text {
                        text: "🎨"
                        font.pixelSize: 48
                        Layout.alignment: Qt.AlignHCenter
                        
                        // Simple pulsing animation
                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            running: root.isGenerating
                            NumberAnimation { from: 1.0; to: 0.5; duration: 800 }
                            NumberAnimation { from: 0.5; to: 1.0; duration: 800 }
                        }
                    }
                    
                    Text {
                        text: "Dreaming... Step " + root.currentStep + " / " + root.totalSteps
                        color: Theme.TEXT
                        font.pixelSize: 18
                        font.bold: true
                        Layout.alignment: Qt.AlignHCenter
                    }
                    
                    ProgressBar {
                        Layout.fillWidth: true
                        from: 0; to: root.totalSteps > 0 ? root.totalSteps : 100
                        value: root.currentStep
                        
                        background: Rectangle {
                            implicitHeight: 8
                            color: Theme.SURFACE0
                            radius: 4
                        }
                        contentItem: Item {
                            implicitHeight: 8
                            Rectangle {
                                width: parent.parent.visualPosition * parent.width
                                height: parent.height
                                radius: 4
                                color: Theme.MAUVE
                            }
                        }
                    }
                    
                    Button {
                        text: "❌ Cancel Generation"
                        Layout.alignment: Qt.AlignHCenter
                        Layout.topMargin: 10
                        
                        background: Rectangle {
                            color: parent.down ? "#b30000" : Theme.RED
                            radius: Theme.BORDER_RADIUS
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "white"
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        
                        onClicked: {
                            backend.cancel()
                        }
                    }
                }
            }
        }
    }
}
