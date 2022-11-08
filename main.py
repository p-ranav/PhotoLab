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
from collapsible_box import CollapsibleBox
import random
import qdarkstyle

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
        vlay = QtWidgets.QVBoxLayout(content)

        # Tone
        tone_box = CollapsibleBox("Tone")
        vlay.addWidget(tone_box)
        lay = QtWidgets.QFormLayout()
        tone_sliders = ["Exposure", "Contrast", "Highlights", "Shadows", "Whites", "Blacks"]
        for j in range(6):
            slider = QSlider(QtCore.Qt.Horizontal)
            lay.addRow(tone_sliders[j], slider)
        tone_box.setContentLayout(lay)
        tone_box.resize(tone_box.width() + 100, tone_box.height())

        vlay.addStretch()

        self.MainWindow.show()

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