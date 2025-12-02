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
                Text { text: "Presets Coming Soon"; color: Theme.TEXT; anchors.centerIn: parent } 
            }
            
            // === TAB 3: CHARACTERS ===
            Item {
                id: tabCharacters
                
                function refreshCharacters() {
                    charView.model = backend.get_characters()
                }
                
                // Refresh when tab becomes active
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
                        cellHeight: 180
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
                                        width: 100; height: 100
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
                                            
                                            // Fallback Icon
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
                                        
                                        Item { Layout.fillHeight: true } // Spacer
                                        
                                        Text { text: "Triggers:"; color: Theme.OVERLAY0; font.pixelSize: 12 }
                                        Text { 
                                            text: modelData.trigger_words
                                            color: Theme.MAUVE; font.pixelSize: 12
                                            elide: Text.ElideRight; Layout.fillWidth: true 
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
                
                Button {
                    id: zoomBtn
                    anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 15
                    z: 100; visible: fullImg.status === Image.Ready 
                    text: imageArea.isZoomed ? "🔄 Fit View" : "🔍 Original Size"
                    leftPadding: 16; rightPadding: 16; topPadding: 10; bottomPadding: 10
                    background: Rectangle { color: Theme.MANTLE; radius: Theme.BORDER_RADIUS; border.color: Theme.SURFACE0; border.width: 1; opacity: 0.9 }
                    contentItem: Text { text: zoomBtn.text; color: Theme.TEXT; font.bold: true; font.pixelSize: 14; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
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
                    contentItem: Text { 
                        text: parent.text
                        color: "white" // FIXED: Separated from font.bold
                        font.bold: true 
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter 
                    }
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
    
    // --- Character Editor Dialog ---
    Dialog {
        id: charDialog
        title: isEditMode ? "Edit Character" : "New Character"
        anchors.centerIn: parent
        width: 500
        modal: true
        closePolicy: Popup.CloseOnEscape
        
        property bool isEditMode: false
        property int editId: -1
        
        function openNew() {
            isEditMode = false; editId = -1
            inpName.text = ""; inpDesc.text = ""; inpTrigger.text = ""; inpNotes.text = ""; inpPreview.text = ""
            charDialog.open()
        }
        
        function openEdit(data) {
            isEditMode = true; editId = data.id
            inpName.text = data.name; inpDesc.text = data.description
            inpTrigger.text = data.trigger_words; inpNotes.text = data.notes; inpPreview.text = data.preview_path
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
            
            RowLayout {
                TextField { id: inpPreview; placeholderText: "Avatar Path (Optional)"; Layout.fillWidth: true; color: Theme.TEXT; background: Rectangle { color: Theme.MANTLE; radius: 4; border.color: Theme.SURFACE0 } }
                Button { 
                    text: "📁"; width: 40
                    onClicked: fileDialog.open()
                    background: Rectangle { color: Theme.SURFACE0; radius: 4 }
                    contentItem: Text { text: parent.text; color: Theme.TEXT; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
            }
            
            TextArea { id: inpNotes; placeholderText: "Notes / Backstory..."; Layout.fillWidth: true; Layout.preferredHeight: 100; color: Theme.TEXT; background: Rectangle { color: Theme.MANTLE; radius: 4; border.color: Theme.SURFACE0 } }
            
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
                            backend.update_character(charDialog.editId, inpName.text, inpDesc.text, inpTrigger.text, inpPreview.text, inpNotes.text)
                        } else {
                            backend.add_character(inpName.text, inpDesc.text, inpTrigger.text, inpPreview.text, inpNotes.text)
                        }
                        tabCharacters.refreshCharacters()
                        charDialog.close()
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
