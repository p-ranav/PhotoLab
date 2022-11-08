from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QGroupBox,
    QVBoxLayout,
    QFormLayout,
    QSlider,
)
from PyQt5.QtGui import QPixmap
import sys
import qdarkstyle
import cv2
import numpy as np
from PIL import Image, ImageEnhance

class Gui(QtCore.QObject):
    def __init__(self, MainWindow):
        super().__init__()
        self.MainWindow = MainWindow

        self.form = QGroupBox()
        self.form_layout = QVBoxLayout()

        self.logo_label = QLabel()
        self.welcome_pixmap = self.set_label_image(self.logo_label, 'welcome.jpg')
        self.welcome_pixmap_original_aspect_ratio = self.welcome_pixmap.width() / self.welcome_pixmap.height()
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

        # Tone sliders
        tone_label = QLabel("Tone")
        lay.addWidget(tone_label)

        # Brightness
        self.CurrentBrightness = 0
        self.AddBrightnessSlider(lay)
        self.AddContrastSlider(lay)

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
        
        w = min(pixmap.width(), label.maximumWidth())
        h = min(pixmap.height(), label.maximumHeight())
        pixmap = pixmap.scaled(QtCore.QSize(w, h), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        return pixmap

    def QPixmapToNumpy(self, pixmap):
        channels_count = 4
        width = pixmap.width()
        height = pixmap.height()
        image = pixmap.toImage()
        s = image.bits().asstring(width * height * channels_count)
        arr = np.frombuffer(s, dtype=np.uint8).reshape((height, width, channels_count)) 
        return arr

    def NumpyToQPixmap(self, arr):
        height, width, channel = arr.shape
        print(height, width, channel)
        bytesPerLine = channel * width
        qImg = QtGui.QImage(arr.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
        return QPixmap(qImg)

    def AddBrightnessSlider(self, layout):
        self.BrightnessSlider = QSlider(QtCore.Qt.Horizontal)
        self.BrightnessSlider.setRange(0, 100)
        layout.addRow("Brightness", self.BrightnessSlider)
        self.BrightnessSlider.valueChanged.connect(self.OnBrightnessChanged)

    def ChangeBrightness(self, img, value=30):
        shape = img.shape
        alpha = img[...,3]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        lim = 255 - value
        v[v > lim] = 255
        v[v <= lim] += value

        final_hsv = cv2.merge((h, s, v))
        img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2RGB)

        return img

    def OnBrightnessChanged(self, val):
        CurrentImage = self.QPixmapToNumpy(self.welcome_pixmap)
        CurrentImage = self.ChangeBrightness(CurrentImage, val)
        CurrentImageAsPixMap = self.NumpyToQPixmap(CurrentImage)
        self.logo_label.setPixmap(CurrentImageAsPixMap)

    def AddContrastSlider(self, layout):
        self.ContrastSlider = QSlider(QtCore.Qt.Horizontal)
        self.ContrastSlider.setRange(-200, 200)
        layout.addRow("Contrast", self.ContrastSlider)
        self.ContrastSlider.valueChanged.connect(self.OnContrastChanged)

    def ChangeContrast(self, img, Contrast):
        print(Contrast)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        Contrast = int((Contrast - 0) * (127 - (-127)) / (254 - 0) + (-127))
        Alpha = float(131 * (Contrast + 127)) / (127 * (131 - Contrast))
        Gamma = 127 * (1 - Alpha)
        img = cv2.addWeighted(img, Alpha, img, 0, Gamma)
        return img

    def OnContrastChanged(self, val):
        CurrentImage = self.QPixmapToNumpy(self.welcome_pixmap)
        CurrentImage = self.ChangeContrast(CurrentImage, val)
        CurrentImageAsPixMap = self.NumpyToQPixmap(CurrentImage)
        self.logo_label.setPixmap(CurrentImageAsPixMap)

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