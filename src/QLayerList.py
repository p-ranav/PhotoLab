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
        button.setIconSize(QtCore.QSize(100, 100))
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
                lb.setIconSize(QtCore.QSize(50, 50))

    def updateScrollView(self):
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

    def onDuplicateLayer(self):
        self.parent.image_viewer.duplicateCurrentLayer()
        self.currentButton.setChecked(False)
        self.currentButton.setIconSize(QtCore.QSize(50, 50))

        self.currentLayer = self.parent.image_viewer.currentLayer
        pixmap = self.parent.getCurrentLayerLatestPixmap()

        button = QtWidgets.QToolButton(self)
        button.setText("Layer " + str(self.currentLayer + 1))
        button.setIcon(QtGui.QIcon(pixmap))
        button.setIconSize(QtCore.QSize(100, 100))
        button.setMinimumHeight(50)
        button.setMinimumWidth(180)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setCheckable(True)
        button.setObjectName("Layer " + str(self.currentLayer))
        button.clicked.connect(self.OnLayerSelect)
        button.setChecked(True)
        self.currentButton = button

        self.layerButtons.append(button)
        self.layout.addWidget(button)

        self.updateScrollView()

    def onDeleteLayer(self):
        objectName = self.currentButton.objectName()

        if len(self.layerButtons) > 1:
            # Can only delete second, third, etc. layers
            # Cannot delete when only 1 layer is open

            layerIndex = objectName.split("Layer ")[-1]
            layerIndex = int(layerIndex)

            if self.parent.image_viewer.currentLayer == layerIndex:
                # Current layer matches
                # Switch to a different layer first
                layerList = list(reversed(self.layerButtons))

                nextLayer = None
                newLayerButtons = []

                for i, l in enumerate(layerList):
                    if l.objectName() == objectName:
                        # l is the layer being deleted
                        # The next layer in the layer we want to switch to

                        nextIndex = i + 1 if (i + 1 < len(layerList)) else (i - 1)

                        if nextIndex >= 0:
                            nextLayer = layerList[nextIndex]
                            nextLayer.setChecked(True)
                            nextLayerIndex = int(nextLayer.objectName().split("Layer ")[-1])
                            
                            if nextLayerIndex is not None:
                                self.layout.removeWidget(l)
                                self.currentButton = nextLayer
                                self.currentButton.setIconSize(QtCore.QSize(100, 100))
                                self.parent.image_viewer.currentLayer = nextLayerIndex
                                pixmap = self.parent.image_viewer.getCurrentLayerLatestPixmap()
                                self.parent.image_viewer.setImage(pixmap, False)
                                previous = self.parent.image_viewer.getCurrentLayerPreviousPixmap()
                                if previous:
                                    self.parent.previousImage.setImage(previous, False)
                                del self.parent.image_viewer.layerHistory[layerIndex]
                    else:
                        newLayerButtons.append(l)

                self.layerButtons = list(reversed(newLayerButtons))

    def init(self):
        self.numLayers = self.getNumberOfLayers()
        self.currentLayer = self.parent.image_viewer.currentLayer
        pixmap = self.parent.getCurrentLayerLatestPixmap()

        if not self.currentButton:
            titleBar = QtWidgets.QWidget()
            titleBar.setContentsMargins(0, 0, 0, 0)
            titleBarLayout = QtWidgets.QHBoxLayout()
            titleBarLayout.setContentsMargins(0, 0, 0, 0)
            titleBar.setLayout(titleBarLayout)
            titleBar.setMinimumWidth(180)
            titleBarLayout.setSpacing(0)

            duplicateLayerButton = QtWidgets.QPushButton()
            self.parent.setIconPixmapWithColor(duplicateLayerButton, "icons/duplicate.svg")
            duplicateLayerButton.setIconSize(QtCore.QSize(20, 20))
            duplicateLayerButton.setToolTip("Duplicate Layer")
            duplicateLayerButton.clicked.connect(self.onDuplicateLayer)

            duplicateLayerButton.setStyleSheet('''
                border: none;
                color: white;
                background-color: rgb(83, 83, 83);
            ''')

            deleteLayerButton = QtWidgets.QPushButton()
            self.parent.setIconPixmapWithColor(deleteLayerButton, "icons/trash.svg")
            deleteLayerButton.setIconSize(QtCore.QSize(20, 20))
            deleteLayerButton.setToolTip("Delete Layer")
            deleteLayerButton.clicked.connect(self.onDeleteLayer)

            deleteLayerButton.setStyleSheet('''
                border: none;
                color: white;
                background-color: rgb(83, 83, 83);
            ''')

            tools = QtWidgets.QWidget()
            toolsLayout = QtWidgets.QHBoxLayout()
            toolsLayout.addWidget(duplicateLayerButton)
            toolsLayout.addWidget(deleteLayerButton)
            tools.setLayout(toolsLayout)

            titleBarLayout.addWidget(tools)
            titleBarLayout.setAlignment(tools, Qt.AlignmentFlag.AlignCenter)

            self.layout.addWidget(titleBar)

        for i in range(self.numLayers):
            button = QtWidgets.QToolButton(self)
            button.setText("Layer " + str(i + 1))
            button.setIcon(QtGui.QIcon(pixmap))
            button.setIconSize(QtCore.QSize(100, 100))
            button.setMinimumHeight(50)
            button.setMinimumWidth(180)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setCheckable(True)
            button.setObjectName("Layer " + str(i))
            button.clicked.connect(self.OnLayerSelect)
            button.setStyleSheet("background-color: rgb(44, 44, 44);")
            if i == self.currentLayer:
                button.setChecked(True)
                self.currentButton = button
            else:
                button.setChecked(False)

            self.layerButtons.append(button)
            self.layout.addWidget(button)

        self.updateScrollView()

    def update(self):
        self.init()

    def setButtonPixmap(self, pixmap):
        self.currentButton.setIcon(QtGui.QIcon(pixmap))