from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QSlider,
    QToolBar,
    QToolButton,
    QFileDialog,
    QProgressDialog
)
from PyQt6.QtGui import QPixmap
import sys
import qdarkstyle

from QImageViewer import QtImageViewer
from PyQt6.QtGui import QKeySequence
import pyqtgraph as pg
import numpy as np
from QColorPicker import QColorPicker
import os
from QFlowLayout import QFlowLayout
from PIL import Image, ImageEnhance, ImageFilter
from PIL.ImageQt import ImageQt
from FileUtils import merge_files
from QProgressBarThread import QProgressBarThread

def free_gpu_cache():
    import torch
    from GPUtil import showUtilization as gpu_usage
    from numba import cuda

    print("Initial GPU Usage")
    gpu_usage()                             

    torch.cuda.empty_cache()

    #cuda.select_device(0)
    #cuda.close()
    #cuda.select_device(0)

    print("GPU Usage after emptying the cache")
    gpu_usage()

class Gui(QtCore.QObject):
    def __init__(self, MainWindow):
        super().__init__()
        self.MainWindow = MainWindow

        ##############################################################################################
        ##############################################################################################
        # Create Histogram
        ##############################################################################################
        ##############################################################################################

        # Compute image histogram
        r_histogram = []
        g_histogram = []
        b_histogram = []
        
        # ITU-R 601-2 luma transform:
        luma_histogram = []

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

        ##############################################################################################
        ##############################################################################################
        # Histogram Dock
        ##############################################################################################
        ##############################################################################################

        # Create histogram dock
        HistogramDock = QtWidgets.QDockWidget("Histogram")
        # TODO: Change these numbers on dock resize
        # These are just the starting value
        HistogramDock.setMinimumWidth(100)
        HistogramDock.setMinimumHeight(220)
        HistogramDock.setMaximumHeight(220)
        HistogramDock.setMaximumWidth(380)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, HistogramDock)

        content = QtWidgets.QWidget()
        HistogramLayout = QtWidgets.QVBoxLayout(content)
        HistogramDock.setWidget(content)

        HistogramLayout.addWidget(self.ImageHistogramPlot)

        ##############################################################################################
        ##############################################################################################
        # Color Picker
        ##############################################################################################
        ##############################################################################################

        # Create color picker dock
        ColorPickerDock = QtWidgets.QDockWidget("ColorPicker")
        ColorPickerDock.setMinimumWidth(100)
        ColorPickerDock.setMinimumHeight(100)
        ColorPickerDock.setMaximumHeight(260)
        ColorPickerDock.setMaximumWidth(380)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, ColorPickerDock)

        content = QtWidgets.QWidget()
        ColorPickerLayout = QtWidgets.QVBoxLayout(content)
        ColorPickerDock.setWidget(content)

        self.color_picker = QColorPicker(content, rgb=(173, 36, 207))
        ColorPickerLayout.addWidget(self.color_picker)

        ##############################################################################################
        ##############################################################################################
        # Adjustment Sliders
        ##############################################################################################
        ##############################################################################################

        dock = QtWidgets.QDockWidget("")
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
        self.AddRedColorSlider(lay)
        self.AddGreenColorSlider(lay)
        self.AddBlueColorSlider(lay)
        self.AddColorSlider(lay)
        self.AddBrightnessSlider(lay)
        self.AddContrastSlider(lay)
        self.AddSharpnessSlider(lay)

        # State of enhance sliders
        self.RedFactor = 100
        self.GreenFactor = 100
        self.BlueFactor = 100
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

        #self.SliderTimerId = -1
        ## create the shared queue
        #self.sliderQueue = Queue()

        #self.sliderQueueConsumeTimer = QtCore.QTimer()
        #self.sliderQueueConsumeTimer.setInterval(2500)
        #self.sliderQueueConsumeTimer.timeout.connect(self.sliderConsumer)
        #self.sliderQueueConsumeTimer.start()

        ##############################################################################################
        ##############################################################################################
        # Keyboard Shortcuts
        ##############################################################################################
        ##############################################################################################

        self.OpenShortcut = QtGui.QShortcut(QKeySequence("Ctrl+O"), self.MainWindow)
        self.OpenShortcut.activated.connect(self.OnOpen)

        self.PasteShortcut = QtGui.QShortcut(QKeySequence("Ctrl+V"), self.MainWindow)
        self.PasteShortcut.activated.connect(self.OnPaste)

        self.SaveShortcut = QtGui.QShortcut(QKeySequence("Ctrl+S"), self.MainWindow)
        self.SaveShortcut.activated.connect(self.OnSave)

        self.SaveAsShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Shift+S"), self.MainWindow)
        self.SaveAsShortcut.activated.connect(self.OnSaveAs)

        self.UndoShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Z"), self.MainWindow)
        self.UndoShortcut.activated.connect(self.OnUndo)

        ##############################################################################################
        ##############################################################################################
        # Toolbar
        ##############################################################################################
        ##############################################################################################

        # Using a QToolBar object and a toolbar area
        ImageToolBar = QToolBar("Toolbar", self.MainWindow)

        ##############################################################################################
        ##############################################################################################
        # Cursor Tool
        ##############################################################################################
        ##############################################################################################

        self.CursorToolButton = QToolButton(self.MainWindow)
        # self.CursorToolButton.setIconSize(QtCore.QSize(32, 32))
        self.CursorToolButton.setText("&Cursor")
        self.CursorToolButton.setToolTip("Cursor")
        self.CursorToolButton.setIcon(QtGui.QIcon("icons/cursor.svg"))
        self.CursorToolButton.setCheckable(True)
        self.CursorToolButton.toggled.connect(self.OnCursorToolButton)

        ##############################################################################################
        ##############################################################################################
        # Color Picker Tool
        ##############################################################################################
        ##############################################################################################

        self.ColorPickerToolButton = QToolButton(self.MainWindow)
        self.ColorPickerToolButton.setText("&Color Picker")
        self.ColorPickerToolButton.setToolTip("Color Picker")
        self.ColorPickerToolButton.setIcon(QtGui.QIcon("icons/color_picker.svg"))
        self.ColorPickerToolButton.setCheckable(True)
        self.ColorPickerToolButton.toggled.connect(self.OnColorPickerToolButton)

        ##############################################################################################
        ##############################################################################################
        # Paint Tool
        ##############################################################################################
        ##############################################################################################

        self.PaintToolButton = QToolButton(self.MainWindow)
        self.PaintToolButton.setText("&Paint")
        self.PaintToolButton.setToolTip("Paint")
        self.PaintToolButton.setIcon(QtGui.QIcon("icons/paint.svg"))
        self.PaintToolButton.setCheckable(True)
        self.PaintToolButton.toggled.connect(self.OnPaintToolButton)

        ##############################################################################################
        ##############################################################################################
        # Fill Tool
        ##############################################################################################
        ##############################################################################################

        self.FillToolButton = QToolButton(self.MainWindow)
        self.FillToolButton.setText("&Fill")
        self.FillToolButton.setToolTip("Fill")
        self.FillToolButton.setIcon(QtGui.QIcon("icons/fill.svg"))
        self.FillToolButton.setCheckable(True)
        self.FillToolButton.toggled.connect(self.OnFillToolButton)

        ##############################################################################################
        ##############################################################################################
        # Crop Tool
        ##############################################################################################
        ##############################################################################################

        self.CropToolButton = QToolButton(self.MainWindow)
        self.CropToolButton.setText("&Crop")
        self.CropToolButton.setIcon(QtGui.QIcon("icons/crop.svg"))
        self.CropToolButton.setToolTip("Basic Crop")
        self.CropToolButton.setCheckable(True)
        self.CropToolButton.toggled.connect(self.OnCropToolButton)

        self.CropToolShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Shift+Alt+K"), self.MainWindow)
        self.CropToolShortcut.activated.connect(lambda: self.CropToolButton.toggle())

        ##############################################################################################
        ##############################################################################################
        # Select + Crop Tool
        ##############################################################################################
        ##############################################################################################

        self.SelectToolButton = QToolButton(self.MainWindow)
        self.SelectToolButton.setText("&Select")
        self.SelectToolButton.setToolTip("Path Crop")
        self.SelectToolButton.setIcon(QtGui.QIcon("icons/select.svg"))
        self.SelectToolButton.setCheckable(True)
        self.SelectToolButton.toggled.connect(self.OnSelectToolButton)

        ##############################################################################################
        ##############################################################################################
        # Spot Removal Tool
        ##############################################################################################
        ##############################################################################################

        self.SpotRemovalToolButton = QToolButton(self.MainWindow)
        self.SpotRemovalToolButton.setText("&Spot Removal")
        self.SpotRemovalToolButton.setToolTip("Spot Removal")
        self.SpotRemovalToolButton.setIcon(QtGui.QIcon("icons/spot_removal.svg"))
        self.SpotRemovalToolButton.setCheckable(True)
        self.SpotRemovalToolButton.toggled.connect(self.OnSpotRemovalToolButton)

        ##############################################################################################
        ##############################################################################################
        # Blur Tool
        ##############################################################################################
        ##############################################################################################

        self.BlurToolButton = QToolButton(self.MainWindow)
        self.BlurToolButton.setText("&Blur")
        self.BlurToolButton.setToolTip("Blur")
        self.BlurToolButton.setIcon(QtGui.QIcon("icons/blur.svg"))
        self.BlurToolButton.setCheckable(True)
        self.BlurToolButton.toggled.connect(self.OnBlurToolButton)

        ##############################################################################################
        ##############################################################################################
        # Background Removal Tool
        ##############################################################################################
        ##############################################################################################

        self.BackgroundRemovalToolButton = QToolButton(self.MainWindow)
        self.BackgroundRemovalToolButton.setText("&Background Removal")
        self.BackgroundRemovalToolButton.setToolTip("Background Removal")
        self.BackgroundRemovalToolButton.setIcon(QtGui.QIcon("icons/background_removal.svg"))
        self.BackgroundRemovalToolButton.setCheckable(True)
        self.BackgroundRemovalToolButton.toggled.connect(self.OnBackgroundRemovalToolButton)

        ##############################################################################################
        ##############################################################################################
        # Human Segmentation Tool
        ##############################################################################################
        ##############################################################################################

        self.HumanSegmentationToolButton = QToolButton(self.MainWindow)
        self.HumanSegmentationToolButton.setText("&Human Segmentation")
        self.HumanSegmentationToolButton.setToolTip("Human Segmentation")
        self.HumanSegmentationToolButton.setIcon(QtGui.QIcon("icons/human_segmentation.svg"))
        self.HumanSegmentationToolButton.setCheckable(True)
        self.HumanSegmentationToolButton.toggled.connect(self.OnHumanSegmentationToolButton)

        ##############################################################################################
        ##############################################################################################
        # Colorizer Tool
        ##############################################################################################
        ##############################################################################################

        self.ColorizerToolButton = QToolButton(self.MainWindow)
        self.ColorizerToolButton.setText("&Colorizer")
        self.ColorizerToolButton.setToolTip("Colorizer")
        self.ColorizerToolButton.setIcon(QtGui.QIcon("icons/colorizer.svg"))
        self.ColorizerToolButton.setCheckable(True)
        self.ColorizerToolButton.toggled.connect(self.OnColorizerToolButton)

        ##############################################################################################
        ##############################################################################################
        # Super-Resolution Tool
        ##############################################################################################
        ##############################################################################################

        self.SuperResolutionToolButton = QToolButton(self.MainWindow)
        self.SuperResolutionToolButton.setText("&Super Resolution")
        self.SuperResolutionToolButton.setToolTip("Super-Resolution")
        self.SuperResolutionToolButton.setIcon(QtGui.QIcon("icons/super_resolution.svg"))
        self.SuperResolutionToolButton.setCheckable(True)
        self.SuperResolutionToolButton.toggled.connect(self.OnSuperResolutionToolButton)

        ##############################################################################################
        ##############################################################################################
        # Anime GAN v2 Tool
        # https://github.com/bryandlee/animegan2-pytorch
        ##############################################################################################
        ##############################################################################################

        self.AnimeGanV2ToolButton = QToolButton(self.MainWindow)
        self.AnimeGanV2ToolButton.setText("&Anime GAN v2")
        self.AnimeGanV2ToolButton.setToolTip("Anime GAN v2")
        self.AnimeGanV2ToolButton.setIcon(QtGui.QIcon("icons/anime.svg"))
        self.AnimeGanV2ToolButton.setCheckable(True)
        self.AnimeGanV2ToolButton.toggled.connect(self.OnAnimeGanV2ToolButton)

        ##############################################################################################
        ##############################################################################################
        # Eraser Tool
        ##############################################################################################
        ##############################################################################################

        self.EraserToolButton = QToolButton(self.MainWindow)
        self.EraserToolButton.setText("&Eraser")
        self.EraserToolButton.setToolTip("Eraser")
        self.EraserToolButton.setIcon(QtGui.QIcon("icons/eraser.svg"))
        self.EraserToolButton.setCheckable(True)
        self.EraserToolButton.toggled.connect(self.OnEraserToolButton)

        ##############################################################################################
        ##############################################################################################
        # Toolbar
        ##############################################################################################
        ##############################################################################################

        self.tools = {
            "cursor": {
                "tool": "CursorToolButton",
                "var": '_isCursor'
            },
            "color_picker": {
                "tool": "ColorPickerToolButton",
                "var": '_isColorPicking'
            },
            "paint": {
                "tool": "PaintToolButton",
                "var": '_isPainting'
            },
            "fill": {
                "tool": "FillToolButton",
                "var": '_isFilling'
            },
            "crop": {
                "tool": "CropToolButton",
                "var": '_isCropping'
            },
            "select": {
                "tool": "SelectToolButton",
                "var": '_isSelecting',
                "destructor": 'exitSelect'
            },
            "spot_removal": {
                "tool": "SpotRemovalToolButton",
                "var": '_isRemovingSpots'
            },
            "background_removal": {
                "tool": "BackgroundRemovalToolButton",
                "var": '_isRemovingBackground'
            },
            "human_segmentation": {
                "tool": "HumanSegmentationToolButton",
                "var": '_isSegmentingHuman'
            },
            "colorizer": {
                "tool": "ColorizerToolButton",
                "var": '_isColorizing'
            },
            "super_resolution": {
                "tool": "SuperResolutionToolButton",
                "var": '_isUpscaling'
            },
            "eraser": {
                "tool": "EraserToolButton",
                "var": '_isErasing'
            },
            "blur": {
                "tool": "BlurToolButton",
                "var": '_isBlurring'
            },
        }

        ToolbarDockWidget = QtWidgets.QDockWidget("Tools")
        ToolbarDockWidget.setMinimumWidth(145)
        ToolbarContent = QtWidgets.QWidget()
        ToolbarLayout = QFlowLayout(ToolbarContent)
        ToolbarLayout.setSpacing(0)

        tool_buttons = [
            self.CursorToolButton, self.ColorPickerToolButton, self.PaintToolButton, self.EraserToolButton, 
            self.FillToolButton, self.CropToolButton, self.SelectToolButton, self.SpotRemovalToolButton, 
            self.BlurToolButton, self.BackgroundRemovalToolButton, self.HumanSegmentationToolButton, self.ColorizerToolButton,
            self.SuperResolutionToolButton, self.AnimeGanV2ToolButton
        ]

        for button in tool_buttons:
            button.setIconSize(QtCore.QSize(30, 30))
            ToolbarLayout.addWidget(button)

        ToolbarContent.setLayout(ToolbarLayout)
        ToolbarDockWidget.setWidget(ToolbarContent)

        self.MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, ToolbarDockWidget)

        ##############################################################################################
        ##############################################################################################
        # Show Window
        ##############################################################################################
        ##############################################################################################

        self.initImageViewer()
        self.MainWindow.showMaximized()

        self.progressWidgetLayout = QtWidgets.QVBoxLayout()
        self.progressWidget = QtWidgets.QWidget()
        self.progressBarLabel = QtWidgets.QLabel("Foo")

        # self.progressBarLayout = QtWidgets.QVBoxLayout()
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setMinimumWidth(300)
        self.progressBar.setMinimumHeight(50)
        self.progressWidgetLayout.addWidget(self.progressBarLabel)
        self.progressWidgetLayout.addWidget(self.progressBar)

        self.progressWidget.setLayout(self.progressWidgetLayout)
        self.progressWidget.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        # Initialize the thread
        self.progressBarThread = QProgressBarThread()

    @QtCore.pyqtSlot(int, str)
    def updateProgressBar(self, e, label):
        self.progressBar.setValue(e)
        self.progressBarLabel.setText(label)

    def initImageViewer(self):
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

        self.image_viewer.ColorPicker = self.color_picker

        # Set the central widget of the Window. Widget will expand
        # to take up all the space in the window by default.
        self.MainWindow.setCentralWidget(self.image_viewer)

    def resetSliderValues(self):
        # State of enhance sliders
        self.RedFactor = 100
        self.BlueFactor = 100
        self.GreenFactor = 100
        self.Color = 100
        self.Brightness = 100
        self.Contrast = 100
        self.Sharpness = 100
        self.GaussianBlurRadius = 0

        self.RedColorSlider.setValue(self.RedFactor)        
        self.GreenColorSlider.setValue(self.GreenFactor)        
        self.BlueColorSlider.setValue(self.BlueFactor)        
        self.ColorSlider.setValue(self.Color)        
        self.BrightnessSlider.setValue(self.Brightness)
        self.ContrastSlider.setValue(self.Contrast)
        self.SharpnessSlider.setValue(self.Sharpness)
        self.GaussianBlurSlider.setValue(self.GaussianBlurRadius)

    def getCurrentLayerLatestPixmap(self):
        return self.image_viewer.getCurrentLayerLatestPixmap()

    def processSliderChange(self, explanationOfChange, typeOfChange, valueOfChange, objectOfChange):
        self.UpdateImage(explanationOfChange, typeOfChange, valueOfChange, objectOfChange)

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

    def UpdateReds(self, Pixmap, value):
        CurrentImage = self.QPixmapToImage(Pixmap)

        # Split into channels
        r, g, b, a = CurrentImage.split()

        # Increase Reds
        r = r.point(lambda i: i * value)

        # Recombine back to RGB image
        AdjustedImage = Image.merge('RGBA', (r, g, b, a))

        return self.ImageToQPixmap(AdjustedImage)

    def AddRedColorSlider(self, layout):
        self.RedColorSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.RedColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Red", self.RedColorSlider)

        # Default value of the Color slider
        self.RedColorSlider.setValue(100) 

        self.RedColorSlider.valueChanged.connect(self.OnRedColorChanged)

    def OnRedColorChanged(self, value):
        self.RedFactor = value
        self.processSliderChange("Red", "Slider", value, "RedColorSlider")

    def UpdateGreens(self, Pixmap, value):
        CurrentImage = self.QPixmapToImage(Pixmap)

        # Split into channels
        r, g, b, a = CurrentImage.split()

        # Increase Greens
        g = g.point(lambda i: i * value)

        # Recombine back to RGB image
        AdjustedImage = Image.merge('RGBA', (r, g, b, a))

        return self.ImageToQPixmap(AdjustedImage)

    def AddGreenColorSlider(self, layout):
        self.GreenColorSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.GreenColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Green", self.GreenColorSlider)

        # Default value of the Color slider
        self.GreenColorSlider.setValue(100) 

        self.GreenColorSlider.valueChanged.connect(self.OnGreenColorChanged)

    def OnGreenColorChanged(self, value):
        self.GreenFactor = value
        self.processSliderChange("Green", "Slider", value, "GreenColorSlider")

    def UpdateBlues(self, Pixmap, value):
        CurrentImage = self.QPixmapToImage(Pixmap)

        # Split into channels
        r, g, b, a = CurrentImage.split()

        # Increase Blues
        b = b.point(lambda i: i * value)

        # Recombine back to RGB image
        AdjustedImage = Image.merge('RGBA', (r, g, b, a))

        return self.ImageToQPixmap(AdjustedImage)

    def AddBlueColorSlider(self, layout):
        self.BlueColorSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.BlueColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Blue", self.BlueColorSlider)

        # Default value of the Color slider
        self.BlueColorSlider.setValue(100) 

        self.BlueColorSlider.valueChanged.connect(self.OnBlueColorChanged)

    def OnBlueColorChanged(self, value):
        self.BlueFactor = value
        self.processSliderChange("Blue", "Slider", value, "BlueColorSlider")

    def AddColorSlider(self, layout):
        self.ColorSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.ColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Saturation", self.ColorSlider)

        # Default value of the Color slider
        self.ColorSlider.setValue(100) 

        self.ColorSlider.valueChanged.connect(self.OnColorChanged)

    def OnColorChanged(self, value):
        self.Color = value
        self.processSliderChange("Saturation", "Slider", value, "ColorSlider")

    def AddBrightnessSlider(self, layout):
        self.BrightnessSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.BrightnessSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Brightness", self.BrightnessSlider)

        # Default value of the brightness slider
        self.BrightnessSlider.setValue(100) 

        self.BrightnessSlider.valueChanged.connect(self.OnBrightnessChanged)

    def OnBrightnessChanged(self, value):
        self.Brightness = value
        self.processSliderChange("Brightness", "Slider", value, "BrightnessSlider")

    def AddContrastSlider(self, layout):
        self.ContrastSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.ContrastSlider.setRange(0, 200) # 1 is original image, 0 is a solid grey image
        layout.addRow("Contrast", self.ContrastSlider)

        # Default value of the brightness slider
        self.ContrastSlider.setValue(100) 

        self.ContrastSlider.valueChanged.connect(self.OnContrastChanged)

    def OnContrastChanged(self, value):
        self.Contrast = value
        self.processSliderChange("Contrast", "Slider", value, "ContrastSlider")

    def AddSharpnessSlider(self, layout):
        self.SharpnessSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.SharpnessSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Sharpness", self.SharpnessSlider)

        # Default value of the Sharpness slider
        self.SharpnessSlider.setValue(100) 

        self.SharpnessSlider.valueChanged.connect(self.OnSharpnessChanged)

    def OnSharpnessChanged(self, value):
        self.Sharpness = value
        self.processSliderChange("Sharpness", "Slider", value, "SharpnessSlider")

    def AddGaussianBlurSlider(self, layout):
        self.GaussianBlurSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.GaussianBlurSlider.setRange(0, 2000)
        layout.addRow("Gaussian Blur", self.GaussianBlurSlider)
        self.GaussianBlurSlider.valueChanged.connect(self.OnGaussianBlurChanged)

    def OnGaussianBlurChanged(self, value):
        self.GaussianBlurRadius = value
        self.processSliderChange("Gaussian Blur", "Slider", value, "GaussianBlurSlider")

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

    @QtCore.pyqtSlot()
    def onUpdateImageCompleted(self):
        import torch

        Pixmap, explanationOfChange, typeOfChange, valueOfChange, objectOfChange = self.progressBarThread.taskFunctionOutput
        if Pixmap:
            self.image_viewer.setImage(Pixmap, True, explanationOfChange, typeOfChange, valueOfChange, objectOfChange)
            self.UpdateHistogramPlot()
        self.progressBarThread.taskFunctionArgs = []

        self.progressBarThread.completeSignal.disconnect(self.onUpdateImageCompleted)
        self.progressBarThread.progressSignal.disconnect(self.updateProgressBar)

        # Clean up CUDA resources
        if torch.cuda.is_available():
            free_gpu_cache()

    def performUpdateImage(self, _, args):
        explanationOfChange, typeOfChange, valueOfChange, objectOfChange = args
        Pixmap = self.image_viewer.getCurrentLayerLatestPixmapBeforeSliderChange()
        if Pixmap:
            Pixmap = self.UpdateReds(Pixmap, float(self.RedFactor / 100))
            Pixmap = self.UpdateGreens(Pixmap, float(self.GreenFactor / 100))
            Pixmap = self.UpdateBlues(Pixmap, float(self.BlueFactor / 100))
            Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Color, self.Color)
            Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Brightness, self.Brightness)
            Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Contrast, self.Contrast)
            Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Sharpness, self.Sharpness)
            if self.GaussianBlurRadius > 0:
                Pixmap = self.ApplyGaussianBlur(Pixmap, float(self.GaussianBlurRadius / 100))

        return [Pixmap, explanationOfChange, typeOfChange, valueOfChange, objectOfChange]

    def UpdateImage(self, explanationOfChange, typeOfChange, valueOfChange, objectOfChange):
        # if not self.progressBarThread.isRunning():
        # TODO: Figure out how to correctly do this when lots of slider changes are made 
        # in quick succession

        self.progressBarThread.maxRange = 1000
        self.progressBarThread.completeSignal.connect(self.onUpdateImageCompleted)
        self.progressBarThread.progressSignal.connect(self.updateProgressBar)
        self.progressBarThread.taskFunction = self.performUpdateImage
        self.progressBarThread.taskFunctionArgs = [
            explanationOfChange, 
            typeOfChange, 
            valueOfChange, 
            objectOfChange]
        self.progressBarThread.start()

    def OnCursorToolButton(self, checked):
        self.EnableTool("cursor") if checked else self.DisableTool("cursor")

    def OnColorPickerToolButton(self, checked):
        self.EnableTool("color_picker") if checked else self.DisableTool("color_picker")

    def OnPaintToolButton(self, checked):
        self.EnableTool("paint") if checked else self.DisableTool("paint")

    def OnFillToolButton(self, checked):
        self.EnableTool("fill") if checked else self.DisableTool("fill")

    def OnCropToolButton(self, checked):
        self.EnableTool("crop") if checked else self.DisableTool("crop")

    def OnSelectToolButton(self, checked):
        self.EnableTool("select") if checked else self.DisableTool("select")

    def OnSpotRemovalToolButton(self, checked):
        self.EnableTool("spot_removal") if checked else self.DisableTool("spot_removal")

    @QtCore.pyqtSlot()
    def onBackgroundRemovalCompleted(self):
        import torch

        output = self.progressBarThread.taskFunctionOutput

        # Save new pixmap
        updatedPixmap = self.ImageToQPixmap(output)
        self.image_viewer.setImage(updatedPixmap, True, "Background Removal")

        self.progressBar.setValue(100)
        self.progressWidget.hide()

        self.progressBarThread.completeSignal.disconnect(self.onBackgroundRemovalCompleted)
        self.progressBarThread.progressSignal.disconnect(self.updateProgressBar)

        self.BackgroundRemovalToolButton.setChecked(False)

        # Clean up CUDA resources
        if torch.cuda.is_available():
            free_gpu_cache()

    def performBackgroundRemoval(self, progressSignal):
        from BackgroundRemoval import remove2

        # Merge NN model files into pth file if not exists
        if not os.path.exists("models/u2net.pth"):
            merge_files("u2net.pth", "models")

        progressSignal.emit(10, "Loading current pixmap")
        currentPixmap = self.getCurrentLayerLatestPixmap()
        return remove2(self.QPixmapToImage(currentPixmap), progressSignal, model_name="u2net")

    def OnBackgroundRemovalToolButton(self, checked):
        if checked:
            self.EnableTool("background_removal") if checked else self.DisableTool("background_removal")

            self.progressWidget.setWindowTitle("Performing Background Removal...")
            self.progressBarLabel.setText("Starting...")
            self.progressWidget.show()

            if not self.progressBarThread.isRunning():
                self.progressBarThread.maxRange = 1000
                self.progressBarThread.completeSignal.connect(self.onBackgroundRemovalCompleted)
                self.progressBarThread.progressSignal.connect(self.updateProgressBar)
                self.progressBarThread.taskFunction = self.performBackgroundRemoval
                self.progressBarThread.start()

    @QtCore.pyqtSlot()
    def onHumanSegmentationCompleted(self):
        import torch

        output = self.progressBarThread.taskFunctionOutput

        # Save new pixmap
        updatedPixmap = self.ImageToQPixmap(output)
        self.image_viewer.setImage(updatedPixmap, True, "Human Segmentation")

        self.progressBar.setValue(100)
        self.progressWidget.hide()

        self.progressBarThread.completeSignal.disconnect(self.onHumanSegmentationCompleted)
        self.progressBarThread.progressSignal.disconnect(self.updateProgressBar)

        self.HumanSegmentationToolButton.setChecked(False)

        # Clean up CUDA resources
        if torch.cuda.is_available():
            free_gpu_cache()

    def performHumanSegmentation(self, progressSignal):
        from BackgroundRemoval import remove2

        if not os.path.exists("models/u2net_human_seg.pth"):
            merge_files("u2net_human_seg.pth", "models")

        progressSignal.emit(10, "Loading current pixmap")
        currentPixmap = self.getCurrentLayerLatestPixmap()
        return remove2(self.QPixmapToImage(currentPixmap), progressSignal, model_name="u2net_human_seg")

    def OnHumanSegmentationToolButton(self, checked):

        if checked:
            self.EnableTool("human_segmentation") if checked else self.DisableTool("human_segmentation")

            self.progressWidget.setWindowTitle("Performing Human Segmentation...")
            self.progressBarLabel.setText("Starting...")
            self.progressWidget.show()

            if not self.progressBarThread.isRunning():
                self.progressBarThread.maxRange = 1000
                self.progressBarThread.completeSignal.connect(self.onHumanSegmentationCompleted)
                self.progressBarThread.progressSignal.connect(self.updateProgressBar)
                self.progressBarThread.taskFunction = self.performHumanSegmentation
                self.progressBarThread.start()

    @QtCore.pyqtSlot()
    def onColorizationCompleted(self):
        import torch

        output = self.progressBarThread.taskFunctionOutput

        # Save new pixmap
        output = Image.fromarray(output)
        updatedPixmap = self.ImageToQPixmap(output)
        self.image_viewer.setImage(updatedPixmap, True, "Colorizer")

        self.progressBar.setValue(100)
        self.progressWidget.hide()

        self.progressBarThread.completeSignal.disconnect(self.onColorizationCompleted)
        self.progressBarThread.progressSignal.disconnect(self.updateProgressBar)

        self.ColorizerToolButton.setChecked(False)

        # Clean up CUDA resources
        if torch.cuda.is_available():
            free_gpu_cache()

    def performColorization(self, progressSignal):
        import ColorizerUtil
        import ColorizerSiggraph17Model
        import torch
        import cv2

        progressSignal.emit(10, "Checking CUDA availability")

        useGpu = torch.cuda.is_available()

        progressSignal.emit(20, "Loading colorizer model")

        # Load colorizer
        colorizer_siggraph17 = ColorizerSiggraph17Model.siggraph17(pretrained=True).eval()
        if(useGpu):
            colorizer_siggraph17.cuda()

        progressSignal.emit(30, "Loading current pixmap")

        # Load current image
        currentPixmap = self.getCurrentLayerLatestPixmap()
        image = self.QPixmapToImage(currentPixmap)
        image = ColorizerUtil.load_img(image)
        b, g, r, a = cv2.split(image)

        progressSignal.emit(40, "Preprocessing image")

        (tens_l_orig, tens_l_rs) = ColorizerUtil.preprocess_img(np.dstack((b, g, r)), HW=(256,256))
        if(useGpu):
            tens_l_rs = tens_l_rs.cuda()

        progressSignal.emit(50, "Running colorizer on " + "cuda" if useGpu else "cpu")

        # colorizer outputs 256x256 ab map
        # resize and concatenate to original L channel
        img_bw = ColorizerUtil.postprocess_tens(tens_l_orig, torch.cat((0*tens_l_orig,0*tens_l_orig),dim=1))
        output = ColorizerUtil.postprocess_tens(tens_l_orig, colorizer_siggraph17(tens_l_rs).cpu())

        del image
        del tens_l_rs
        del tens_l_orig
        del img_bw

        progressSignal.emit(80, "Postprocessing output")

        # Fix RGB channels and recover the alpha channel that was lost earlier
        output = np.dstack((output * 255, a)).astype(np.uint8)

        progressSignal.emit(90, "Done")
        
        return output

    def OnColorizerToolButton(self, checked):

        if checked:
            self.EnableTool("colorizer") if checked else self.DisableTool("colorizer")

            self.progressWidget.setWindowTitle("Colorizing...")
            self.progressBarLabel.setText("Starting colorization")
            self.progressWidget.show()

            if not self.progressBarThread.isRunning():
                self.progressBarThread.maxRange = 1000
                self.progressBarThread.completeSignal.connect(self.onColorizationCompleted)
                self.progressBarThread.progressSignal.connect(self.updateProgressBar)
                self.progressBarThread.taskFunction = self.performColorization
                self.progressBarThread.start()

    @QtCore.pyqtSlot()
    def onSuperResolutionCompleted(self):
        import torch

        output = self.progressBarThread.taskFunctionOutput

        # Save new pixmap
        output = Image.fromarray(output)
        updatedPixmap = self.ImageToQPixmap(output)
        self.image_viewer.setImage(updatedPixmap, True, "Super-Resolution")

        self.progressBar.setValue(100)
        self.progressWidget.hide()

        self.progressBarThread.completeSignal.disconnect(self.onSuperResolutionCompleted)
        self.progressBarThread.progressSignal.disconnect(self.updateProgressBar)

        self.SuperResolutionToolButton.setChecked(False)

        # Clean up CUDA resources
        if torch.cuda.is_available():
            free_gpu_cache()

    def performSuperResolution(self, progressSignal):
        import torch
        import QualityScaler
        import ColorizerUtil
        import cv2

        progressSignal.emit(10, "Loading current pixmap")

        currentPixmap = self.getCurrentLayerLatestPixmap()
        image = self.QPixmapToImage(currentPixmap)
        w = image.width
        h = image.height
        image = ColorizerUtil.load_img(image)
        b, g, r, a = cv2.split(image)
        image_np = np.dstack((b, g, r))

        progressSignal.emit(20, "Checking CUDA availability")
            
        useGpu = torch.cuda.is_available()
        device = "cuda" if useGpu else "cpu"

        i = 0
        max_attempts = 2 # once on CUDA, once on CPU

        while i < max_attempts:
            try:

                progressSignal.emit(30, "Setting up torch autograd")

                QualityScaler.optimize_torch()

                model = "BSRGANx4"
                progressSignal.emit(40, "Loading model " + model + " on " + device)

                model = QualityScaler.prepare_AI_model(model, device)
                tiles_resolution = 700 # If the image is smaller than this on both sides, it'll be upscaled without any tiling

                progressSignal.emit(50, "Setting tile resolution " + str(tiles_resolution))

                upscaled = QualityScaler.upscale_image(image_np, model, device, tiles_resolution, progressSignal)

                alpha = np.full((upscaled.height, upscaled.width), 255)
                upscaled_np = np.asarray(upscaled)
                upscaled_rgba = np.dstack((upscaled_np, alpha)).astype(np.uint8)

                i += 1

                return upscaled_rgba

            except RuntimeError as e:
                i += 1
                print(e)
                if device == "cuda":
                    # Retry on CPU
                    progressSignal.emit(10, "Failed to run on CUDA device. Retrying on CPU")
                    device = "cpu"
                    free_gpu_cache()
                    print("Retrying on CPU")

    def OnSuperResolutionToolButton(self, checked):

        if checked:
            self.EnableTool("super_resolution") if checked else self.DisableTool("super_resolution")

            self.progressWidget.setWindowTitle("Perform Super-Resolution Quality Scaling...")
            self.progressBarLabel.setText("Starting")
            self.progressWidget.show()

            if not self.progressBarThread.isRunning():
                self.progressBarThread.maxRange = 1000
                self.progressBarThread.completeSignal.connect(self.onSuperResolutionCompleted)
                self.progressBarThread.progressSignal.connect(self.updateProgressBar)
                self.progressBarThread.taskFunction = self.performSuperResolution
                self.progressBarThread.start()

    @QtCore.pyqtSlot()
    def onAnimeGanV2Completed(self):
        import torch

        output = self.progressBarThread.taskFunctionOutput

        if output:
            # Save new pixmap
             updatedPixmap = self.ImageToQPixmap(output)
             self.image_viewer.setImage(updatedPixmap, True, "Anime GAN v2")

        self.progressBar.setValue(100)
        self.progressWidget.hide()

        self.progressBarThread.completeSignal.disconnect(self.onAnimeGanV2Completed)
        self.progressBarThread.progressSignal.disconnect(self.updateProgressBar)

        self.AnimeGanV2ToolButton.setChecked(False)

        # Clean up CUDA resources
        if torch.cuda.is_available():
            free_gpu_cache()

    def performAnimeGanV2(self, progressSignal):
        from torchvision.transforms.functional import to_tensor, to_pil_image
        from AnimeGANv2Model import Generator as AnimeGanV2Generator
        import torch
        import cv2

        # Clean up CUDA resources
        if torch.cuda.is_available():
            free_gpu_cache()

        progressSignal.emit(10, "Checking CUDA capability")
        useGpu = torch.cuda.is_available()
        device = "cuda" if useGpu else "cpu"

        i = 0
        max_attempts = 2 # once on CUDA, once on CPU

        while i < max_attempts:
            try:
                progressSignal.emit(20, "Loading model")
 
                net = AnimeGanV2Generator()
                net.load_state_dict(torch.load("models/face_paint_512_v2.pt", map_location=device))
                net.to(device).eval()

                progressSignal.emit(30, "Loading current pixmap")

                currentPixmap = self.getCurrentLayerLatestPixmap()
                image = self.QPixmapToImage(currentPixmap)

                progressSignal.emit(40, "Preprocessing image")

                b, g, r, _ = cv2.split(np.asarray(image))
                image_np = np.dstack((b, g, r))
                image_pil = Image.fromarray(image_np)

                with torch.no_grad():
                    progressSignal.emit(50, "Converting to tensor")
                    image_tensor = to_tensor(image_pil).unsqueeze(0) * 2 - 1

                    progressSignal.emit(60, "Running the model on " + device)

                    out = net(image_tensor.to(device), False # <-- upsample_align (Align corners in decoder upsampling layers)
                              ).cpu()
                    out = out.squeeze(0).clip(-1, 1) * 0.5 + 0.5

                    progressSignal.emit(70, "Postprocessing output")

                    out = to_pil_image(out)

                    # Add alpha channel back
                    alpha = np.full((out.height, out.width), 255)
                    out_np = np.dstack((np.asarray(out), alpha)).astype(np.uint8)

                    del image_tensor
                    del net
                    del out

                    i += 1

                    return Image.fromarray(out_np)

            except RuntimeError as e:
                i += 1
                print(e)
                if device == "cuda":
                    # Retry on CPU
                    progressSignal.emit(10, "Failed to run on CUDA device. Retrying on CPU")
                    device = "cpu"
                    free_gpu_cache()
                    print("Retrying on CPU")

    def OnAnimeGanV2ToolButton(self, checked):
        if checked:
            self.EnableTool("anime") if checked else self.DisableTool("anime")

            self.progressWidget.setWindowTitle("Anime GAN v2...")
            self.progressBarLabel.setText("Starting")
            self.progressWidget.show()

            if not self.progressBarThread.isRunning():
                self.progressBarThread.maxRange = 1000
                self.progressBarThread.completeSignal.connect(self.onAnimeGanV2Completed)
                self.progressBarThread.progressSignal.connect(self.updateProgressBar)
                self.progressBarThread.taskFunction = self.performAnimeGanV2
                self.progressBarThread.start()

    def OnEraserToolButton(self, checked):
        self.EnableTool("eraser") if checked else self.DisableTool("eraser")

    def OnBlurToolButton(self, checked):
        self.EnableTool("blur") if checked else self.DisableTool("blur")

    def EnableTool(self, tool):
        for key, value in self.tools.items():
            if key == tool:
                getattr(self, value["tool"]).setChecked(True)
                setattr(self.image_viewer, value["var"], True)
            else:
                # Disable the other tools
                getattr(self, value["tool"]).setChecked(False)
                setattr(self.image_viewer, value["var"], False)
                if "destructor" in value:
                    getattr(self.image_viewer, value["destructor"])()

    def DisableTool(self, tool):
        value = self.tools[tool]
        getattr(self, value["tool"]).setChecked(False)
        setattr(self.image_viewer, value["var"], False)
        if "destructor" in value:
            getattr(self.image_viewer, value["destructor"])()

    def updateHistogram(self):
        # Update Histogram

        # Compute image histogram
        img = self.QPixmapToImage(self.getCurrentLayerLatestPixmap())
        r, g, b, a = img.split()
        r_histogram = r.histogram()
        g_histogram = g.histogram()
        b_histogram = b.histogram()
        
        # ITU-R 601-2 luma transform:
        luma_histogram = [sum(x) for x in zip([item * float(299/1000) for item in r_histogram],
                                              [item * float(587/1000) for item in g_histogram],
                                              [item * float(114/1000) for item in b_histogram])]

        # Create histogram plot
        x = list(range(len(r_histogram)))
        self.ImageHistogramPlot.removeItem(self.ImageHistogramGraphRed)
        self.ImageHistogramPlot.removeItem(self.ImageHistogramGraphGreen)
        self.ImageHistogramPlot.removeItem(self.ImageHistogramGraphBlue)
        self.ImageHistogramPlot.removeItem(self.ImageHistogramGraphLuma)
        self.ImageHistogramGraphRed = pg.PlotCurveItem(x = x, y = r_histogram, fillLevel=2, width = 1.0, brush=(255,0,0,80))
        self.ImageHistogramGraphGreen = pg.PlotCurveItem(x = x, y = g_histogram, fillLevel=2, width = 1.0, brush=(0,255,0,80))
        self.ImageHistogramGraphBlue = pg.PlotCurveItem(x = x, y = b_histogram, fillLevel=2, width = 1.0, brush=(0,0,255,80))
        self.ImageHistogramGraphLuma = pg.PlotCurveItem(x = x, y = luma_histogram, fillLevel=2, width = 1.0, brush=(255,255,255,80))
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphRed)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphGreen)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphBlue)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphLuma)

    def updateColorPicker(self):
        # Set the RGB in the color picker to the value in the middle of the image
        currentPixmap = self.getCurrentLayerLatestPixmap()
        pixelAccess = self.QPixmapToImage(currentPixmap).load()
        middle_pixel_x = int(currentPixmap.width() / 2)
        middle_pixel_y = int(currentPixmap.height() / 2)
        r, g, b, a = pixelAccess[middle_pixel_x, middle_pixel_y]
        self.color_picker.setRGB((r, g, b))

    def OnOpen(self):
        # Load an image file to be displayed (will popup a file dialog).
        self.image_viewer.open()
        filename = self.image_viewer._current_filename
        filename = os.path.basename(filename)
        self.MainWindow.setWindowTitle(filename)
        # self.image_viewer.OriginalImage = self.image_viewer.pixmap()
        self.updateHistogram()
        self.updateColorPicker()
        self.resetSliderValues()

    def OnSave(self):
        # self.image_viewer.OriginalImage = self.image_viewer.pixmap()
        self.image_viewer.save()
   
    def OnSaveAs(self):
        name, ext = os.path.splitext(self.image_viewer._current_filename)
        dialog = QFileDialog()
        dialog.setDefaultSuffix("jpg")
        extension_filter = "Default (*.jpg);;BMP (*.bmp);;Icon (*.ico);;JPEG (*.jpeg *.jpg);;PBM (*.pbm);;PGM (*.pgm);;PNG (*.png);;PPM (*.ppm);;TIF (*.tif *.tiff);;WBMP (*.wbmp);;XBM (*.xbm);;XPM (*.xpm)"
        name = dialog.getSaveFileName(self.MainWindow, 'Save File', name + " EDITED" + ".jpg", extension_filter)
        # self.image_viewer.OriginalImage = self.image_viewer.pixmap()
        self.image_viewer.save(name[0])
        filename = self.image_viewer._current_filename
        filename = os.path.basename(filename)
        self.MainWindow.setWindowTitle(filename)

    def OnUndo(self):
        self.image_viewer.undoCurrentLayerLatestChange()

    def OnPaste(self):
        cb = QApplication.clipboard()
        md = cb.mimeData()
        if md.hasImage():
            img = cb.image()
            self.initImageViewer()
            self.image_viewer._current_filename = "Untitled.png"
            self.image_viewer.setImage(img, True, "Paste")
            filename = self.image_viewer._current_filename
            self.MainWindow.setWindowTitle(filename)
            # self.image_viewer.OriginalImage = self.image_viewer.pixmap()

            self.updateHistogram()
            self.updateColorPicker()
            self.resetSliderValues()

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