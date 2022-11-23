import PyQt6
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QSlider,
    QToolBar,
    QToolButton,
    QFileDialog,
)
from PyQt6.QtGui import QPixmap
import sys

from QImageViewer import QtImageViewer
from PyQt6.QtGui import QKeySequence
import pyqtgraph as pg
from QColorPicker import QColorPicker
import os
from QFlowLayout import QFlowLayout
from PIL import Image, ImageEnhance, ImageFilter
from QWorker import QWorker

def free_gpu_cache():
    import torch
    from GPUtil import showUtilization as gpu_usage

    print("Initial GPU Usage")
    gpu_usage()                             

    torch.cuda.empty_cache()

    print("GPU Usage after emptying the cache")
    gpu_usage()

def importLibraries():
    import torch
    import numpy as np
    import cv2
    import PIL
    print("Torch version", torch.__version__)
    print("Torch CUDA available?", "YES" if torch.cuda.is_available() else "NO")
    print("cv2 version", cv2.__version__)
    print("numpy version", np.__version__)
    print("PIl version", PIL.__version__)

class Gui(QtWidgets.QMainWindow):

    sliderChangeSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(Gui, self).__init__(parent)
        self.setWindowTitle('Photo Editor')
        self.setMinimumHeight(850)

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

        self.OpenShortcut = QtGui.QShortcut(QKeySequence("Ctrl+O"), self)
        self.OpenShortcut.activated.connect(self.OnOpen)

        self.PasteShortcut = QtGui.QShortcut(QKeySequence("Ctrl+V"), self)
        self.PasteShortcut.activated.connect(self.OnPaste)

        self.SaveShortcut = QtGui.QShortcut(QKeySequence("Ctrl+S"), self)
        self.SaveShortcut.activated.connect(self.OnSave)

        self.SaveAsShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.SaveAsShortcut.activated.connect(self.OnSaveAs)

        self.UndoShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Z"), self)
        self.UndoShortcut.activated.connect(self.OnUndo)

        ##############################################################################################
        ##############################################################################################
        # Toolbar
        ##############################################################################################
        ##############################################################################################

        # Using a QToolBar object and a toolbar area
        ImageToolBar = QToolBar("Toolbar", self)

        ##############################################################################################
        ##############################################################################################
        # Cursor Tool
        ##############################################################################################
        ##############################################################################################

        self.CursorToolButton = QToolButton(self)
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

        self.ColorPickerToolButton = QToolButton(self)
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

        self.PaintToolButton = QToolButton(self)
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

        self.FillToolButton = QToolButton(self)
        self.FillToolButton.setText("&Fill")
        self.FillToolButton.setToolTip("Fill")
        self.FillToolButton.setIcon(QtGui.QIcon("icons/fill.svg"))
        self.FillToolButton.setCheckable(True)
        self.FillToolButton.toggled.connect(self.OnFillToolButton)

        ##############################################################################################
        ##############################################################################################
        # Rectangle Select Tool
        ##############################################################################################
        ##############################################################################################

        self.RectSelectToolButton = QToolButton(self)
        self.RectSelectToolButton.setText("&Rectangle Select")
        self.RectSelectToolButton.setToolTip("Rectangle Select")
        self.RectSelectToolButton.setIcon(QtGui.QIcon("icons/select_rect.svg"))
        self.RectSelectToolButton.setCheckable(True)
        self.RectSelectToolButton.toggled.connect(self.OnRectSelectToolButton)

        ##############################################################################################
        ##############################################################################################
        # Path Select Tool
        ##############################################################################################
        ##############################################################################################

        self.PathSelectToolButton = QToolButton(self)
        self.PathSelectToolButton.setText("&Path Select")
        self.PathSelectToolButton.setToolTip("Path Select")
        self.PathSelectToolButton.setIcon(QtGui.QIcon("icons/select_path.svg"))
        self.PathSelectToolButton.setCheckable(True)
        self.PathSelectToolButton.toggled.connect(self.OnPathSelectToolButton)

        ##############################################################################################
        ##############################################################################################
        # Crop Tool
        ##############################################################################################
        ##############################################################################################

        self.CropToolButton = QToolButton(self)
        self.CropToolButton.setText("&Crop")
        self.CropToolButton.setIcon(QtGui.QIcon("icons/crop.svg"))
        self.CropToolButton.setToolTip("Crop")
        self.CropToolButton.setCheckable(True)
        self.CropToolButton.toggled.connect(self.OnCropToolButton)

        self.CropToolShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Shift+Alt+K"), self)
        self.CropToolShortcut.activated.connect(lambda: self.CropToolButton.toggle())

        ##############################################################################################
        ##############################################################################################
        # Rotate Left Tool
        ##############################################################################################
        ##############################################################################################

        self.RotateLeftToolButton = QToolButton(self)
        self.RotateLeftToolButton.setText("&Rotate Left")
        self.RotateLeftToolButton.setIcon(QtGui.QIcon("icons/rotate_left.svg"))
        self.RotateLeftToolButton.setToolTip("Rotate Left")
        self.RotateLeftToolButton.setCheckable(True)
        self.RotateLeftToolButton.toggled.connect(self.OnRotateLeftToolButton)

        ##############################################################################################
        ##############################################################################################
        # Rotate Right Tool
        ##############################################################################################
        ##############################################################################################

        self.RotateRightToolButton = QToolButton(self)
        self.RotateRightToolButton.setText("&Rotate Right")
        self.RotateRightToolButton.setIcon(QtGui.QIcon("icons/rotate_right.svg"))
        self.RotateRightToolButton.setToolTip("Rotate Right")
        self.RotateRightToolButton.setCheckable(True)
        self.RotateRightToolButton.toggled.connect(self.OnRotateRightToolButton)

        ##############################################################################################
        ##############################################################################################
        # Horizontal Stack Tool
        ##############################################################################################
        ##############################################################################################

        self.HStackToolButton = QToolButton(self)
        self.HStackToolButton.setText("&Horizontal Stack")
        self.HStackToolButton.setIcon(QtGui.QIcon("icons/hstack.svg"))
        self.HStackToolButton.setToolTip("Horizontal Stack")
        self.HStackToolButton.setCheckable(True)
        self.HStackToolButton.toggled.connect(self.OnHStackToolButton)

        ##############################################################################################
        ##############################################################################################
        # Vertical Stack Tool
        ##############################################################################################
        ##############################################################################################

        self.VStackToolButton = QToolButton(self)
        self.VStackToolButton.setText("&Vertical Stack")
        self.VStackToolButton.setIcon(QtGui.QIcon("icons/vstack.svg"))
        self.VStackToolButton.setToolTip("Vertical Stack")
        self.VStackToolButton.setCheckable(True)
        self.VStackToolButton.toggled.connect(self.OnVStackToolButton)

        ##############################################################################################
        ##############################################################################################
        # Flip Left Right Tool
        ##############################################################################################
        ##############################################################################################

        self.FlipLeftRightToolButton = QToolButton(self)
        self.FlipLeftRightToolButton.setText("&Flip Left-Right")
        self.FlipLeftRightToolButton.setIcon(QtGui.QIcon("icons/flip_left_right.svg"))
        self.FlipLeftRightToolButton.setToolTip("Flip Left-Right")
        self.FlipLeftRightToolButton.setCheckable(True)
        self.FlipLeftRightToolButton.toggled.connect(self.OnFlipLeftRightToolButton)

        ##############################################################################################
        ##############################################################################################
        # Flip Top Bottom Tool
        ##############################################################################################
        ##############################################################################################

        self.FlipTopBottomToolButton = QToolButton(self)
        self.FlipTopBottomToolButton.setText("&Flip Top-Bottom")
        self.FlipTopBottomToolButton.setIcon(QtGui.QIcon("icons/flip_top_bottom.svg"))
        self.FlipTopBottomToolButton.setToolTip("Flip Top-Bottom")
        self.FlipTopBottomToolButton.setCheckable(True)
        self.FlipTopBottomToolButton.toggled.connect(self.OnFlipTopBottomToolButton)

        ##############################################################################################
        ##############################################################################################
        # Spot Removal Tool
        ##############################################################################################
        ##############################################################################################

        self.SpotRemovalToolButton = QToolButton(self)
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

        self.BlurToolButton = QToolButton(self)
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

        self.BackgroundRemovalToolButton = QToolButton(self)
        self.BackgroundRemovalToolButton.setText("&Background Removal")
        self.BackgroundRemovalToolButton.setToolTip("Background Removal")
        self.BackgroundRemovalToolButton.setIcon(QtGui.QIcon("icons/background_removal.svg"))
        self.BackgroundRemovalToolButton.setCheckable(True)
        self.BackgroundRemovalToolButton.toggled.connect(self.OnBackgroundRemovalToolButton)

        ##############################################################################################
        ##############################################################################################
        # Background Removal Tool
        ##############################################################################################
        ##############################################################################################

        self.PortraitModeBackgroundBlurToolButton = QToolButton(self)
        self.PortraitModeBackgroundBlurToolButton.setText("&Portrait Mode")
        self.PortraitModeBackgroundBlurToolButton.setToolTip("Portrait Mode")
        self.PortraitModeBackgroundBlurToolButton.setIcon(QtGui.QIcon("icons/portrait_mode.svg"))
        self.PortraitModeBackgroundBlurToolButton.setCheckable(True)
        self.PortraitModeBackgroundBlurToolButton.toggled.connect(self.OnPortraitModeBackgroundBlurToolButton)

        ##############################################################################################
        ##############################################################################################
        # Human Segmentation Tool
        ##############################################################################################
        ##############################################################################################

        self.HumanSegmentationToolButton = QToolButton(self)
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

        self.ColorizerToolButton = QToolButton(self)
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

        self.SuperResolutionToolButton = QToolButton(self)
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

        self.AnimeGanV2ToolButton = QToolButton(self)
        self.AnimeGanV2ToolButton.setText("&Anime GAN v2")
        self.AnimeGanV2ToolButton.setToolTip("Anime GAN v2")
        self.AnimeGanV2ToolButton.setIcon(QtGui.QIcon("icons/anime.svg"))
        self.AnimeGanV2ToolButton.setCheckable(True)
        self.AnimeGanV2ToolButton.toggled.connect(self.OnAnimeGanV2ToolButton)

        ##############################################################################################
        ##############################################################################################
        # White Balance Tool
        # https://github.com/mahmoudnafifi/WB_sRGB
        ##############################################################################################
        ##############################################################################################

        self.WhiteBalanceToolButton = QToolButton(self)
        self.WhiteBalanceToolButton.setText("&White Balance")
        self.WhiteBalanceToolButton.setToolTip("White Balance")
        self.WhiteBalanceToolButton.setIcon(QtGui.QIcon("icons/white_balance.svg"))
        self.WhiteBalanceToolButton.setCheckable(True)
        self.WhiteBalanceToolButton.toggled.connect(self.OnWhiteBalanceToolButton)

        ##############################################################################################
        ##############################################################################################
        # Eraser Tool
        ##############################################################################################
        ##############################################################################################

        self.EraserToolButton = QToolButton(self)
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
            "select_rect": {
                "tool": "RectSelectToolButton",
                "var": '_isSelectingRect',
                "destructor": 'exitSelectRect'
            },
            "select_path": {
                "tool": "PathSelectToolButton",
                "var": '_isSelectingPath',
                "destructor": 'exitSelectPath'
            },
            "crop": {
                "tool": "CropToolButton",
                "var": '_isCropping'
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
            "portrait_mode": {
                "tool": "PortraitModeBackgroundBlurToolButton",
                "var": '_isBlurringBackground'
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
            "white_balance": {
                "tool": "WhiteBalanceToolButton",
                "var": '_isWhiteBalancing'
            },
        }

        ToolbarDockWidget = QtWidgets.QDockWidget("Tools")
        ToolbarDockWidget.setMinimumWidth(145)
        ToolbarContent = QtWidgets.QWidget()
        ToolbarLayout = QFlowLayout(ToolbarContent)
        ToolbarLayout.setSpacing(0)

        tool_buttons = [
            self.CursorToolButton, self.ColorPickerToolButton, self.PaintToolButton, self.EraserToolButton, 
            self.FillToolButton, self.RectSelectToolButton, self.PathSelectToolButton, self.CropToolButton, 
            self.RotateLeftToolButton, self.RotateRightToolButton,
            self.HStackToolButton, self.VStackToolButton, 
            self.FlipLeftRightToolButton, self.FlipTopBottomToolButton,
            self.SpotRemovalToolButton, self.BlurToolButton, self.WhiteBalanceToolButton, 
            self.BackgroundRemovalToolButton, self.HumanSegmentationToolButton, self.PortraitModeBackgroundBlurToolButton, 
            self.ColorizerToolButton, self.SuperResolutionToolButton, self.AnimeGanV2ToolButton, 
        ]

        for button in tool_buttons:
            button.setIconSize(QtCore.QSize(30, 30))
            ToolbarLayout.addWidget(button)

        ToolbarContent.setLayout(ToolbarLayout)
        ToolbarDockWidget.setWidget(ToolbarContent)
        ToolbarDockWidget.setMaximumHeight(180)
        self.currentTool = None

        ##############################################################################################
        ##############################################################################################
        # Right Dock
        ##############################################################################################
        ##############################################################################################

        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, ToolbarDockWidget)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, HistogramDock)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, ColorPickerDock)

        ##############################################################################################
        ##############################################################################################
        # Show Window
        ##############################################################################################
        ##############################################################################################

        self.initImageViewer()
        self.showMaximized()

        self.threadpool = QtCore.QThreadPool()
        self.sliderChangedPixmap = None
        self.sliderExplanationOfChange = None
        self.sliderTypeOfChange = None
        self.sliderValueOfChange = None
        self.sliderObjectOfChange = None
        self.sliderChangeSignal.connect(self.onUpdateImageCompleted)
        self.sliderWorkers = []

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
        self.setCentralWidget(self.image_viewer)

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
        if len(self.sliderWorkers):
            pass
        # Pass the function to execute
        worker = QWorker(self.performUpdateImage, explanationOfChange, typeOfChange, valueOfChange, objectOfChange)
        # worker.signals.result.connect(self.print_output)
        # worker.signals.finished.connect(self.thread_complete)
        # worker.signals.progress.connect(self.progress_fn)

        # Execute
        self.threadpool.start(worker)
        self.sliderWorkers.append(worker)
        # self.UpdateImage(explanationOfChange, typeOfChange, valueOfChange, objectOfChange)

    def QPixmapToImage(self, pixmap):
        width = pixmap.width()
        height = pixmap.height()
        image = pixmap.toImage()

        byteCount = image.bytesPerLine() * height
        data = image.constBits().asstring(byteCount)
        return Image.frombuffer('RGBA', (width, height), data, 'raw', 'BGRA', 0, 1)

    def ImageToQPixmap(self, image):
        from PIL.ImageQt import ImageQt
        return QPixmap.fromImage(ImageQt(image))

    def EnhanceImage(self, Pixmap, Property, value):
        CurrentImage = self.QPixmapToImage(Pixmap)
        AdjustedImage = Property(CurrentImage).enhance(float(value) / 100)
        return self.ImageToQPixmap(AdjustedImage)

    def ApplyGaussianBlur(self, Pixmap, value):
        CurrentImage = self.QPixmapToImage(Pixmap)
        AdjustedImage = CurrentImage.filter(ImageFilter.GaussianBlur(radius=value))
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
        if self.sliderChangedPixmap:
            self.image_viewer.setImage(self.sliderChangedPixmap, True, self.sliderExplanationOfChange, 
                                       self.sliderTypeOfChange, self.sliderValueOfChange, self.sliderObjectOfChange)
            self.UpdateHistogramPlot()

    def performUpdateImage(self, explanationOfChange, typeOfChange, valueOfChange, objectOfChange):
        Pixmap = self.image_viewer.getCurrentLayerLatestPixmapBeforeSliderChange()
        if Pixmap:
            if self.RedFactor != 100:
                Pixmap = self.UpdateReds(Pixmap, float(self.RedFactor / 100))
            if self.GreenFactor != 100:
                Pixmap = self.UpdateGreens(Pixmap, float(self.GreenFactor / 100))
            if self.BlueFactor != 100:
                Pixmap = self.UpdateBlues(Pixmap, float(self.BlueFactor / 100))
            if self.Color != 100:
                Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Color, self.Color)
            if self.Brightness != 100:
                Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Brightness, self.Brightness)
            if self.Contrast != 100:
                Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Contrast, self.Contrast)
            if self.Sharpness != 100:
                Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Sharpness, self.Sharpness)
            if self.GaussianBlurRadius > 0:
                Pixmap = self.ApplyGaussianBlur(Pixmap, float(self.GaussianBlurRadius / 100))

            self.sliderChangedPixmap = Pixmap
            self.sliderExplanationOfChange = explanationOfChange
            self.sliderTypeOfChange = typeOfChange
            self.sliderValueOfChange = valueOfChange
            self.sliderObjectOfChange = objectOfChange
            self.sliderChangeSignal.emit()

    def UpdateImage(self, explanationOfChange, typeOfChange, valueOfChange, objectOfChange):
        ## if not self.progressBarThread.isRunning():
        ## TODO: Figure out how to correctly do this when lots of slider changes are made 
        ## in quick succession

        #self.progressBarThread.taskFunctionArgs = [
        #    explanationOfChange, 
        #    typeOfChange, 
        #    valueOfChange, 
        #    objectOfChange]
        #self.progressBarThread.start()
        pass

    def OnCursorToolButton(self, checked):
        self.EnableTool("cursor") if checked else self.DisableTool("cursor")

    def OnColorPickerToolButton(self, checked):
        self.EnableTool("color_picker") if checked else self.DisableTool("color_picker")

    def OnPaintToolButton(self, checked):
        self.EnableTool("paint") if checked else self.DisableTool("paint")

    def OnFillToolButton(self, checked):
        self.EnableTool("fill") if checked else self.DisableTool("fill")

    def OnCropToolButton(self, checked):
        if checked:
            self.image_viewer._isCropping = True
            self.image_viewer.performCrop()
            self.DisableAllTools()
            # self.DisableTool("crop")

    def OnRotateLeftToolButton(self, checked):
        if checked:
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.rotate(90, expand=True)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Rotate Left", "Tool", None, None)
        self.RotateLeftToolButton.setChecked(False)

    def OnRotateRightToolButton(self, checked):
        if checked:
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.rotate(-90, expand=True)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Rotate Right", "Tool", None, None)
        self.RotateRightToolButton.setChecked(False)

    def OnHStackToolButton(self, checked):
        if checked:
            if self.image_viewer._current_filename:

                pixmap = self.getCurrentLayerLatestPixmap()
                first = self.QPixmapToImage(pixmap)

                if pixmap:

                    # Open second image
                    filepath, _ = QFileDialog.getOpenFileName(self, "Open image file.")
                    if len(filepath) and os.path.isfile(filepath):
                        second = Image.open(filepath)

                        if first.width != second.width or first.height != second.height:
                            # The two images are of different size

                            # If the two images are not the exact same size
                            # Ask the user if they want to resize the first or second or leave as is
                            msgBox = QtWidgets.QMessageBox()
                            msgBox.setText('First Image is ' + str(first.width) + "x" + str(first.height) + '\n'
                                           'Second Image is ' + str(second.width) + "x" + str(second.height))
                            msgBox.addButton(QtWidgets.QPushButton('Resize First'), QtWidgets.QMessageBox.ButtonRole.YesRole)
                            msgBox.addButton(QtWidgets.QPushButton('Resize Second'), QtWidgets.QMessageBox.ButtonRole.NoRole)
                            msgBox.addButton(QtWidgets.QPushButton("Stack As Is"), QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
                            msgBox.addButton(QtWidgets.QPushButton('Cancel'), QtWidgets.QMessageBox.ButtonRole.RejectRole)
                            ret = msgBox.exec()

                            from PIL import ImageOps
                            
                            if ret == 3:
                                # Cancel operation
                                self.HStackToolButton.setChecked(False)
                                return
                            elif ret == 0:
                                # Resize first to match the size of second
                                first = ImageOps.contain(first, (second.width, second.height))
                            elif ret == 1:
                                # Resize second to match the size of first
                                second = ImageOps.contain(second, (first.width, first.height))
                            elif ret == 2:
                                # Do nothing
                                pass

                        # Hstack the two
                        dst = Image.new('RGBA', (first.width + second.width, first.height))
                        dst.paste(first, (0, 0))
                        dst.paste(second, (first.width, 0))

                        # Save result
                        updatedPixmap = self.ImageToQPixmap(dst)
                        self.image_viewer.setImage(updatedPixmap, True, "HStack", "Tool", None, None)

        self.HStackToolButton.setChecked(False)

    def OnVStackToolButton(self, checked):
        if checked:
            if self.image_viewer._current_filename:

                pixmap = self.getCurrentLayerLatestPixmap()
                first = self.QPixmapToImage(pixmap)

                if pixmap:

                    # Open second image
                    filepath, _ = QFileDialog.getOpenFileName(self, "Open image file.")
                    if len(filepath) and os.path.isfile(filepath):
                        second = Image.open(filepath)

                        if first.width != second.width or first.height != second.height:
                            # The two images are of different size

                            # If the two images are not the exact same size
                            # Ask the user if they want to resize the first or second or leave as is
                            msgBox = QtWidgets.QMessageBox()
                            msgBox.setText('First Image is ' + str(first.width) + "x" + str(first.height) + '\n'
                                           'Second Image is ' + str(second.width) + "x" + str(second.height))
                            msgBox.addButton(QtWidgets.QPushButton('Resize First'), QtWidgets.QMessageBox.ButtonRole.YesRole)
                            msgBox.addButton(QtWidgets.QPushButton('Resize Second'), QtWidgets.QMessageBox.ButtonRole.NoRole)
                            msgBox.addButton(QtWidgets.QPushButton("Stack As Is"), QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
                            msgBox.addButton(QtWidgets.QPushButton('Cancel'), QtWidgets.QMessageBox.ButtonRole.RejectRole)
                            ret = msgBox.exec()

                            from PIL import ImageOps
                            
                            if ret == 3:
                                # Cancel operation
                                self.HStackToolButton.setChecked(False)
                                return
                            elif ret == 0:
                                # Resize first to match the size of second
                                first = ImageOps.contain(first, (second.width, second.height))
                            elif ret == 1:
                                # Resize second to match the size of first
                                second = ImageOps.contain(second, (first.width, first.height))
                            elif ret == 2:
                                # Do nothing
                                pass

                        # Vstack the two
                        dst = Image.new('RGBA', (first.width, first.height + second.height))
                        dst.paste(first, (0, 0))
                        dst.paste(second, (0, first.height))

                        # Save result
                        updatedPixmap = self.ImageToQPixmap(dst)
                        self.image_viewer.setImage(updatedPixmap, True, "VStack", "Tool", None, None)

        self.VStackToolButton.setChecked(False)

    def OnFlipLeftRightToolButton(self, checked):
        if checked:
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.transpose(Image.FLIP_LEFT_RIGHT)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Flip Left-Right", "Tool", None, None)
        self.FlipLeftRightToolButton.setChecked(False)

    def OnFlipTopBottomToolButton(self, checked):
        if checked:
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.transpose(Image.FLIP_TOP_BOTTOM)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Flip Top-Bottom", "Tool", None, None)
        self.FlipTopBottomToolButton.setChecked(False)

    def OnRectSelectToolButton(self, checked):
        self.EnableTool("select_rect") if checked else self.DisableTool("select_rect")

    def OnPathSelectToolButton(self, checked):
        self.EnableTool("select_path") if checked else self.DisableTool("select_path")

    def OnSpotRemovalToolButton(self, checked):
        self.EnableTool("spot_removal") if checked else self.DisableTool("spot_removal")

    @QtCore.pyqtSlot()
    def onBackgroundRemovalCompleted(self):
        output = self.currentTool.output
        if output is not None:
            # Save new pixmap
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "Background Removal")

        self.BackgroundRemovalToolButton.setChecked(False)
        del self.currentTool
        self.currentTool = None

    def OnBackgroundRemovalToolButton(self, checked):
        if checked and not self.currentTool:
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolBackgroundRemoval import QToolBackgroundRemoval
            self.currentTool = QToolBackgroundRemoval(None, image, self.onBackgroundRemovalCompleted)
            self.currentTool.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.currentTool.show()

    @QtCore.pyqtSlot()
    def onPortraitModeBackgroundBlurCompleted(self):
        backgroundRemoved = self.currentTool.backgroundRemoved
        backgroundRemoved = self.ImageToQPixmap(backgroundRemoved)

        output = self.currentTool.output
        if output is not None:

            # Depth prediction output
            # Blurred based on predicted depth
            updatedPixmap = self.ImageToQPixmap(output)

            # Draw foreground on top of the blurred background
            painter = QtGui.QPainter(updatedPixmap)
            painter.drawPixmap(QtCore.QPoint(), backgroundRemoved)
            painter.end()

            self.image_viewer.setImage(updatedPixmap, True, "Portrait Mode Background Blur")

        self.PortraitModeBackgroundBlurToolButton.setChecked(False)
        del self.currentTool
        self.currentTool = None

    def OnPortraitModeBackgroundBlurToolButton(self, checked):
        if checked and not self.currentTool:
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolPortraitMode import QToolPortraitMode

            # Run human segmentation with alpha matting
            self.currentTool = QToolPortraitMode(None, image, self.onPortraitModeBackgroundBlurCompleted)
            self.currentTool.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.currentTool.show()

    @QtCore.pyqtSlot()
    def onHumanSegmentationCompleted(self):
        output = self.currentTool.output
        if output is not None:
            # Save new pixmap
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "Human Segmentation")

        self.HumanSegmentationToolButton.setChecked(False)
        del self.currentTool
        self.currentTool = None

    def OnHumanSegmentationToolButton(self, checked):
        if checked and not self.currentTool:
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolHumanSegmentation import QToolHumanSegmentation
            self.currentTool = QToolHumanSegmentation(None, image, self.onHumanSegmentationCompleted)
            self.currentTool.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.currentTool.show()

    @QtCore.pyqtSlot()
    def OnColorizerCompleted(self):
        if self.currentTool:
            output = self.currentTool.output
            if output is not None:

                # Save new pixmap
                from PIL import Image
                output = Image.fromarray(output)
                updatedPixmap = self.ImageToQPixmap(output)
                self.image_viewer.setImage(updatedPixmap, True, "Colorizer")

            self.ColorizerToolButton.setChecked(False)
            del self.currentTool
            self.currentTool = None

    def OnColorizerToolButton(self, checked):
        if checked and not self.currentTool:
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolColorizer import QToolColorizer
            self.currentTool = QToolColorizer(None, image, self.OnColorizerCompleted)
            self.currentTool.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.currentTool.show()

    @QtCore.pyqtSlot()
    def onSuperResolutionCompleted(self):
        output = self.currentTool.output
        if output is not None:
            # Save new pixmap
            output = Image.fromarray(output)
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "Super Resolution")

        self.AnimeGanV2ToolButton.setChecked(False)
        del self.currentTool
        self.currentTool = None

    def OnSuperResolutionToolButton(self, checked):
        if checked and not self.currentTool:
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)
            from QToolSuperResolution import QToolSuperResolution
            self.currentTool = QToolSuperResolution(None, image, self.onSuperResolutionCompleted)
            self.currentTool.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.currentTool.show()

    @QtCore.pyqtSlot()
    def OnAnimeGanV2Completed(self):
        output = self.currentTool.output
        if output is not None:
            # Save new pixmap
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "Anime GAN v2")

        self.AnimeGanV2ToolButton.setChecked(False)
        del self.currentTool
        self.currentTool = None

    def OnAnimeGanV2ToolButton(self, checked):
        if checked and not self.currentTool:
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolAnimeGANv2 import QToolAnimeGANv2
            self.currentTool = QToolAnimeGANv2(None, image, self.OnAnimeGanV2Completed)
            self.currentTool.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.currentTool.show()

    @QtCore.pyqtSlot()
    def onWhiteBalanceCompleted(self):
        output = self.currentTool.output
        if output is not None:
            # Save new pixmap
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "White Balance")

        self.WhiteBalanceToolButton.setChecked(False)
        del self.currentTool
        self.currentTool = None

    def OnWhiteBalanceToolButton(self, checked):
        if checked and not self.currentTool:
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolWhiteBalance import QToolWhiteBalance
            self.currentTool = QToolWhiteBalance(None, image, self.onWhiteBalanceCompleted)
            self.currentTool.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.currentTool.show()

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

    def DisableAllTools(self):
        for _, value in self.tools.items():
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
        if self.image_viewer._current_filename != None:
            filename = self.image_viewer._current_filename
            filename = os.path.basename(filename)
            self.setWindowTitle(filename)
            # self.image_viewer.OriginalImage = self.image_viewer.pixmap()
            self.updateHistogram()
            self.updateColorPicker()
            self.resetSliderValues()

    def OnSave(self):
        if self.image_viewer._current_filename.lower().endswith(".nef"):
            # Cannot save pixmap as .NEF (yet)
            # so open SaveAs menu to export as PNG instead
            self.OnSaveAs()
        else:
            self.image_viewer.save()
   
    def OnSaveAs(self):
        name, ext = os.path.splitext(self.image_viewer._current_filename)
        dialog = QFileDialog()
        dialog.setDefaultSuffix("png")
        extension_filter = "Default (*.png);;BMP (*.bmp);;Icon (*.ico);;JPEG (*.jpeg *.jpg);;PBM (*.pbm);;PGM (*.pgm);;PNG (*.png);;PPM (*.ppm);;TIF (*.tif *.tiff);;WBMP (*.wbmp);;XBM (*.xbm);;XPM (*.xpm)"
        name = dialog.getSaveFileName(self, 'Save File', name + ".png", extension_filter)
        # self.image_viewer.OriginalImage = self.image_viewer.pixmap()
        self.image_viewer.save(name[0])
        filename = self.image_viewer._current_filename
        filename = os.path.basename(filename)
        self.setWindowTitle(filename)

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
            self.setWindowTitle(filename)
            # self.image_viewer.OriginalImage = self.image_viewer.pixmap()

            self.updateHistogram()
            self.updateColorPicker()
            self.resetSliderValues()

def main():
    app = QApplication(sys.argv)

    # app.setStyleSheet(open("darktheme.stylesheet").read())

    gui = Gui()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()