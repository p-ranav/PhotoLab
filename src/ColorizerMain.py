import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ColorizerDraw import GUIDraw
from ColorizerGamut import GUIGamut
from ColorizerPalette import GUIPalette
from ColorizerVis import GUI_VIS


class IColoriTUI(QWidget):
    def __init__(self, parent, viewer, alphaChannel, color_model, im_bgr=None, load_size=224, win_size=256, device='cpu'):
        # draw the layout
        QWidget.__init__(self, parent)

        self.viewer = viewer
        self.alphaChannel = alphaChannel

        # main layout
        mainLayout = QHBoxLayout()
        self.setLayout(mainLayout)

        # gamut layout
        self.gamutWidget = GUIGamut(gamut_size=110)
        gamutLayout = self.AddWidget(self.gamutWidget, 'ab Color Gamut')
        colorLayout = QVBoxLayout()

        colorLayout.addLayout(gamutLayout)
        mainLayout.addLayout(colorLayout)

        # palette
        self.usedPalette = GUIPalette(grid_sz=(10, 1))
        upLayout = self.AddWidget(self.usedPalette, 'Recently used colors')
        colorLayout.addLayout(upLayout)

        self.colorPush = QPushButton()  # to visualize the selected color
        self.colorPush.setFixedWidth(self.usedPalette.width())
        self.colorPush.setFixedHeight(25)
        self.colorPush.setStyleSheet("background-color: grey")
        colorPushLayout = self.AddWidget(self.colorPush, 'Current Color')
        colorLayout.addLayout(colorPushLayout)
        colorLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # drawPad layout
        drawPadLayout = QVBoxLayout()
        mainLayout.addLayout(drawPadLayout)
        self.drawWidget = GUIDraw(color_model, load_size=load_size, win_size=win_size, device=device)
        drawPadLayout = self.AddWidget(self.drawWidget, 'Drawing Pad')
        mainLayout.addLayout(drawPadLayout)

        drawPadMenu = QHBoxLayout()

        self.bGray = QCheckBox("&Gray")
        self.bGray.setToolTip('show gray-scale image')

        self.bLoad = QPushButton('&Load')
        self.bLoad.setToolTip('load an input image')
        self.bSave = QPushButton("&Save")
        self.bSave.setToolTip('Save the current result.')

        drawPadMenu.addWidget(self.bGray)
        # drawPadMenu.addWidget(self.bLoad)
        drawPadMenu.addWidget(self.bSave)

        drawPadLayout.addLayout(drawPadMenu)
        self.visWidget = GUI_VIS(win_size=win_size, scale=win_size / float(load_size))
        visWidgetLayout = self.AddWidget(self.visWidget, 'Colorized Result')
        mainLayout.addLayout(visWidgetLayout)

        self.bRestart = QPushButton("&Restart")
        self.bRestart.setToolTip('Restart the system')

        self.bQuit = QPushButton("&Quit")
        self.bQuit.setToolTip('Quit the system.')
        visWidgetMenu = QHBoxLayout()
        visWidgetMenu.addWidget(self.bRestart)

        self.setStyleSheet('''
            background-color: rgb(22, 22, 22);
        ''')
        buttons = [self.bSave, self.bRestart, self.bQuit]
        for b in buttons:
            b.setStyleSheet('''
                background-color: rgb(44, 44, 44);
                height: 30px;
                width: 100px;
            ''')

        visWidgetMenu.addWidget(self.bQuit)
        visWidgetLayout.addLayout(visWidgetMenu)

        self.drawWidget.update()
        self.visWidget.update()
        # self.colorPush.clicked.connect(self.drawWidget.change_color)

        # color indicator
        self.drawWidget.update_color.connect(self.colorPush.setStyleSheet)

        # update result
        self.drawWidget.update_result.connect(self.visWidget.update_result) # pyqt5

        # update gamut
        self.drawWidget.update_gammut.connect(self.gamutWidget.set_gamut) # pyqt5
        self.drawWidget.update_ab.connect(self.gamutWidget.set_ab)
        self.gamutWidget.update_color.connect(self.drawWidget.set_color)

        # connect palette
        self.drawWidget.used_colors.connect(self.usedPalette.set_colors) # pyqt5
        self.usedPalette.update_color.connect(self.drawWidget.set_color)
        self.usedPalette.update_color.connect(self.gamutWidget.set_ab)
        
        # menu events
        self.bGray.setChecked(True)
        self.bRestart.clicked.connect(self.reset)
        self.bQuit.clicked.connect(self.quit)
        self.bGray.toggled.connect(self.enable_gray)
        self.bSave.clicked.connect(self.save)
        self.bLoad.clicked.connect(self.load)

        self.start_t = time.time()

        if im_bgr is not None:
            self.drawWidget.init_result(im_bgr)
        print('UI initialized')

    def AddWidget(self, widget, title):
        widgetLayout = QVBoxLayout()
        widgetBox = QGroupBox()
        widgetBox.setTitle(title)
        vbox_t = QVBoxLayout()
        vbox_t.addWidget(widget)
        widgetBox.setLayout(vbox_t)
        widgetLayout.addWidget(widgetBox)

        return widgetLayout

    def nextImage(self):
        self.drawWidget.nextImage()

    def reset(self):
        # self.start_t = time.time()
        print('============================reset all=========================================')
        self.visWidget.reset()
        self.gamutWidget.reset()
        self.usedPalette.reset()
        self.drawWidget.reset()
        self.update()
        self.colorPush.setStyleSheet("background-color: grey")

    def enable_gray(self):
        self.drawWidget.enable_gray()

    def quit(self):
        print('time spent = %3.3f' % (time.time() - self.start_t))
        self.close()

    def ImageToQPixmap(self, image):
        from PyQt6.QtGui import QPixmap
        from PIL.ImageQt import ImageQt
        return QPixmap.fromImage(ImageQt(image))

    def save(self):
        print('time spent = %3.3f' % (time.time() - self.start_t))
        self.drawWidget.save_result()

        import cv2
        import numpy as np
        from PIL import Image

        h, w, _ = self.drawWidget.im_full.shape

        output = self.visWidget.result
        output = cv2.resize(output, (w, h))
        output = np.dstack((output, self.alphaChannel))
        output = Image.fromarray(output.astype(np.uint8))
        updatedPixmap = self.ImageToQPixmap(output)
        self.viewer.setImage(updatedPixmap, True, "Interactive Colorization")

        self.close()
        self.destroyed.emit()

    def load(self):
        self.drawWidget.load_image()

    def change_color(self):
        print('change color')
        self.drawWidget.change_color(use_suggest=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_R:
            self.reset()

        if event.key() == Qt.Key.Key_Q:
            self.save()
            self.quit()

        if event.key() == Qt.Key.Key_S:
            self.save()

        if event.key() == Qt.Key.Key_G:
            self.bGray.toggle()

        if event.key() == Qt.Key.Key_L:
            self.load()

    def closeEvent(self, event):
        self.close()
        event.accept()
        self.destroyed.emit()