from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QGroupBox,
    QVBoxLayout,
    QFormLayout,
    QSlider,
)
from PyQt6.QtGui import QPixmap
import sys
import qdarkstyle
from PIL import Image, ImageEnhance
from PIL.ImageQt import ImageQt
from functools import partial

class Gui(QtCore.QObject):
    def __init__(self, MainWindow):
        super().__init__()
        self.MainWindow = MainWindow

        self.form = QGroupBox()
        self.form_layout = QVBoxLayout()

        self.logo_label = QLabel()
        self.welcome_pixmap = self.set_label_image(self.logo_label, 'welcome.jpg')
        self.logo_label.installEventFilter(self)
        self.form_layout.addWidget(self.logo_label, alignment=QtCore.Qt.AlignCenter)

        self.form.setLayout(self.form_layout)

        # Set the central widget of the Window. Widget will expand
        # to take up all the space in the window by default.
        self.MainWindow.setCentralWidget(self.form)

        dock = QtWidgets.QDockWidget("")
        dock.setMinimumSize(200, self.logo_label.height())
        MainWindow.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        scroll = QtWidgets.QScrollArea()
        dock.setWidget(scroll)
        content = QtWidgets.QWidget()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        lay = QtWidgets.QFormLayout(content)

        # Enhance sliders
        enhance_label = QLabel("Enhance")
        lay.addWidget(enhance_label)

        self.AddColorSlider(lay)
        self.AddBrightnessSlider(lay)
        self.AddContrastSlider(lay)
        self.AddSharpnessSlider(lay)

        # List of QPixmaps after each change
        # Most recent is the last one
        self.CurrentLayer = self.welcome_pixmap
        self.Color = 100
        self.Brightness = 100
        self.Contrast = 100
        self.Sharpness = 100

        self.MainWindow.showMaximized()

    def set_label_image(self, label, image_filename):
        '''
        Fill a QLabel widget with an image file, respecting the widget's maximum sizes,
        while scaling the image down if needed (but not up), and keeping the aspect ratio
        Returns false if image loading failed
        '''
        pixmap = QPixmap(image_filename)
        if pixmap.isNull():
            return None
        
        # w = min(pixmap.width(), label.width())
        # h = min(pixmap.height(), label.height())
        pixmap = pixmap.scaledToWidth(label.width())
        # pixmap = pixmap.scaled(QtCore.QSize(w, h), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        return pixmap

    def QPixmapToImage(self, pixmap):
        width = pixmap.width()
        height = pixmap.height()
        image = pixmap.toImage()

        byteCount = image.bytesPerLine() * height
        data = image.constBits().asstring(byteCount)
        return Image.frombuffer('RGBA', (width, height), data, 'raw', 'BGRA', 0, 1)

    def ImageToQPixmap(self, image):
        return QPixmap.fromImage(ImageQt(image))

    def EnhanceImage(self, Pixmap, Property, value):
        CurrentImage = self.QPixmapToImage(Pixmap)
        AdjustedImage = Property(CurrentImage).enhance(float(value) / 100)
        return self.ImageToQPixmap(AdjustedImage)

    def AddColorSlider(self, layout):
        self.ColorSlider = QSlider(QtCore.Qt.Horizontal)
        self.ColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Saturation", self.ColorSlider)

        # Default value of the Color slider
        self.ColorSlider.setValue(100) 

        self.ColorSlider.valueChanged.connect(self.OnColorChanged)

    def OnColorChanged(self, value):
        self.Color = value
        self.UpdateImage()

    def AddBrightnessSlider(self, layout):
        self.BrightnessSlider = QSlider(QtCore.Qt.Horizontal)
        self.BrightnessSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Brightness", self.BrightnessSlider)

        # Default value of the brightness slider
        self.BrightnessSlider.setValue(100) 

        self.BrightnessSlider.valueChanged.connect(self.OnBrightnessChanged)

    def OnBrightnessChanged(self, value):
        self.Brightness = value
        self.UpdateImage()

    def AddContrastSlider(self, layout):
        self.ContrastSlider = QSlider(QtCore.Qt.Horizontal)
        self.ContrastSlider.setRange(0, 200) # 1 is original image, 0 is a solid grey image
        layout.addRow("Contrast", self.ContrastSlider)

        # Default value of the brightness slider
        self.ContrastSlider.setValue(100) 

        self.ContrastSlider.valueChanged.connect(self.OnContrastChanged)

    def OnContrastChanged(self, value):
        self.Contrast = value
        self.UpdateImage()

    def AddSharpnessSlider(self, layout):
        self.SharpnessSlider = QSlider(QtCore.Qt.Horizontal)
        self.SharpnessSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Sharpness", self.SharpnessSlider)

        # Default value of the Sharpness slider
        self.SharpnessSlider.setValue(100) 

        self.SharpnessSlider.valueChanged.connect(self.OnSharpnessChanged)

    def OnSharpnessChanged(self, value):
        self.Sharpness = value
        self.UpdateImage()

    def UpdateImage(self):
        Pixmap = self.welcome_pixmap
        Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Color, self.Color)
        Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Brightness, self.Brightness)
        Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Contrast, self.Contrast)
        Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Sharpness, self.Sharpness)
        self.logo_label.setPixmap(Pixmap)

def main():
    app = QApplication(sys.argv)

    # setup stylesheet
    # the default system in qdarkstyle uses qtpy environment variable
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    MainWindow = QtWidgets.QMainWindow()
    MainWindow.setWindowTitle('Photo Editor')
    MainWindow.resize(480, 320)
    gui = Gui(MainWindow)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()