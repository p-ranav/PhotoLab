from PyQt6.QtWidgets import QWidget, QToolButton, QHBoxLayout, QScrollArea
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize
from PyQt6 import QtCore
from QFlowLayout import QFlowLayout

class QToolInstagramFilters(QScrollArea):
    def __init__(self, parent=None, toolInput=None):
        super(QToolInstagramFilters, self).__init__(None)
        self.parent = parent
        self.toolInput = toolInput
        self.output = None
        self.layout = QHBoxLayout()
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 800, 800))
        self.setWidget(self.scrollAreaWidgetContents)
        self.scrollAreaWidgetContents.setLayout(self.layout)

        image = toolInput.copy()

        from PIL import Image
        image.thumbnail((200, 200), Image.ANTIALIAS)

        import pilgram
        filters = [
            pilgram._1977,
            pilgram.aden,
            pilgram.brannan,
            pilgram.brooklyn,
            pilgram.clarendon,
            pilgram.earlybird,
            pilgram.gingham,
            pilgram.hudson,
            pilgram.inkwell,
            pilgram.kelvin,
            pilgram.lark,
            pilgram.lofi,
            pilgram.maven,
            pilgram.mayfair,
            pilgram.moon,
            pilgram.nashville,
            pilgram.perpetua,
            pilgram.reyes,
            pilgram.rise,
            pilgram.slumber,
            pilgram.stinson,
            pilgram.toaster,
            pilgram.valencia,
            pilgram.walden,
            pilgram.willow,
            pilgram.xpro2  
        ]

        filterNames = [
            "1977",
            "Aden",
            "Brannan",
            "Brooklyn",
            "Clarendon",
            "Earlybird",
            "Gingham",
            "Hudson",
            "Inkwell",
            "Kelvin",
            "Lark",
            "Lofi",
            "Maven",
            "Mayfair",
            "Moon",
            "Nashville",
            "Perpetua",
            "Reyes",
            "Rise",
            "Slumber",
            "Stinson",
            "Toaster",
            "Valencia",
            "Walden",
            "Willow",
            "Xpro2"
        ]

        buttonIconSize = QSize(200, 200)

        noFilterButton = QToolButton()
        unfilteredPixmap = self.parent.ImageToQPixmap(image)
        unfilteredPixmap = unfilteredPixmap.scaled(buttonIconSize, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        icon = QIcon(unfilteredPixmap)
        noFilterButton.setIcon(icon)
        noFilterButton.setIconSize(buttonIconSize)
        noFilterButton.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        noFilterButton.setText("No Filter")
        noFilterButton.setObjectName("unfiltered")
        noFilterButton.clicked.connect(self.OnFilterSelect)
        self.layout.addWidget(noFilterButton)

        for i, f in enumerate(filters):
            filterButton = QToolButton()
            filtered = f(image).convert("RGBA")
            filteredPixmap = self.parent.ImageToQPixmap(filtered)
            filteredPixmap = filteredPixmap.scaled(buttonIconSize, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)

            icon = QIcon(filteredPixmap)
            filterButton.setIcon(icon)
            filterButton.setIconSize(buttonIconSize)
            filterButton.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            filterButton.setText(filterNames[i])
            filterButton.setObjectName(f.__name__)
            filterButton.clicked.connect(self.OnFilterSelect)
            self.layout.addWidget(filterButton)

        self.output = None 

    def OnFilterSelect(self):
        import pilgram
        button = self.sender()
        filterName = button.objectName()
        if filterName != "unfiltered":
            filterFunction = getattr(pilgram, filterName)
            self.output = filterFunction(self.toolInput).convert("RGBA")
        else:
            self.output = self.toolInput
        self.parent.image_viewer.setImage(self.parent.ImageToQPixmap(self.output), False)

    def closeEvent(self, event):
        self.destroyed.emit()
        event.accept()
        self.closed = True
        self.parent.DisableTool("instagram_filters")
        print("Closed")
