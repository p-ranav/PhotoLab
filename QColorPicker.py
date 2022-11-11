# ------------------------------------- #
#                                       #
# Modern Color Picker by Tom F.         #
# Edited by GiorgosXou for Qt6 Support. #
#                                       #
# Version 1.3                           #
# made with Qt Creator & PyQt5          #
#                                       #
# ------------------------------------- #

import sys
import colorsys

from PyQt6.QtCore import (QPoint, Qt, pyqtSignal)
from PyQt6.QtGui import QColor, QMouseEvent
from PyQt6.QtWidgets import (QApplication, QWidget, QMainWindow)


from Ui_ColorPicker import Ui_ColorPicker as Ui_Main


class QColorPicker(QWidget):

    colorChanged = pyqtSignal()

    def __init__(self, *args, **kwargs):

        # Extract Initial Color out of kwargs
        rgb = kwargs.pop("rgb", None)
        hsv = kwargs.pop("hsv", None)
        hex = kwargs.pop("hex", None)

        super(QColorPicker, self).__init__(*args, **kwargs)

        # Call UI Builder function
        self.ui = Ui_Main()
        self.ui.setupUi(self)

        # Connect update functions
        self.ui.hue.mouseMoveEvent = self.moveHueSelector
        self.ui.hue.mousePressEvent = self.moveHueSelector
        self.ui.red.textEdited.connect(self.rgbChanged)
        self.ui.green.textEdited.connect(self.rgbChanged)
        self.ui.blue.textEdited.connect(self.rgbChanged)
        self.ui.hex.textEdited.connect(self.hexChanged)

        # Connect selector moving function
        self.ui.black_overlay.mouseMoveEvent = self.moveSVSelector
        self.ui.black_overlay.mousePressEvent = self.moveSVSelector

        if rgb:
            self.setRGB(rgb)
        elif hsv:
            self.setHSV(hsv)
        elif hex:
            self.setHex(hex)
        else:
            self.setRGB((0,0,0))


    ## Main Functions ##
    def getHSV(self, hrange=100, svrange=100):
        h,s,v = self.color
        return (h*(hrange/100.0), s*(svrange/100.0), v*(svrange/100.0))

    def getRGB(self, range=255):
        r,g,b = self.i(self.ui.red.text()), self.i(self.ui.green.text()), self.i(self.ui.blue.text())
        return (r*(range/255.0),g*(range/255.0),b*(range/255.0))

    def getHex(self,ht=False):
        rgb = (self.i(self.ui.red.text()), self.i(self.ui.green.text()), self.i(self.ui.blue.text()))
        if ht: return "#" + self.rgb2hex(rgb)
        else: return self.rgb2hex(rgb)


    ## Update Functions ##
    def hsvChanged(self):
        h,s,v = (100 - self.ui.hue_selector.y() / 1.85, (self.ui.selector.x() + 6) / 2.0, (194 - self.ui.selector.y()) / 2.0)
        r,g,b = self.hsv2rgb(h,s,v)
        self.color = (h,s,v)
        self._setRGB((r,g,b))
        self._setHex(self.hsv2hex(self.color))
        self.ui.color_vis.setStyleSheet(f"background-color: rgb({r},{g},{b})")
        self.ui.color_view.setStyleSheet(f"border-radius: 5px;background-color: qlineargradient(x1:1, x2:0, stop:0 hsl({h}%,100%,50%), stop:1 #fff);")
        self.colorChanged.emit()

    def rgbChanged(self):
        r,g,b = self.i(self.ui.red.text()), self.i(self.ui.green.text()), self.i(self.ui.blue.text())
        self.color = self.rgb2hsv(r,g,b)
        self._setHSV(self.color)
        self._setHex(self.rgb2hex((r,g,b)))
        self.ui.color_vis.setStyleSheet(f"background-color: rgb({r},{g},{b})")
        self.colorChanged.emit()

    def hexChanged(self):
        hex = self.ui.hex.text()
        r,g,b = self.hex2rgb(hex)
        self.color = self.hex2hsv(hex)
        self._setHSV(self.color)
        self._setRGB(self.hex2rgb(hex))
        self.ui.color_vis.setStyleSheet(f"background-color: rgb({r},{g},{b})")
        self.colorChanged.emit()


    ## internal setting functions ##
    def _setRGB(self, c):
        r,g,b = c
        self.ui.red.setText(str(self.i(r)))
        self.ui.green.setText(str(self.i(g)))
        self.ui.blue.setText(str(self.i(b)))

    def _setHSV(self, c):
        self.ui.hue_selector.move(7, int((100 - c[0]) * 1.85))
        self.ui.color_view.setStyleSheet(f"border-radius: 5px;background-color: qlineargradient(x1:1, x2:0, stop:0 hsl({c[0]}%,100%,50%), stop:1 #fff);")
        self.ui.selector.move(int(c[1] * 2 - 6), int((200 - c[2] * 2) - 6))

    def _setHex(self, c):
        self.ui.hex.setText(c)


    ## external setting functions ##
    def setRGB(self, c):
        self._setRGB(c)
        self.rgbChanged()

    def setHSV(self, c):
        self._setHSV(c)
        self.hsvChanged()

    def setHex(self, c):
        self._setHex(c)
        self.hexChanged()


    ## Color Utility ##
    def hsv2rgb(self, h_or_color, s = 0, v = 0):
        if type(h_or_color).__name__ == "tuple": h,s,v = h_or_color
        else: h = h_or_color
        r,g,b = colorsys.hsv_to_rgb(h / 100.0, s / 100.0, v / 100.0)
        return self.clampRGB((r * 255, g * 255, b * 255))

    def rgb2hsv(self, r_or_color, g = 0, b = 0):
        if type(r_or_color).__name__ == "tuple": r,g,b = r_or_color
        else: r = r_or_color
        h,s,v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        return (h * 100, s * 100, v * 100)

    def hex2rgb(self, hex):
        if len(hex) < 6: hex += "0"*(6-len(hex))
        elif len(hex) > 6: hex = hex[0:6]
        rgb = tuple(int(hex[i:i+2], 16) for i in (0,2,4))
        return rgb

    def rgb2hex(self, r_or_color, g = 0, b = 0):
        if type(r_or_color).__name__ == "tuple": r,g,b = r_or_color
        else: r = r_or_color
        hex = '%02x%02x%02x' % (int(r),int(g),int(b))
        return hex

    def hex2hsv(self, hex):
        return self.rgb2hsv(self.hex2rgb(hex))

    def hsv2hex(self, h_or_color, s = 0, v = 0):
        if type(h_or_color).__name__ == "tuple": h,s,v = h_or_color
        else: h = h_or_color
        return self.rgb2hex(self.hsv2rgb(h,s,v))


    # selector move function
    def moveSVSelector(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            pos = event.position()
            if pos.x() < 0: pos.setX(0)
            if pos.y() < 0: pos.setY(0)
            if pos.x() > 200: pos.setX(200)
            if pos.y() > 200: pos.setY(200)
            self.ui.selector.move(int(pos.x() - 6), int(pos.y() - 6))
            self.hsvChanged()

    def moveHueSelector(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            pos = event.position().y() - 7
            if pos < 0: pos = 0
            if pos > 185: pos = 185
            self.ui.hue_selector.move(7, int(pos))
            self.hsvChanged()

    def i(self, text):
        try: return int(text)
        except: return 0

    def clampRGB(self, rgb):
        r,g,b = rgb
        if r<0.0001: r=0
        if g<0.0001: g=0
        if b<0.0001: b=0
        if r>255: r=255
        if g>255: g=255
        if b>255: b=255
        return (r,g,b)      