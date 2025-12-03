import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "Theme.js" as Theme

Item {
    id: root

    // --- State ---
    property int currentTab: 0 
    
    // Signal to tell main.qml to switch to Generate tab
    signal restoreParameters(string prompt, string neg, int steps, double cfg, string seed, string model, string lora, double lora_scale)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        // --- Header ---
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Collection"
                color: Theme.LAVENDER
                font.pixelSize: 28
                font.bold: true
                font.family: Theme.FONT_FAMILY
            }
            Item { Layout.fillWidth: true }
            
            // Tabs
            RowLayout {
                spacing: 10
                TabButtonCustom {
                    text: "Gallery"
                    iconText: "🖼️"
                    isActive: root.currentTab === 0
                    onClicked: root.currentTab = 0
                }
                TabButtonCustom {
                    text: "Presets"
                    iconText: "🎛️"
                    isActive: root.currentTab === 1
                    onClicked: root.currentTab = 1
                }
                TabButtonCustom {
                    text: "Characters"
                    iconText: "👤"
                    isActive: root.currentTab === 2
                    onClicked: root.currentTab = 2
                }
            }
        }
        
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.SURFACE0 }

        // --- Content Stack ---
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentTab
            
            // === TAB 1: GALLERY ===
            Item {
                id: tabGallery
                property string searchText: ""
                property string sortBy: "Newest First"
                property string modelFilter: "All Models"
                
                function refreshGallery() {
                    var imgs = backend.get_gallery_images(searchText, sortBy, modelFilter, 100, 0)
                    galleryView.model = imgs
                }
                Component.onCompleted: refreshGallery()

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    // Filter Bar
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        TextField {
                            placeholderText: "Search prompts..."
                            Layout.fillWidth: true
                            color: Theme.TEXT
                            background: Rectangle { color: Theme.MANTLE; border.color: Theme.SURFACE0; radius: Theme.BORDER_RADIUS }
                            onAccepted: { tabGallery.searchText = text; tabGallery.refreshGallery() }
                        }
                        Button {
                            text: "Refresh"
                            onClicked: tabGallery.refreshGallery()
                            background: Rectangle { color: Theme.SURFACE0; radius: Theme.BORDER_RADIUS }
                            contentItem: Text { text: parent.text; color: Theme.TEXT; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                    }
                    
                    GridView {
                        id: galleryView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        cellWidth: 230
                        cellHeight: 230
                        model: [] 
                        
                        delegate: Item {
                            width: galleryView.cellWidth
                            height: galleryView.cellHeight
                            
                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: 5
                                color: Theme.MANTLE
                                radius: Theme.BORDER_RADIUS
                                border.color: Theme.SURFACE0
                                border.width: 1
                                
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: detailPopup.openImage(modelData)
                                }

                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 2
                                    source: "file://" + modelData.path
                                    fillMode: Image.PreserveAspectCrop
                                    asynchronous: true
                                    sourceSize.width: 250 
                                    sourceSize.height: 250
                                }
                                
                                // Hover Overlay
                                Rectangle {
                                    anchors.fill: parent
                                    color: "#80000000"
                                    visible: mouseAreaHover.containsMouse
                                    radius: Theme.BORDER_RADIUS
                                    
                                    Rectangle {
                                        width: 28; height: 28
                                        radius: 14
                                        color: Theme.RED
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: 5
                                        Text { text: "✕"; anchors.centerIn: parent; color: "white" }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (backend.delete_image(modelData.path)) tabGallery.refreshGallery()
                                            }
                                        }
                                    }
                                }
                                MouseArea {
                                    id: mouseAreaHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    propagateComposedEvents: true
                                    onClicked: (mouse) => { mouse.accepted = false } 
                                }
                            }
                        }
                    }
                }
            }
            
            // === TAB 2: PRESETS ===
            Item { 
                id: tabPresets
                
                function refreshPresets() {
                    presetView.model = backend.get_presets()
                }
                
                onVisibleChanged: if (visible) refreshPresets()

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15
                    
                    // Toolbar
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Text { text: "Generation Presets"; color: Theme.TEXT; font.bold: true; font.pixelSize: 18 }
                        Item { Layout.fillWidth: true }
                        Button {
                            text: "+ New Preset"
                            background: Rectangle { color: Theme.GREEN; radius: Theme.BORDER_RADIUS }
                            contentItem: Text { text: parent.text; color: Theme.BASE; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            onClicked: presetDialog.openNew()
                        }
                    }
                    
                    // Presets Grid
                    GridView {
                        id: presetView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        cellWidth: 300
                        cellHeight: 160
                        model: []
                        
                        delegate: Item {
                            width: presetView.cellWidth
                            height: presetView.cellHeight
                            
                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: 8
                                color: Theme.MANTLE
                                radius: Theme.BORDER_RADIUS
                                border.color: Theme.SURFACE0
                                border.width: 1
                                
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 15
                                    spacing: 5
                                    
                                    RowLayout {
                                        Text { text: "🎛️"; font.pixelSize: 20 }
                                        Text { text: modelData.name; color: Theme.TEXT; font.bold: true; font.pixelSize: 16; Layout.fillWidth: true }
                                        
                                        // Delete
                                        Button {
                                            text: "✕"
                                            background: Rectangle { color: "transparent" }
                                            contentItem: Text { text: parent.text; color: Theme.RED; font.bold: true }
                                            onClicked: {
                                                if (backend.delete_preset(modelData.id)) tabPresets.refreshPresets()
                                            }
                                        }
                                    }
                                    
                                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.SURFACE0; Layout.bottomMargin: 5 }
                                    
                                    Text { text: "Model: " + modelData.model.split('/').pop(); color: Theme.SUBTEXT0; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text { text: "LoRA: " + modelData.lora + " (" + modelData.lora_scale + ")"; color: Theme.SUBTEXT0; font.pixelSize: 12; visible: modelData.lora !== "None" }
                                    Text { text: "Steps: " + modelData.steps + " | CFG: " + modelData.cfg; color: Theme.SUBTEXT0; font.pixelSize: 12 }
                                    
                                    Item { Layout.fillHeight: true }
                                    
                                    Button {
                                        text: "⚡ Apply & Generate"
                                        Layout.fillWidth: true
                                        background: Rectangle { color: Theme.BLUE; radius: 4 }
                                        contentItem: Text { text: parent.text; color: Theme.BASE; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                        onClicked: {
                                            root.restoreParameters(
                                                modelData.prompt_template, modelData.negative_prompt,
                                                modelData.steps, modelData.cfg, "", 
                                                modelData.model, modelData.lora, modelData.lora_scale
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            // === TAB 3: CHARACTERS ===
            Item {
                id: tabCharacters
                
                function refreshCharacters() {
                    charView.model = backend.get_characters()
                }
                
                onVisibleChanged: if (visible) refreshCharacters()

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15
                    
                    // Toolbar
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Text { text: "My Characters"; color: Theme.TEXT; font.bold: true; font.pixelSize: 18 }
                        Item { Layout.fillWidth: true }
                        
                        Button {
                            text: "+ New Character"
                            background: Rectangle { color: Theme.GREEN; radius: Theme.BORDER_RADIUS }
                            contentItem: Text { text: parent.text; color: Theme.BASE; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            onClicked: charDialog.openNew()
                        }
                    }
                    
                    // Characters Grid
                    GridView {
                        id: charView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        cellWidth: 350
                        cellHeight: 200 // Increased height for the "Use" button
                        model: []
                        
                        delegate: Item {
                            width: charView.cellWidth
                            height: charView.cellHeight
                            
                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: 8
                                color: Theme.MANTLE
                                radius: Theme.BORDER_RADIUS
                                border.color: Theme.SURFACE0
                                border.width: 1
                                
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 15
                                    spacing: 15
                                    
                                    // Avatar
                                    Rectangle {
                                        width: 100
                                        height: 100
                                        color: Theme.CRUST
                                        radius: 50
                                        clip: true
                                        border.color: Theme.MAUVE
                                        border.width: 2
                                        
                                        Image {
                                            anchors.fill: parent
                                            source: modelData.preview_path ? "file://" + modelData.preview_path : ""
                                            fillMode: Image.PreserveAspectCrop
                                            sourceSize.width: 150
                                            sourceSize.height: 150
                                            
                                            Text {
                                                visible: parent.status !== Image.Ready
                                                anchors.centerIn: parent
                                                text: "👤"
                                                font.pixelSize: 40
                                            }
                                        }
                                    }
                                    
                                    // Info
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        spacing: 5
                                        
                                        Text { text: modelData.name; color: Theme.TEXT; font.bold: true; font.pixelSize: 18 }
                                        Text { text: modelData.description; color: Theme.SUBTEXT0; font.italic: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                        
                                        // LoRA Badge
                                        Rectangle {
                                            visible: modelData.default_lora !== "None"
                                            color: Theme.SURFACE0
                                            radius: 4
                                            height: 18
                                            width: txtLora.width + 10
                                            Text { 
                                                id: txtLora
                                                anchors.centerIn: parent
                                                text: "🧬 " + modelData.default_lora.split('/').pop() 
                                                font.pixelSize: 10; color: Theme.MAUVE 
                                            }
                                        }
                                        
                                        Item { Layout.fillHeight: true } // Spacer
                                        
                                        // Use Button (New!)
                                        Button {
                                            text: "✨ Use Character"
                                            Layout.fillWidth: true
                                            background: Rectangle { color: Theme.MAUVE; radius: 4 }
                                            contentItem: Text { text: parent.text; color: Theme.BASE; font.bold: true; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            onClicked: {
                                                // Trigger restore parameters with character data
                                                // We keep prompt empty so user can type, but we could also put trigger words there
                                                root.restoreParameters(
                                                    modelData.trigger_words + ", ", 
                                                    "", // Negative
                                                    30, // Default Steps
                                                    7.0, // Default CFG
                                                    "", // Random Seed
                                                    "stabilityai/stable-diffusion-xl-base-1.0", // Default Model (or we could add model to char DB later)
                                                    modelData.default_lora,
                                                    modelData.lora_scale
                                                )
                                            }
                                        }
                                        
                                        RowLayout {
                                            spacing: 10
                                            Button {
                                                text: "Edit"
                                                background: Rectangle { color: Theme.SURFACE0; radius: 4 }
                                                contentItem: Text { text: parent.text; color: Theme.TEXT; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                                onClicked: charDialog.openEdit(modelData)
                                            }
                                            Button {
                                                text: "Delete"
                                                background: Rectangle { color: Theme.RED; radius: 4 }
                                                contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                                onClicked: {
                                                    if (backend.delete_character(modelData.id)) tabCharacters.refreshCharacters()
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // --- Detail Popup (Gallery) ---
    Popup {
        id: detailPopup
        anchors.centerIn: parent
        width: Math.min(1400, root.width - 50)
        height: Math.min(1000, root.height - 50)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 0 
        
        property var currentData: null
        
        function openImage(data) {
            currentData = data
            imageArea.isZoomed = false
            detailPopup.open()
        }
        
        background: Rectangle { color: Theme.BASE; border.color: Theme.LAVENDER; border.width: 2; radius: 10 }
        
        contentItem: RowLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 20
            
            Rectangle {
                id: imageArea
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumWidth: 400
                color: "black"; clip: true; radius: 8
                property bool isZoomed: false

                Flickable {
                    anchors.fill: parent
                    contentWidth: imageArea.isZoomed ? fullImg.sourceSize.width : parent.width
                    contentHeight: imageArea.isZoomed ? fullImg.sourceSize.height : parent.height
                    interactive: imageArea.isZoomed
                    clip: true

                    Image {
                        id: fullImg
                        source: detailPopup.currentData ? "file://" + detailPopup.currentData.path : ""
                        asynchronous: true
                        fillMode: Image.PreserveAspectFit
                        width: imageArea.isZoomed ? sourceSize.width : parent.width
                        height: imageArea.isZoomed ? sourceSize.height : parent.height
                    }
                }
                
                Text {
                    anchors.centerIn: parent
                    visible: fullImg.status === Image.Error || fullImg.status === Image.Null
                    text: "❌ Image Load Error\n" + (detailPopup.currentData ? detailPopup.currentData.path : "No Data")
                    color: "red"
                    horizontalAlignment: Text.AlignHCenter
                }

                Button {
                    id: zoomBtn
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 15
                    z: 100
                    visible: fullImg.status === Image.Ready 
                    
                    text: imageArea.isZoomed ? "🔄 Fit View" : "🔍 Original Size"
                    leftPadding: 16
                    rightPadding: 16
                    topPadding: 10
                    bottomPadding: 10
                    
                    background: Rectangle { 
                        color: Theme.MANTLE
                        radius: Theme.BORDER_RADIUS
                        border.color: Theme.SURFACE0
                        border.width: 1
                        opacity: 0.9 
                    }
                    contentItem: Text { 
                        text: zoomBtn.text
                        color: Theme.TEXT
                        font.bold: true
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter 
                    }
                    onClicked: imageArea.isZoomed = !imageArea.isZoomed
                }
            }
            
            ColumnLayout {
                Layout.preferredWidth: 350; Layout.fillHeight: true; spacing: 15
                Text { text: "Image Details"; color: Theme.LAVENDER; font.bold: true; font.pixelSize: 20 }
                ScrollView {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    TextArea {
                        text: detailPopup.currentData ? 
                              "<b>Prompt:</b><br>" + detailPopup.currentData.prompt + "<br><br>" +
                              "<b>Negative:</b><br>" + detailPopup.currentData.negative_prompt + "<br><br>" +
                              "<b>Model:</b> " + detailPopup.currentData.model + "<br>" +
                              "<b>Seed:</b> " + detailPopup.currentData.seed + "<br>" +
                              "<b>Steps:</b> " + detailPopup.currentData.steps + " | <b>CFG:</b> " + detailPopup.currentData.cfg + "<br>" +
                              "<b>Size:</b> " + fullImg.sourceSize.width + "x" + fullImg.sourceSize.height
                              : ""
                        color: Theme.TEXT; textFormat: TextEdit.RichText; readOnly: true; wrapMode: TextEdit.Wrap; background: Rectangle { color: Theme.MANTLE; radius: 8 }
                    }
                }
                Button {
                    text: "✨ Use Parameters"
                    Layout.fillWidth: true; background: Rectangle { color: Theme.MAUVE; radius: 8 }
                    contentItem: Text { text: parent.text; color: Theme.BASE; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: {
                        var d = detailPopup.currentData
                        root.restoreParameters(d.prompt, d.negative_prompt, parseInt(d.steps), parseFloat(d.cfg), d.seed, d.model, "None", 0.8)
                        detailPopup.close()
                    }
                }
                Button {
                    text: "🗑️ Delete Image"
                    Layout.fillWidth: true; background: Rectangle { color: Theme.RED; radius: 8 }
                    contentItem: Text { text: parent.text; color: "white"; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { if (backend.delete_image(detailPopup.currentData.path)) { tabGallery.refreshGallery(); detailPopup.close() } }
                }
                Button {
                    text: "Close"
                    Layout.fillWidth: true; onClicked: detailPopup.close(); background: Rectangle { color: Theme.SURFACE0; radius: 8 }
                    contentItem: Text { text: parent.text; color: Theme.TEXT; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
            }
        }
    }
    
    // --- Character Editor Dialog (UPDATED with LoRA) ---
    Dialog {
        id: charDialog
        title: isEditMode ? "Edit Character" : "New Character"
        anchors.centerIn: parent
        width: 600 // Wider to fit LoRA controls
        modal: true
        closePolicy: Popup.CloseOnEscape
        
        property bool isEditMode: false
        property int editId: -1
        
        function openNew() {
            isEditMode = false; editId = -1
            inpName.text = ""; inpDesc.text = ""; inpTrigger.text = ""; inpNotes.text = ""; inpPreview.text = ""
            comboCLora.currentIndex = 0; inpCLoraScale.value = 0.8
            charDialog.open()
        }
        
        function openEdit(data) {
            isEditMode = true; editId = data.id
            inpName.text = data.name; inpDesc.text = data.description
            inpTrigger.text = data.trigger_words; inpNotes.text = data.notes; inpPreview.text = data.preview_path
            
            // Set LoRA
            var loraIdx = comboCLora.find(data.default_lora)
            if (loraIdx !== -1) comboCLora.currentIndex = loraIdx
            inpCLoraScale.value = data.lora_scale
            
            charDialog.open()
        }
        
        background: Rectangle { color: Theme.BASE; border.color: Theme.SURFACE0; border.width: 1; radius: 10 }
        
        contentItem: ColumnLayout {
            spacing: 15
            
            Text { 
                text: charDialog.title
                color: Theme.LAVENDER
                font.bold: true
                font.pixelSize: 20
                Layout.alignment: Qt.AlignHCenter 
            }
            
            TextField { id: inpName; placeholderText: "Character Name"; Layout.fillWidth: true; color: Theme.TEXT; background: Rectangle { color: Theme.MANTLE; radius: 4; border.color: Theme.SURFACE0 } }
            TextField { id: inpDesc; placeholderText: "Short Description"; Layout.fillWidth: true; color: Theme.TEXT; background: Rectangle { color: Theme.MANTLE; radius: 4; border.color: Theme.SURFACE0 } }
            TextField { id: inpTrigger; placeholderText: "Trigger Words (comma separated)"; Layout.fillWidth: true; color: Theme.TEXT; background: Rectangle { color: Theme.MANTLE; radius: 4; border.color: Theme.SURFACE0 } }
            
            // --- LoRA Selection (New) ---
            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.SURFACE0 }
            Text { text: "Associated LoRA (Optional)"; color: Theme.MAUVE; font.bold: true }
            
            RowLayout {
                ComboBox { 
                    id: comboCLora
                    Layout.fillWidth: true
                    model: backend.get_loras() 
                    background: Rectangle { color: Theme.MANTLE; radius: 4; border.color: Theme.SURFACE0 }
                    contentItem: Text { text: comboCLora.currentText; color: Theme.TEXT; leftPadding: 10; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                }
                
                Text { text: "Strength: " + inpCLoraScale.value.toFixed(1); color: Theme.TEXT }
                Slider { id: inpCLoraScale; from: 0.0; to: 2.0; stepSize: 0.1; Layout.preferredWidth: 150 }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.SURFACE0 }
            // -----------------------------
            
            RowLayout {
                TextField { id: inpPreview; placeholderText: "Avatar Path (Optional)"; Layout.fillWidth: true; color: Theme.TEXT; background: Rectangle { color: Theme.MANTLE; radius: 4; border.color: Theme.SURFACE0 } }
                Button { 
                    text: "📁"; width: 40
                    onClicked: fileDialog.open()
                    background: Rectangle { color: Theme.SURFACE0; radius: 4 }
                    contentItem: Text { text: parent.text; color: Theme.TEXT; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
            }
            
            TextArea { id: inpNotes; placeholderText: "Notes / Backstory..."; Layout.fillWidth: true; Layout.preferredHeight: 80; color: Theme.TEXT; background: Rectangle { color: Theme.MANTLE; radius: 4; border.color: Theme.SURFACE0 } }
            
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { 
                    text: "Cancel"
                    onClicked: charDialog.close()
                    background: Rectangle { color: Theme.SURFACE0; radius: 4 }
                    contentItem: Text { text: parent.text; color: Theme.TEXT; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
                Button { 
                    text: "Save"
                    background: Rectangle { color: Theme.GREEN; radius: 4 }
                    contentItem: Text { text: parent.text; color: Theme.BASE; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: {
                        if (charDialog.isEditMode) {
                            backend.update_character(charDialog.editId, inpName.text, inpDesc.text, inpTrigger.text, inpPreview.text, inpNotes.text, comboCLora.currentText, inpCLoraScale.value)
                        } else {
                            backend.add_character(inpName.text, inpDesc.text, inpTrigger.text, inpPreview.text, inpNotes.text, comboCLora.currentText, inpCLoraScale.value)
                        }
                        tabCharacters.refreshCharacters()
                        charDialog.close()
                    }
                }
            }
        }
    }
    
    // --- Preset Editor Dialog ---
    Dialog {
        id: presetDialog
        title: "New Preset"
        anchors.centerIn: parent
        width: 500
        modal: true
        closePolicy: Popup.CloseOnEscape
        
        function openNew() {
            inpPName.text = ""
            inpPSteps.value = 30
            inpPCfg.value = 7.0
            inpPPrompt.text = ""
            inpPNeg.text = ""
            comboPModel.currentIndex = 0
            comboPLora.currentIndex = 0
            presetDialog.open()
        }
        
        background: Rectangle { 
            color: Theme.BASE
            border.color: Theme.SURFACE0
            border.width: 1
            radius: 10 
        }
        
        contentItem: ColumnLayout {
            spacing: 15
            Text { 
                text: "Create New Preset"
                color: Theme.LAVENDER
                font.bold: true
                font.pixelSize: 20
                Layout.alignment: Qt.AlignHCenter 
            }
            
            TextField { 
                id: inpPName
                placeholderText: "Preset Name (e.g. Cinematic 80s)"
                Layout.fillWidth: true
                color: Theme.TEXT
                background: Rectangle { 
                    color: Theme.MANTLE
                    radius: 4
                    border.color: Theme.SURFACE0 
                } 
            }
            
            RowLayout {
                ComboBox { 
                    id: comboPModel
                    Layout.fillWidth: true
                    model: backend.get_models() 
                    background: Rectangle { 
                        color: Theme.MANTLE
                        radius: 4
                        border.color: Theme.SURFACE0 
                    }
                    contentItem: Text { 
                        text: comboPModel.currentText
                        color: Theme.TEXT
                        leftPadding: 10
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight 
                    }
                }
                ComboBox { 
                    id: comboPLora
                    Layout.fillWidth: true
                    model: backend.get_loras()
                    background: Rectangle { 
                        color: Theme.MANTLE
                        radius: 4
                        border.color: Theme.SURFACE0 
                    }
                    contentItem: Text { 
                        text: comboPLora.currentText
                        color: Theme.TEXT
                        leftPadding: 10
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight 
                    }
                }
            }
            
            RowLayout {
                Text { text: "Steps: " + inpPSteps.value; color: Theme.TEXT }
                Slider { id: inpPSteps; from: 1; to: 100; value: 30; stepSize: 1; Layout.fillWidth: true }
                Text { text: "CFG: " + inpPCfg.value.toFixed(1); color: Theme.TEXT }
                Slider { id: inpPCfg; from: 1.0; to: 20.0; value: 7.0; stepSize: 0.5; Layout.fillWidth: true }
            }
            
            TextArea { 
                id: inpPPrompt
                placeholderText: "Prompt Template..."
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                color: Theme.TEXT
                background: Rectangle { 
                    color: Theme.MANTLE
                    radius: 4
                    border.color: Theme.SURFACE0 
                } 
            }
            TextArea { 
                id: inpPNeg
                placeholderText: "Negative Prompt..."
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                color: Theme.TEXT
                background: Rectangle { 
                    color: Theme.MANTLE
                    radius: 4
                    border.color: Theme.SURFACE0 
                } 
            }
            
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { 
                    text: "Cancel"
                    onClicked: presetDialog.close()
                    background: Rectangle { 
                        color: Theme.SURFACE0
                        radius: 4 
                    }
                    contentItem: Text { 
                        text: parent.text
                        color: Theme.TEXT
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter 
                    }
                }
                Button { 
                    text: "Save"
                    background: Rectangle { 
                        color: Theme.GREEN
                        radius: 4 
                    }
                    contentItem: Text { 
                        text: parent.text
                        color: Theme.BASE
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter 
                    }
                    onClicked: {
                        backend.add_preset(
                            inpPName.text, comboPModel.currentText, comboPLora.currentText, 0.8, 
                            inpPSteps.value, inpPCfg.value, inpPPrompt.text, inpPNeg.text
                        )
                        tabPresets.refreshPresets()
                        presetDialog.close()
                    }
                }
            }
        }
    }

    FileDialog {
        id: fileDialog
        title: "Select Avatar Image"
        nameFilters: ["Images (*.png *.jpg *.jpeg)"]
        onAccepted: {
            var p = fileDialog.currentFile.toString()
            if (p.startsWith("file://")) p = p.substring(7)
            inpPreview.text = p
        }
    }

    component TabButtonCustom: Button {
        id: tBtn
        property string iconText: ""
        property bool isActive: false
        
        background: Rectangle {
            color: tBtn.isActive ? Theme.SURFACE0 : "transparent"
            radius: Theme.BORDER_RADIUS
            border.color: tBtn.isActive ? Theme.MAUVE : "transparent"
        }
        
        contentItem: Row {
            spacing: 8
            Text {
                text: tBtn.iconText
                font.pixelSize: 16
            }
            Text {
                text: tBtn.text
                color: tBtn.isActive ? Theme.TEXT : Theme.SUBTEXT0
                font.bold: tBtn.isActive
            }
        }
    }
}
