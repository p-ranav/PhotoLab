from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import Qt
from QFlowLayout import QFlowLayout

class QLayerList(QtWidgets.QDockWidget):
    def __init__(self, title, parent):
        super(QLayerList, self).__init__(title, parent)

        self.parent = parent
        self.layout = QFlowLayout()
        self.layerButtons = []
        self.currentButton = None
        self.init()

    def getNumberOfLayers(self):
        if getattr(self.parent, "image_viewer", None):
            layerHistoryMap = self.parent.image_viewer.layerHistory
            return len(layerHistoryMap.keys())
        else:
            return 0

    def OnLayerSelect(self):
        button = self.sender()
        selectedLayerIndex = button.objectName().split("Layer ")[-1]
        selectedLayerIndex = int(selectedLayerIndex)
        self.parent.image_viewer.currentLayer = selectedLayerIndex
        for lb in self.layerButtons:
            if lb.objectName() == button.objectName():
                lb.setChecked(True)
                self.currentButton = lb
                pixmap = self.parent.image_viewer.getCurrentLayerLatestPixmap()
                self.parent.image_viewer.setImage(pixmap, False)
                previous = self.parent.image_viewer.getCurrentLayerPreviousPixmap()
                if previous:
                    self.parent.previousImage.setImage(previous, False)
            else:
                lb.setChecked(False)

    def onDuplicateLayer(self):
        self.parent.image_viewer.duplicateCurrentLayer()
        self.parent.layerListDock.update()

    def init(self):
        self.numLayers = self.getNumberOfLayers()
        self.currentLayer = self.parent.image_viewer.currentLayer
        pixmap = self.parent.getCurrentLayerLatestPixmap()

        if not self.currentButton:
            titleBar = QtWidgets.QWidget()
            titleBar.setContentsMargins(0, 0, 0, 0)
            titleBar.setMinimumWidth(260)
            titleBar.setMinimumHeight(20)
            titleBarLayout = QtWidgets.QHBoxLayout()
            titleBarLayout.setContentsMargins(0, 0, 0, 0)
            titleBar.setLayout(titleBarLayout)
            duplicateLayerButton = QtWidgets.QPushButton()
            duplicateLayerButton.setIcon(QtGui.QIcon("icons/duplicate.svg"))
            duplicateLayerButton.setIconSize(QtCore.QSize(20, 20))
            duplicateLayerButton.setToolTip("Duplicate")
            duplicateLayerButton.clicked.connect(self.onDuplicateLayer)
            titleBarLayout.addWidget(duplicateLayerButton)
            titleBarLayout.setAlignment(duplicateLayerButton, Qt.AlignmentFlag.AlignRight)
            self.layout.addWidget(titleBar)

        for i in range(self.numLayers):
            button = QtWidgets.QToolButton(self)
            button.setText("Layer " + str(i + 1))
            button.setIcon(QtGui.QIcon(pixmap))
            button.setIconSize(QtCore.QSize(50, 50))
            button.setMinimumHeight(50)
            button.setMinimumWidth(260)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setCheckable(True)
            button.setObjectName("Layer " + str(i))
            button.clicked.connect(self.OnLayerSelect)
            if i == self.currentLayer:
                button.setChecked(True)
                self.currentButton = button
            else:
                button.setChecked(False)

            self.layerButtons.append(button)
            self.layout.addWidget(button)

        self.scroll = QtWidgets.QScrollArea()
        self.content = QtWidgets.QWidget()

        self.content.setLayout(self.layout)
        self.content.setContentsMargins(0, 0, 0, 0)

        #Scroll Area Properties
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.content)
        self.setWidget(self.scroll)

    def update(self):
        for button in self.layerButtons:
            self.layout.removeWidget(button)
        self.layerButtons = []
        self.init()

    def setButtonPixmap(self, pixmap):
        self.currentButton.setIcon(QtGui.QIcon(pixmap))