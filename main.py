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
    QToolButton,
    QFileDialog
)
from PyQt6.QtGui import QPixmap
import sys
import qdarkstyle

from functools import partial
from QImageViewer import QtImageViewer
from QCropItem import QCropItem
from PyQt6.QtGui import QKeySequence
import pyqtgraph as pg
import cv2
from matplotlib import pyplot as plt
import numpy as np
from QColorPicker import QColorPicker
import os
from QFlowLayout import QFlowLayout
import utilities
from bg import remove2
from threading import Thread
from queue import Queue
from PIL import Image, ImageEnhance, ImageFilter
from PIL.ImageQt import ImageQt

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

        # Set the central widget of the Window. Widget will expand
        # to take up all the space in the window by default.
        self.MainWindow.setCentralWidget(self.image_viewer)

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
        self.image_viewer.ColorPicker = self.color_picker

        ##############################################################################################
        ##############################################################################################
        # Adjustment Sliders
        ##############################################################################################
        ##############################################################################################

        dock = QtWidgets.QDockWidget("")
        # dock.setMinimumSize(100, self.image_viewer.height())
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
            self.BlurToolButton, self.BackgroundRemovalToolButton, self.HumanSegmentationToolButton            
        ]

        for button in tool_buttons:
            button.setIconSize(QtCore.QSize(20, 20))
            ToolbarLayout.addWidget(button)

        ToolbarContent.setLayout(ToolbarLayout)
        ToolbarDockWidget.setWidget(ToolbarContent)

        self.MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, ToolbarDockWidget)

        ##############################################################################################
        ##############################################################################################
        # Show Window
        ##############################################################################################
        ##############################################################################################

        self.MainWindow.showMaximized()

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

    def UpdateImage(self, explanationOfChange, typeOfChange, valueOfChange, objectOfChange):
        Pixmap = self.image_viewer.getCurrentLayerPixmapBeforeChangeTo(explanationOfChange)
        if Pixmap:
            Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Color, self.Color)
            Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Brightness, self.Brightness)
            Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Contrast, self.Contrast)
            Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Sharpness, self.Sharpness)
            if self.GaussianBlurRadius > 0:
                Pixmap = self.ApplyGaussianBlur(Pixmap, float(self.GaussianBlurRadius / 100))
            self.image_viewer.setImage(Pixmap, True, explanationOfChange, typeOfChange, valueOfChange, objectOfChange)
            # TODO: Add every adjusted image to a history list
            # Will help with implementing undo
            # Will also help with using sliders AND using tools at the same time and
            # maintaining consistency
            self.UpdateHistogramPlot()

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

    def OnBackgroundRemovalToolButton(self, checked):
        if checked:
            # Set cursor to wait
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            self.EnableTool("background_removal") if checked else self.DisableTool("background_removal")

            # Remove background
            currentPixmap = self.getCurrentLayerLatestPixmap()
            BackgroundRemovedImage = remove2(self.QPixmapToImage(currentPixmap), model_name="u2net")
            updatedPixmap = self.ImageToQPixmap(BackgroundRemovedImage)
            self.image_viewer.setImage(updatedPixmap, True, "Background Removal")
            # self.image_viewer.OriginalImage = updatedPixmap

            # Restore cursor
            QApplication.restoreOverrideCursor()

        self.BackgroundRemovalToolButton.setChecked(False)

    def OnHumanSegmentationToolButton(self, checked):
        if checked:
            # Set cursor to wait
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            self.EnableTool("human_segmentation") if checked else self.DisableTool("human_segmentation")

            # Remove background
            currentPixmap = self.getCurrentLayerLatestPixmap()
            BackgroundRemovedImage = remove2(self.QPixmapToImage(currentPixmap), model_name="u2net_human_seg")
            updatedPixmap = self.ImageToQPixmap(BackgroundRemovedImage)
            self.image_viewer.setImage(updatedPixmap, True, "Human Segmentation")
            # self.image_viewer.OriginalImage = updatedPixmap

            # Restore cursor
            QApplication.restoreOverrideCursor()

        self.HumanSegmentationToolButton.setChecked(False)

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

    def OnSave(self):
        # self.image_viewer.OriginalImage = self.image_viewer.pixmap()
        self.image_viewer.save()
   
    def OnSaveAs(self):
        dialog = QFileDialog()
        dialog.setDefaultSuffix("png")
        name = dialog.getSaveFileName(self.MainWindow, 'Save File', "Untitled.png", "BMP (*.bmp);;Icon (*.ico);;JPEG (*.jpeg *.jpg);;PBM (*.pbm);;PGM (*.pgm);;PNG (*.png);;PPM (*.ppm);;TIF (*.tif *.tiff);;WBMP (*.wbmp);;XBM (*.xbm);;XPM (*.xpm)")
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
            self.image_viewer._current_filename = "Untitled.png"
            self.image_viewer.setImage(img, True, "Paste")
            filename = self.image_viewer._current_filename
            self.MainWindow.setWindowTitle(filename)
            # self.image_viewer.OriginalImage = self.image_viewer.pixmap()

            self.updateHistogram()
            self.updateColorPicker()

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