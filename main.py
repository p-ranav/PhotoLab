from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, pyqtSlot, QPointF
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QGroupBox,
    QVBoxLayout,
    QFormLayout,
    QSlider,
    QToolBar,
    QToolButton
)
from PyQt6.QtGui import QPixmap
import sys
import qdarkstyle
from PIL import Image, ImageEnhance, ImageFilter
from PIL.ImageQt import ImageQt
from functools import partial
from QImageViewer import QtImageViewer
from QCropItem import QCropItem
from PyQt6.QtGui import QKeySequence
import pyqtgraph as pg
import cv2
from matplotlib import pyplot as plt
import numpy as np

def QImageToCvMat(incomingImage):
    '''  Converts a QImage into an opencv MAT format  '''

    incomingImage = incomingImage.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)

    width = incomingImage.width()
    height = incomingImage.height()

    ptr = incomingImage.bits()
    ptr.setsize(height * width * 4)
    arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
    return arr

class Gui(QtCore.QObject):
    def __init__(self, MainWindow):
        super().__init__()
        self.MainWindow = MainWindow

        self.image_viewer = QtImageViewer(self)

        # Set viewer's aspect ratio mode.
        # !!! ONLY applies to full image view.
        # !!! Aspect ratio always ignored when zoomed.
        #   Qt.AspectRatioMode.IgnoreAspectRatio: Fit to viewport.
        #   Qt.AspectRatioMode.KeepAspectRatio: Fit in viewport using aspect ratio.
        #   Qt.AspectRatioMode.KeepAspectRatioByExpanding: Fill viewport using aspect ratio.
        self.image_viewer.aspectRatioMode = Qt.AspectRatioMode.KeepAspectRatio
    
        # Set the viewer's scroll bar behaviour.
        #   Qt.ScrollBarPolicy.ScrollBarAlwaysOff: Never show scroll bar.
        #   Qt.ScrollBarPolicy.ScrollBarAlwaysOn: Always show scroll bar.
        #   Qt.ScrollBarPolicy.ScrollBarAsNeeded: Show scroll bar only when zoomed.
        self.image_viewer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.image_viewer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
        # Allow zooming by draggin a zoom box with the left mouse button.
        # !!! This will still emit a leftMouseButtonReleased signal if no dragging occured,
        #     so you can still handle left mouse button clicks in this way.
        #     If you absolutely need to handle a left click upon press, then
        #     either disable region zooming or set it to the middle or right button.
        self.image_viewer.regionZoomButton = Qt.MouseButton.LeftButton  # set to None to disable
    
        # Pop end of zoom stack (double click clears zoom stack).
        self.image_viewer.zoomOutButton = Qt.MouseButton.RightButton  # set to None to disable
    
        # Mouse wheel zooming.
        self.image_viewer.wheelZoomFactor = 1.25  # Set to None or 1 to disable
    
        # Allow panning with the middle mouse button.
        self.image_viewer.panButton = Qt.MouseButton.MiddleButton  # set to None to disable
        
        # Load an image file to be displayed (will popup a file dialog).
        self.image_viewer.open()
        self.image_viewer.OriginalImage = self.image_viewer.pixmap()

        # Compute image histogram
        img = self.QPixmapToImage(self.image_viewer.OriginalImage)
        r, g, b, a = img.split()
        r_histogram = r.histogram()
        g_histogram = g.histogram()
        b_histogram = b.histogram()
        
        # ITU-R 601-2 luma transform:
        luma_histogram = [sum(x) for x in zip([item * float(299/1000) for item in r_histogram],
                                              [item * float(587/1000) for item in g_histogram],
                                              [item * float(114/1000) for item in b_histogram])]

        # Create histogram plot
        self.ImageHistogramPlot = pg.plot()
        x = list(range(len(r_histogram)))
        self.ImageHistogramGraphRed = pg.PlotCurveItem(x = x, y = r_histogram, fillLevel=2, width = 1.0, brush=(255,0,0,80))
        self.ImageHistogramGraphGreen = pg.PlotCurveItem(x = x, y = g_histogram, fillLevel=2, width = 1.0, brush=(0,255,0,80))
        self.ImageHistogramGraphBlue = pg.PlotCurveItem(x = x, y = b_histogram, fillLevel=2, width = 1.0, brush=(0,0,255,80))
        self.ImageHistogramGraphLuma = pg.PlotCurveItem(x = x, y = luma_histogram, fillLevel=2, width = 1.0, brush=(255,255,255,80))
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphRed)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphGreen)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphBlue)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphLuma)

        # Create histogram dock
        HistogramDock = QtWidgets.QDockWidget("Histogram")
        HistogramDock.setMinimumWidth(200)
        HistogramDock.setMinimumHeight(300)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, HistogramDock)

        scroll = QtWidgets.QScrollArea()
        HistogramDock.setWidget(scroll)
        content = QtWidgets.QWidget()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        HistogramLayout = QtWidgets.QVBoxLayout(content)

        HistogramLayout.addWidget(self.ImageHistogramPlot)

        # Set the central widget of the Window. Widget will expand
        # to take up all the space in the window by default.
        self.MainWindow.setCentralWidget(self.image_viewer)

        dock = QtWidgets.QDockWidget("")
        dock.setMinimumSize(200, self.image_viewer.height())
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)

        scroll = QtWidgets.QScrollArea()
        dock.setWidget(scroll)
        content = QtWidgets.QWidget()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        lay = QtWidgets.QFormLayout(content)

        # Filter sliders
        filter_label = QLabel("Basic")
        lay.addWidget(filter_label)
        
        # Enhance sliders
        self.AddColorSlider(lay)
        self.AddBrightnessSlider(lay)
        self.AddContrastSlider(lay)
        self.AddSharpnessSlider(lay)

        # State of enhance sliders
        self.Color = 100
        self.Brightness = 100
        self.Contrast = 100
        self.Sharpness = 100

        # Filter sliders
        filter_label = QLabel("Filter")
        lay.addWidget(filter_label)

        self.AddGaussianBlurSlider(lay)

        # State of filter sliders
        self.GaussianBlurRadius = 0

        self.SliderTimerId = -1

        # Using a QToolBar object and a toolbar area
        ImageToolBar = QToolBar("Toolbar", self.MainWindow)
        self.MainWindow.addToolBar(Qt.LeftToolBarArea, ImageToolBar)

        self.CropToolButton = QToolButton(self.MainWindow)
        self.CropToolButton.setText("&Crop")
        self.CropToolButton.setIcon(QtGui.QIcon("crop.svg"))
        self.CropToolButton.setCheckable(True)
        self.CropToolButton.toggled.connect(self.OnCropToolButton)

        self.CropToolShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Shift+Alt+K"), self.MainWindow)
        self.CropToolShortcut.activated.connect(lambda: self.CropToolButton.toggle())

        self.SelectToolButton = QToolButton(self.MainWindow)
        self.SelectToolButton.setText("&Select")
        self.SelectToolButton.setIcon(QtGui.QIcon("select.svg"))
        self.SelectToolButton.setCheckable(True)
        self.SelectToolButton.toggled.connect(self.OnSelectToolButton)

        ImageToolBar.addWidget(self.CropToolButton)
        ImageToolBar.addWidget(self.SelectToolButton)

        self.MainWindow.showMaximized()

    def timerEvent(self, event):
        self.killTimer(self.SliderTimerId)
        self.SliderTimerId = -1
        self.UpdateImage()

    def UpdateImageWithDelay(self):
        if self.SliderTimerId != -1:
            self.killTimer(self.SliderTimerId)
            
        # https://stackoverflow.com/questions/43152489/pyqt5-qslider-valuechanged-event-with-delay
        self.SliderTimerId = self.startTimer(250)

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

    def ApplyGaussianBlur(self, Pixmap, value):
        CurrentImage = self.QPixmapToImage(Pixmap)
        AdjustedImage = CurrentImage.filter(ImageFilter.GaussianBlur(radius=float(self.GaussianBlurRadius / 100)))
        return self.ImageToQPixmap(AdjustedImage)

    def AddColorSlider(self, layout):
        self.ColorSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.ColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Saturation", self.ColorSlider)

        # Default value of the Color slider
        self.ColorSlider.setValue(100) 

        self.ColorSlider.valueChanged.connect(self.OnColorChanged)

    def OnColorChanged(self, value):
        self.Color = value
        self.UpdateImageWithDelay()

    def AddBrightnessSlider(self, layout):
        self.BrightnessSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.BrightnessSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Brightness", self.BrightnessSlider)

        # Default value of the brightness slider
        self.BrightnessSlider.setValue(100) 

        self.BrightnessSlider.valueChanged.connect(self.OnBrightnessChanged)

    def OnBrightnessChanged(self, value):
        self.Brightness = value
        self.UpdateImageWithDelay()

    def AddContrastSlider(self, layout):
        self.ContrastSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.ContrastSlider.setRange(0, 200) # 1 is original image, 0 is a solid grey image
        layout.addRow("Contrast", self.ContrastSlider)

        # Default value of the brightness slider
        self.ContrastSlider.setValue(100) 

        self.ContrastSlider.valueChanged.connect(self.OnContrastChanged)

    def OnContrastChanged(self, value):
        self.Contrast = value
        self.UpdateImageWithDelay()

    def AddSharpnessSlider(self, layout):
        self.SharpnessSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.SharpnessSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Sharpness", self.SharpnessSlider)

        # Default value of the Sharpness slider
        self.SharpnessSlider.setValue(100) 

        self.SharpnessSlider.valueChanged.connect(self.OnSharpnessChanged)

    def OnSharpnessChanged(self, value):
        self.Sharpness = value
        self.UpdateImageWithDelay()

    def AddGaussianBlurSlider(self, layout):
        self.GaussianBlurSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.GaussianBlurSlider.setRange(0, 2000)
        layout.addRow("Gaussian Blur", self.GaussianBlurSlider)
        self.GaussianBlurSlider.valueChanged.connect(self.OnGaussianBlurChanged)

    def OnGaussianBlurChanged(self, value):
        self.GaussianBlurRadius = value
        self.UpdateImageWithDelay()

    def OnSharpnessChanged(self, value):
        self.Sharpness = value
        self.UpdateImageWithDelay()

    def UpdateImage(self):
        Pixmap = self.image_viewer.OriginalImage
        Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Color, self.Color)
        Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Brightness, self.Brightness)
        Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Contrast, self.Contrast)
        Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Sharpness, self.Sharpness)
        if self.GaussianBlurRadius > 0:
            Pixmap = self.ApplyGaussianBlur(Pixmap, float(self.GaussianBlurRadius / 100))
        self.image_viewer.setImage(Pixmap)
        self.UpdateHistogramPlot()

    def OnCropToolButton(self, checked):
        if checked:
            self.image_viewer._isCropping = True
        else:
            # Remove the crop path item
            self.image_viewer._isCropping = False

    def OnSelectToolButton(self, checked):
        if checked:
            self.image_viewer._isSelecting = True
        else:
            # Remove the crop path item
            self.image_viewer._isSelecting = False

    def UpdateHistogramPlot(self):
        # Compute image histogram
        img = self.QPixmapToImage(self.image_viewer.pixmap())
        r, g, b, a = img.split()
        r_histogram = r.histogram()
        g_histogram = g.histogram()
        b_histogram = b.histogram()

        # ITU-R 601-2 luma transform:
        luma_histogram = [sum(x) for x in zip([item * float(299/1000) for item in r_histogram],
                                              [item * float(587/1000) for item in g_histogram],
                                              [item * float(114/1000) for item in b_histogram])]

        # Update histogram plot
        self.ImageHistogramGraphRed.setData(y=r_histogram)
        self.ImageHistogramGraphGreen.setData(y=g_histogram)
        self.ImageHistogramGraphBlue.setData(y=b_histogram)
        self.ImageHistogramGraphLuma.setData(y=luma_histogram)

def main():
    app = QApplication(sys.argv)

    ## setup stylesheet
    ## the default system in qdarkstyle uses qtpy environment variable
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    MainWindow = QtWidgets.QMainWindow()
    MainWindow.setWindowTitle('Photo Editor')
    gui = Gui(MainWindow)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()