import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
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
                            id: searchField
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
                    
                    // Image Grid
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
                                    
                                    // Delete Button
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
                                                if (backend.delete_image(modelData.path)) {
                                                    tabGallery.refreshGallery()
                                                }
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
            Item { id: tabPresets; Text { text: "Presets Coming Soon"; color: Theme.TEXT; anchors.centerIn: parent } }
            Item { id: tabCharacters; Text { text: "Characters Coming Soon"; color: Theme.TEXT; anchors.centerIn: parent } }
        }
    }

    // --- Detail Popup ---
    Popup {
        id: detailPopup
        anchors.centerIn: parent
        width: Math.min(1400, root.width - 50)
        height: Math.min(1000, root.height - 50)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 0 // Remove default padding to handle layout manually
        
        property var currentData: null
        
        function openImage(data) {
            currentData = data
            imageArea.isZoomed = false
            detailPopup.open()
        }
        
        background: Rectangle {
            color: Theme.BASE
            border.color: Theme.LAVENDER
            border.width: 2
            radius: 10
        }
        
        // Explicit Content Item for robust layout
        contentItem: RowLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 20
            
            // --- Image Viewer Area (Left) ---
            Rectangle {
                id: imageArea
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 400 // Prevent collapse
                color: "black" 
                clip: true
                radius: 8
                
                property bool isZoomed: false

                // 1. Flickable Container
                Flickable {
                    id: flick
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
                
                // 2. Debug/Error Text (Visible only if image fails or path is empty)
                Text {
                    anchors.centerIn: parent
                    visible: fullImg.status === Image.Error || fullImg.status === Image.Null
                    text: "❌ Image Load Error\n" + (detailPopup.currentData ? detailPopup.currentData.path : "No Data")
                    color: "red"
                    horizontalAlignment: Text.AlignHCenter
                }

                // 3. Zoom Button (Overlay)
                Button {
                    id: zoomBtn
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 15
                    z: 100 // Ensure visibility on top
                    visible: fullImg.status === Image.Ready // Only show if image loaded
                    
                    text: imageArea.isZoomed ? "🔄 Fit View" : "🔍 Original Size"
                    
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
                        padding: 8
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: imageArea.isZoomed = !imageArea.isZoomed
                }
            }
            
            // --- Metadata Sidebar (Right) ---
            ColumnLayout {
                Layout.preferredWidth: 350
                Layout.fillHeight: true
                spacing: 15
                
                Text { text: "Image Details"; color: Theme.LAVENDER; font.bold: true; font.pixelSize: 20 }
                
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    TextArea {
                        text: detailPopup.currentData ? 
                              "<b>Prompt:</b><br>" + detailPopup.currentData.prompt + "<br><br>" +
                              "<b>Negative:</b><br>" + detailPopup.currentData.negative_prompt + "<br><br>" +
                              "<b>Model:</b> " + detailPopup.currentData.model + "<br>" +
                              "<b>Seed:</b> " + detailPopup.currentData.seed + "<br>" +
                              "<b>Steps:</b> " + detailPopup.currentData.steps + " | <b>CFG:</b> " + detailPopup.currentData.cfg + "<br>" +
                              "<b>Size:</b> " + fullImg.sourceSize.width + "x" + fullImg.sourceSize.height
                              : ""
                        color: Theme.TEXT
                        textFormat: TextEdit.RichText
                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        background: Rectangle { color: Theme.MANTLE; radius: 8 }
                    }
                }
                
                Button {
                    text: "✨ Use Parameters"
                    Layout.fillWidth: true
                    background: Rectangle { color: Theme.MAUVE; radius: 8 }
                    contentItem: Text { text: parent.text; color: Theme.BASE; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: {
                        var d = detailPopup.currentData
                        var lora = "None"; var loraScale = 0.8 
                        root.restoreParameters(
                            d.prompt, d.negative_prompt, parseInt(d.steps), parseFloat(d.cfg), 
                            d.seed, d.model, lora, loraScale
                        )
                        detailPopup.close()
                    }
                }
                
                Button {
                    text: "🗑️ Delete Image"
                    Layout.fillWidth: true
                    background: Rectangle { color: Theme.RED; radius: 8 }
                    contentItem: Text { text: parent.text; color: "white"; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: {
                        if (backend.delete_image(detailPopup.currentData.path)) {
                            tabGallery.refreshGallery()
                            detailPopup.close()
                        }
                    }
                }
                
                Button {
                    text: "Close"
                    Layout.fillWidth: true
                    onClicked: detailPopup.close()
                    background: Rectangle { color: Theme.SURFACE0; radius: 8 }
                    contentItem: Text { text: parent.text; color: Theme.TEXT; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
            }
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
            Text { text: tBtn.iconText; font.pixelSize: 16 }
            Text { text: tBtn.text; color: tBtn.isActive ? Theme.TEXT : Theme.SUBTEXT0; font.bold: tBtn.isActive }
        }
    }
}
