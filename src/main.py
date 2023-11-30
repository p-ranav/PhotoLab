from turtle import width
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
    QStatusBar
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
import QCurveWidget

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
        self.setWindowTitle('PhotoLab')
        self.setMinimumHeight(850)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

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
        self.HistogramContent = None
        self.ImageHistogramPlot.hide()

        ##############################################################################################
        ##############################################################################################
        # Color Picker
        ##############################################################################################
        ##############################################################################################
        self.color_picker = None

        ##############################################################################################
        ##############################################################################################
        # Adjustment Sliders
        ##############################################################################################
        ##############################################################################################

        # State of enhance sliders
        self.RedFactor = 100
        self.GreenFactor = 100
        self.BlueFactor = 100
        self.Temperature = 6000 # Kelvin, maps to (255,255,255), direct sunlight
        self.Color = 100
        self.Brightness = 100
        self.Contrast = 100
        self.Sharpness = 100

        # State of filter sliders
        self.GaussianBlurRadius = 0

        self.timer_id = -1
        self.sliderExplanationOfChange = None
        self.sliderTypeOfChange = None
        self.sliderValueOfChange = None
        self.sliderObjectOfChange = None

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
        self.SaveShortcut.activated.connect(self.OnSaveAs)

        self.SaveAsShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.SaveAsShortcut.activated.connect(self.OnSaveAs)

        self.UndoShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Z"), self)
        self.UndoShortcut.activated.connect(self.OnUndo)

        ##############################################################################################
        ##############################################################################################
        # Cursor Tool
        ##############################################################################################
        ##############################################################################################

        self.CursorToolButton = QToolButton(self)
        # self.CursorToolButton.setIconSize(QtCore.QSize(32, 32))
        self.CursorToolButton.setText("&Cursor")
        self.CursorToolButton.setToolTip("Cursor")
        self.setIconPixmapWithColor(self.CursorToolButton, "icons/cursor.svg")
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
        self.setIconPixmapWithColor(self.ColorPickerToolButton, "icons/color_picker.svg")
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
        self.setIconPixmapWithColor(self.PaintToolButton, "icons/paint.svg")
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
        self.setIconPixmapWithColor(self.FillToolButton, "icons/fill.svg")
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
        self.setIconPixmapWithColor(self.RectSelectToolButton, "icons/select_rect.svg")
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
        self.setIconPixmapWithColor(self.PathSelectToolButton, "icons/select_path.svg")
        self.PathSelectToolButton.setCheckable(True)
        self.PathSelectToolButton.toggled.connect(self.OnPathSelectToolButton)

        ##############################################################################################
        ##############################################################################################
        # Crop Tool
        ##############################################################################################
        ##############################################################################################

        self.CropToolButton = QToolButton(self)
        self.CropToolButton.setText("&Crop")
        self.setIconPixmapWithColor(self.CropToolButton, "icons/crop.svg")
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
        self.setIconPixmapWithColor(self.RotateLeftToolButton, "icons/rotate_left.svg")
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
        self.setIconPixmapWithColor(self.RotateRightToolButton, "icons/rotate_right.svg")
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
        self.setIconPixmapWithColor(self.HStackToolButton, "icons/hstack.svg")
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
        self.setIconPixmapWithColor(self.VStackToolButton, "icons/vstack.svg")
        self.VStackToolButton.setToolTip("Vertical Stack")
        self.VStackToolButton.setCheckable(True)
        self.VStackToolButton.toggled.connect(self.OnVStackToolButton)

        ##############################################################################################
        ##############################################################################################
        # Horizontal Panorama Tool
        ##############################################################################################
        ##############################################################################################

        self.LandscapePanoramaToolButton = QToolButton(self)
        self.LandscapePanoramaToolButton.setText("&Landscape Panorama")
        self.setIconPixmapWithColor(self.LandscapePanoramaToolButton, "icons/panorama.svg")
        self.LandscapePanoramaToolButton.setToolTip("Landscape Panorama")
        self.LandscapePanoramaToolButton.setCheckable(True)
        self.LandscapePanoramaToolButton.toggled.connect(self.OnLandscapePanoramaToolButton)

        ##############################################################################################
        ##############################################################################################
        # Flip Left Right Tool
        ##############################################################################################
        ##############################################################################################

        self.FlipLeftRightToolButton = QToolButton(self)
        self.FlipLeftRightToolButton.setText("&Flip Left-Right")
        self.setIconPixmapWithColor(self.FlipLeftRightToolButton, "icons/flip_left_right.svg")
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
        self.setIconPixmapWithColor(self.FlipTopBottomToolButton, "icons/flip_top_bottom.svg")
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
        self.setIconPixmapWithColor(self.SpotRemovalToolButton, "icons/spot_removal.svg")
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
        self.setIconPixmapWithColor(self.BlurToolButton, "icons/blur.svg")
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
        self.setIconPixmapWithColor(self.BackgroundRemovalToolButton, "icons/background_removal.svg")
        self.BackgroundRemovalToolButton.setCheckable(True)
        self.BackgroundRemovalToolButton.toggled.connect(self.OnBackgroundRemovalToolButton)

        ##############################################################################################
        ##############################################################################################
        # Portrait Mode Background Blur Tool
        ##############################################################################################
        ##############################################################################################

        self.PortraitModeBackgroundBlurToolButton = QToolButton(self)
        self.PortraitModeBackgroundBlurToolButton.setText("&Portrait Mode")
        self.PortraitModeBackgroundBlurToolButton.setToolTip("Portrait Mode")
        self.setIconPixmapWithColor(self.PortraitModeBackgroundBlurToolButton, "icons/portrait_mode.svg")
        self.PortraitModeBackgroundBlurToolButton.setCheckable(True)
        self.PortraitModeBackgroundBlurToolButton.toggled.connect(self.OnPortraitModeBackgroundBlurToolButton)

        ##############################################################################################
        ##############################################################################################
        # Grayscale Background Tool
        ##############################################################################################
        ##############################################################################################

        self.GrayscaleBackgroundToolButton = QToolButton(self)
        self.GrayscaleBackgroundToolButton.setText("&Grayscale Background")
        self.GrayscaleBackgroundToolButton.setToolTip("Grayscale Background")
        self.setIconPixmapWithColor(self.GrayscaleBackgroundToolButton, "icons/grayscale_background.svg")
        self.GrayscaleBackgroundToolButton.setCheckable(True)
        self.GrayscaleBackgroundToolButton.toggled.connect(self.OnGrayscaleBackgroundToolButton)

        ##############################################################################################
        ##############################################################################################
        # Human Segmentation Tool
        ##############################################################################################
        ##############################################################################################

        self.HumanSegmentationToolButton = QToolButton(self)
        self.HumanSegmentationToolButton.setText("&Human Segmentation")
        self.HumanSegmentationToolButton.setToolTip("Human Segmentation")
        self.setIconPixmapWithColor(self.HumanSegmentationToolButton, "icons/human_segmentation.svg")
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
        self.setIconPixmapWithColor(self.ColorizerToolButton, "icons/colorizer.svg")
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
        self.setIconPixmapWithColor(self.SuperResolutionToolButton, "icons/super_resolution.svg")
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
        self.setIconPixmapWithColor(self.AnimeGanV2ToolButton, "icons/anime.svg")
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
        self.setIconPixmapWithColor(self.WhiteBalanceToolButton, "icons/white_balance.svg")
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
        self.setIconPixmapWithColor(self.EraserToolButton, "icons/eraser.svg")
        self.EraserToolButton.setCheckable(True)
        self.EraserToolButton.toggled.connect(self.OnEraserToolButton)

        ##############################################################################################
        ##############################################################################################
        # Sliders Tool
        ##############################################################################################
        ##############################################################################################

        self.SlidersToolButton = QToolButton(self)
        self.SlidersToolButton.setText("&Sliders")
        self.SlidersToolButton.setToolTip("Sliders")
        self.setIconPixmapWithColor(self.SlidersToolButton, "icons/sliders.svg")
        self.SlidersToolButton.setCheckable(True)
        self.SlidersToolButton.toggled.connect(self.OnSlidersToolButton)

        ##############################################################################################
        ##############################################################################################
        # Curve Editor Tool
        ##############################################################################################
        ##############################################################################################

        self.CurveEditorToolButton = QToolButton(self)
        self.CurveEditorToolButton.setText("&Curves")
        self.CurveEditorToolButton.setToolTip("Curves")
        self.setIconPixmapWithColor(self.CurveEditorToolButton, "icons/curve.svg")
        self.CurveEditorToolButton.setCheckable(True)
        self.CurveEditorToolButton.toggled.connect(self.OnCurveEditorToolButton)

        ##############################################################################################
        ##############################################################################################
        # Instagram Filters Tool
        ##############################################################################################
        ##############################################################################################

        self.InstagramFiltersToolButton = QToolButton(self)
        self.InstagramFiltersToolButton.setText("&Instagram Filters")
        self.InstagramFiltersToolButton.setToolTip("Instagram Filters")
        self.setIconPixmapWithColor(self.InstagramFiltersToolButton, "icons/instagram.svg")
        self.InstagramFiltersToolButton.setCheckable(True)
        self.InstagramFiltersToolButton.toggled.connect(self.OnInstagramFiltersToolButton)

        ##############################################################################################
        ##############################################################################################
        # Histogram Viewer Tool
        ##############################################################################################
        ##############################################################################################

        self.HistogramToolButton = QToolButton(self)
        self.HistogramToolButton.setText("&Histogram")
        self.HistogramToolButton.setToolTip("Histogram")
        self.setIconPixmapWithColor(self.HistogramToolButton, "icons/histogram.svg")
        self.HistogramToolButton.setCheckable(True)
        self.HistogramToolButton.toggled.connect(self.OnHistogramToolButton)

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
            "histogram": {
                "tool": "HistogramToolButton",
                "var": '_isShowingHistogram'
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
            "eraser": {
                "tool": "EraserToolButton",
                "var": '_isErasing'
            },
            "blur": {
                "tool": "BlurToolButton",
                "var": '_isBlurring'
            },
            "instagram_filters": {
                "tool": "InstagramFiltersToolButton",
                "var": '_isApplyingFilter'
            },
        }

        self.ToolbarDockWidget = QtWidgets.QDockWidget("Tools")
        self.ToolbarDockWidget.setTitleBarWidget(QtWidgets.QWidget())
        ToolbarContent = QtWidgets.QWidget()
        ToolbarLayout = QFlowLayout(ToolbarContent)
        ToolbarLayout.setSpacing(0)

        self.ToolButtons = [
            self.CursorToolButton, self.ColorPickerToolButton, self.PaintToolButton, self.EraserToolButton, 
            self.FillToolButton, self.RectSelectToolButton, self.PathSelectToolButton, self.CropToolButton, 
            self.SlidersToolButton, self.HistogramToolButton, self.CurveEditorToolButton, 
            self.SpotRemovalToolButton, self.BlurToolButton,

            self.RotateLeftToolButton, self.RotateRightToolButton,
            self.HStackToolButton, self.VStackToolButton, 
            self.FlipLeftRightToolButton, self.FlipTopBottomToolButton,
            self.LandscapePanoramaToolButton,

            self.InstagramFiltersToolButton,
            self.WhiteBalanceToolButton, self.BackgroundRemovalToolButton, self.HumanSegmentationToolButton, self.GrayscaleBackgroundToolButton,
            self.PortraitModeBackgroundBlurToolButton, 
            self.ColorizerToolButton, self.SuperResolutionToolButton, self.AnimeGanV2ToolButton, 
        ]

        for button in self.ToolButtons:
            button.setIconSize(QtCore.QSize(20, 20))
            button.setEnabled(False)
            button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            ToolbarLayout.addWidget(button)

        ToolbarContent.setLayout(ToolbarLayout)
        self.ToolbarDockWidget.setWidget(ToolbarContent)

        ##############################################################################################
        ##############################################################################################
        # Right Dock
        ##############################################################################################
        ##############################################################################################

        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.ToolbarDockWidget)
        self.ToolbarDockWidget.setFloating(True)
        self.ToolbarDockWidget.setGeometry(QtCore.QRect(20, 20, 90, 600))

        ##############################################################################################
        ##############################################################################################
        # Show Window
        ##############################################################################################
        ##############################################################################################

        self.initImageViewer()
        self.ToolbarDockWidget.setParent(self.image_viewer)
        self.showMaximized()

        self.threadpool = QtCore.QThreadPool()
        self.sliderChangedPixmap = None
        self.sliderExplanationOfChange = None
        self.sliderTypeOfChange = None
        self.sliderValueOfChange = None
        self.sliderObjectOfChange = None
        self.sliderChangeSignal.connect(self.onUpdateImageCompleted)
        self.sliderWorkers = []

        self.resizeDockWidgets()

    def setIconPixmapWithColor(self, button, filename, findColor='black', newColor='white'):
        pixmap = QPixmap(filename)
        mask = pixmap.createMaskFromColor(QtGui.QColor(findColor), Qt.MaskMode.MaskOutColor)
        pixmap.fill((QtGui.QColor(newColor)))
        pixmap.setMask(mask)
        button.setIcon(QtGui.QIcon(pixmap))

    def setToolButtonStyleChecked(self, button):
        button.setStyleSheet('''
            border-color: rgb(22, 22, 22);
            background-color: rgb(22, 22, 22);
            border-style: solid;
        ''')

    def setToolButtonStyleUnchecked(self, button):
        button.setStyleSheet("")

    def resizeDockWidgets(self):
        pass
        # self.resizeDocks([self.ToolbarDockWidget], [200], Qt.Orientation.Vertical)

    @QtCore.pyqtSlot(int, str)
    def updateProgressBar(self, e, label):
        self.progressBar.setValue(e)
        self.progressBarLabel.setText(label)

    def initImageViewer(self):
        self.image_viewer = QtImageViewer(self)
        self.layerListDock = None
        self.CurvesDock = None

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

        # Set the central widget of the Window. Widget will expand
        # to take up all the space in the window by default.
        self.setCentralWidget(self.image_viewer)

    def resetSliderValues(self):
        # State of enhance sliders
        self.RedFactor = 100
        self.BlueFactor = 100
        self.GreenFactor = 100
        self.Temperature = 6000
        self.Color = 100
        self.Brightness = 100
        self.Contrast = 100
        self.Sharpness = 100
        self.GaussianBlurRadius = 0

        self.RedColorSlider.setValue(self.RedFactor)        
        self.GreenColorSlider.setValue(self.GreenFactor)        
        self.BlueColorSlider.setValue(self.BlueFactor) 
        self.TemperatureSlider.setValue(self.Temperature)
        self.ColorSlider.setValue(self.Color)        
        self.BrightnessSlider.setValue(self.Brightness)
        self.ContrastSlider.setValue(self.Contrast)
        self.SharpnessSlider.setValue(self.Sharpness)
        self.GaussianBlurSlider.setValue(self.GaussianBlurRadius)

    def getCurrentLayerLatestPixmap(self):
        return self.image_viewer.getCurrentLayerLatestPixmap()

    def processSliderChange(self, explanationOfChange, typeOfChange, valueOfChange, objectOfChange):
        self.sliderExplanationOfChange = explanationOfChange
        self.sliderTypeOfChange = typeOfChange
        self.sliderValueOfChange = valueOfChange
        self.sliderObjectOfChange = objectOfChange

        if self.timer_id != -1:
            self.killTimer(self.timer_id)

        self.timer_id = self.startTimer(500)

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

    def AddTemperatureSlider(self, layout):
        self.TemperatureSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.TemperatureSlider.setRange(0, 12000)
        layout.addRow("Temperature", self.TemperatureSlider)

        # Default value of the Temperature slider
        self.TemperatureSlider.setValue(6000)

        self.TemperatureSlider.valueChanged.connect(self.OnTemperatureChanged)

    def OnTemperatureChanged(self, value):
        self.Temperature = value
        self.processSliderChange("Temperature", "Slider", value, "TemperatureSlider")

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
            self.image_viewer.setImage(self.sliderChangedPixmap, False, self.sliderExplanationOfChange, 
                                       self.sliderTypeOfChange, self.sliderValueOfChange, self.sliderObjectOfChange)
            self.UpdateHistogramPlot()

    def timerEvent(self, event):
        self.killTimer(self.timer_id)
        self.timer_id = -1

        Pixmap = self.image_viewer.getCurrentLayerLatestPixmap()
        OriginalPixmap = Pixmap.copy()

        # TODO: If a selection is active
        # Only apply changes to the selected region
        if self.image_viewer._isSelectingRect:
            print(self.image_viewer._selectRect)
            Pixmap = Pixmap.copy(self.image_viewer._selectRect.toRect())
        elif self.image_viewer._isSelectingPath:
            Pixmap = self.image_viewer.getSelectedRegionAsPixmap()

        if Pixmap:
            if self.RedFactor != 100:
                Pixmap = self.UpdateReds(Pixmap, float(self.RedFactor / 100))
            if self.GreenFactor != 100:
                Pixmap = self.UpdateGreens(Pixmap, float(self.GreenFactor / 100))
            if self.BlueFactor != 100:
                Pixmap = self.UpdateBlues(Pixmap, float(self.BlueFactor / 100))
            if self.Temperature != 6000:
                import AdjustTemperature
                img = self.QPixmapToImage(Pixmap)
                import numpy as np
                import cv2
                arr = np.asarray(img)
                b, g, r, a = cv2.split(arr)
                img = Image.fromarray(np.dstack((b, g, r)))

                def FindClosest(lst, K):
                    return lst[min(range(len(lst)), key = lambda i: abs(lst[i]-K))]

                img = AdjustTemperature.convert_temp(img, FindClosest(list(AdjustTemperature.kelvin_table.keys()), self.Temperature))
                img = np.asarray(img)
                img = np.dstack((img, a))
                img = Image.fromarray(img)
                Pixmap = self.ImageToQPixmap(img)
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

            if self.image_viewer._isSelectingRect:
                painter = QtGui.QPainter(OriginalPixmap)
                selectRect = self.image_viewer._selectRect
                point = QtCore.QPoint(int(selectRect.x()), int(selectRect.y()))
                painter.drawPixmap(point, Pixmap)
                painter.end()
                Pixmap = OriginalPixmap
            elif self.image_viewer._isSelectingPath:
                painter = QtGui.QPainter(OriginalPixmap)
                painter.drawPixmap(QtCore.QPoint(), Pixmap)
                painter.end()
                Pixmap = OriginalPixmap

            self.sliderChangedPixmap = Pixmap
            self.sliderExplanationOfChange = self.sliderExplanationOfChange
            self.sliderTypeOfChange = self.sliderTypeOfChange
            self.sliderValueOfChange = self.sliderValueOfChange
            self.sliderObjectOfChange = self.sliderObjectOfChange
            self.sliderChangeSignal.emit()

    def RemoveRenderedCursor(self):
        # The cursor overlay is being rendered in the view
        # Remove it
        if any([self.image_viewer._isBlurring, self.image_viewer._isRemovingSpots]):
            pixmap = self.getCurrentLayerLatestPixmap()
            self.image_viewer.setImage(pixmap, False)

    def InitTool(self):
        self.RemoveRenderedCursor()

    def OnCursorToolButton(self, checked):
        self.InitTool()
        self.EnableTool("cursor") if checked else self.DisableTool("cursor")

    def OnColorPickerToolButton(self, checked):
        if checked:
            self.InitTool()
            class ColorPickerWidget(QtWidgets.QWidget):
                def __init__(self, parent, mainWindow):
                    QtWidgets.QWidget.__init__(self, parent)
                    self.parent = parent
                    self.closed = False
                    self.mainWindow = mainWindow

                def closeEvent(self, event):
                    self.destroyed.emit()
                    event.accept()
                    self.closed = True
                    self.mainWindow.DisableTool("color_picker")

            self.ColorPickerContent = ColorPickerWidget(None, self)
            ColorPickerLayout = QtWidgets.QVBoxLayout(self.ColorPickerContent)
            self.color_picker = QColorPicker(self.ColorPickerContent, rgb=(173, 36, 207))
            self.image_viewer.ColorPicker = self.color_picker
            ColorPickerLayout.addWidget(self.color_picker)
            self.EnableTool("color_picker") if checked else self.DisableTool("color_picker")

            self.ColorPickerContent.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
            self.ColorPickerContent.show()
            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.ColorPickerContent.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.DisableTool("color_picker")
            self.ColorPickerContent.hide()

    def OnHistogramToolButton(self, checked):
        if checked:
            self.InitTool()
            class HistogrmaWidget(QtWidgets.QWidget):
                def __init__(self, parent, mainWindow):
                    QtWidgets.QWidget.__init__(self, parent)
                    self.parent = parent
                    self.closed = False
                    self.mainWindow = mainWindow

                def closeEvent(self, event):
                    self.destroyed.emit()
                    event.accept()
                    self.closed = True
                    self.mainWindow.DisableTool("histogram")
            if not self.HistogramContent:
                self.HistogramContent = HistogrmaWidget(None, self)
                self.HistogramLayout = QtWidgets.QVBoxLayout(self.HistogramContent)
                self.HistogramLayout.addWidget(self.ImageHistogramPlot)
                self.HistogramContent.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
            self.ImageHistogramPlot.show()
            self.HistogramContent.show()
            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.HistogramContent.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.DisableTool("histogram")
            self.HistogramContent.hide()
            #del self.HistogramContent
            #del self.HistogramLayout

    def OnPaintToolButton(self, checked):
        if checked:
            self.InitTool()
            class ColorPickerWidget(QtWidgets.QWidget):
                def __init__(self, parent, mainWindow):
                    QtWidgets.QWidget.__init__(self, parent)
                    self.parent = parent
                    self.closed = False
                    self.mainWindow = mainWindow

                def closeEvent(self, event):
                    self.destroyed.emit()
                    event.accept()
                    self.closed = True
                    self.mainWindow.DisableTool("paint")

            self.PaintContent = ColorPickerWidget(None, self)
            ColorPickerLayout = QtWidgets.QVBoxLayout(self.PaintContent)
            self.color_picker = QColorPicker(self.PaintContent, rgb=(173, 36, 207))
            self.image_viewer.ColorPicker = self.color_picker
            ColorPickerLayout.addWidget(self.color_picker)
            self.EnableTool("paint") if checked else self.DisableTool("paint")

            self.PaintContent.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
            self.PaintContent.show()
            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.PaintContent.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.DisableTool("paint")
            self.PaintContent.hide()

    def OnFillToolButton(self, checked):
        if checked:
            self.InitTool()
            class ColorPickerWidget(QtWidgets.QWidget):
                def __init__(self, parent, mainWindow):
                    QtWidgets.QWidget.__init__(self, parent)
                    self.parent = parent
                    self.closed = False
                    self.mainWindow = mainWindow

                def closeEvent(self, event):
                    self.destroyed.emit()
                    event.accept()
                    self.closed = True
                    self.mainWindow.DisableTool("fill")

            self.FillContent = ColorPickerWidget(None, self)
            ColorPickerLayout = QtWidgets.QVBoxLayout(self.FillContent)
            self.color_picker = QColorPicker(self.FillContent, rgb=(173, 36, 207))
            self.image_viewer.ColorPicker = self.color_picker
            ColorPickerLayout.addWidget(self.color_picker)
            self.EnableTool("fill") if checked else self.DisableTool("fill")

            self.FillContent.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
            self.FillContent.show()
            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.FillContent.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.DisableTool("fill")
            self.FillContent.hide()

    def OnCropToolButton(self, checked):
        if checked:
            self.InitTool()
            self.image_viewer._isCropping = True

    def OnRotateLeftToolButton(self, checked):
        if checked:
            self.InitTool()
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.rotate(90, expand=True)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Rotate Left", "Tool", None, None)
        self.RotateLeftToolButton.setChecked(False)

    def OnRotateRightToolButton(self, checked):
        if checked:
            self.InitTool()
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.rotate(-90, expand=True)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Rotate Right", "Tool", None, None)
        self.RotateRightToolButton.setChecked(False)

    def OnHStackToolButton(self, checked):
        if checked:
            self.InitTool()
            if self.image_viewer._current_filename:

                pixmap = self.getCurrentLayerLatestPixmap()
                first = self.QPixmapToImage(pixmap)

                if pixmap:

                    # Open second image
                    filepath, _ = QFileDialog.getOpenFileName(self, "Open Image")
                    if len(filepath) and os.path.isfile(filepath):
                        second = Image.open(filepath)

                        if first.width != second.width or first.height != second.height:
                            # The two images are of different size

                            # If the two images are not the exact same size
                            # Ask the user if they want to resize the first or second or leave as is
                            msgBox = QtWidgets.QMessageBox()
                            msgBox.setText('First Image is ' + str(first.width) + "x" + str(first.height) + '\n'
                                           'Second Image is ' + str(second.width) + "x" + str(second.height))

                            resizeFirst = QtWidgets.QPushButton('Resize First')
                            resizeSecond = QtWidgets.QPushButton('Resize Second')
                            stackAsIs = QtWidgets.QPushButton("Stack As Is")
                            cancel = QtWidgets.QPushButton('Cancel')

                            for button in [resizeFirst, resizeSecond, stackAsIs, cancel]:
                                button.setStyleSheet('''
                                    border: 1px solid;
                                    background-color: rgb(44, 44, 44);
                                    height: 30px;
                                    width: 100px;
                                ''')

                            msgBox.addButton(resizeFirst, QtWidgets.QMessageBox.ButtonRole.YesRole)
                            msgBox.addButton(resizeSecond, QtWidgets.QMessageBox.ButtonRole.NoRole)
                            msgBox.addButton(stackAsIs, QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
                            msgBox.addButton(cancel, QtWidgets.QMessageBox.ButtonRole.RejectRole)
                            msgBox.setStyleSheet('''
                                background-color: rgb(22, 22, 22);
                            ''')
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
            self.InitTool()
            if self.image_viewer._current_filename:

                pixmap = self.getCurrentLayerLatestPixmap()
                first = self.QPixmapToImage(pixmap)

                if pixmap:

                    # Open second image
                    filepath, _ = QFileDialog.getOpenFileName(self, "Open Image")
                    if len(filepath) and os.path.isfile(filepath):
                        second = Image.open(filepath)

                        if first.width != second.width or first.height != second.height:
                            # The two images are of different size

                            # If the two images are not the exact same size
                            # Ask the user if they want to resize the first or second or leave as is
                            msgBox = QtWidgets.QMessageBox()
                            msgBox.setText('First Image is ' + str(first.width) + "x" + str(first.height) + '\n'
                                           'Second Image is ' + str(second.width) + "x" + str(second.height))

                            resizeFirst = QtWidgets.QPushButton('Resize First')
                            resizeSecond = QtWidgets.QPushButton('Resize Second')
                            stackAsIs = QtWidgets.QPushButton("Stack As Is")
                            cancel = QtWidgets.QPushButton('Cancel')

                            for button in [resizeFirst, resizeSecond, stackAsIs, cancel]:
                                button.setStyleSheet('''
                                    border: 1px solid;
                                    background-color: rgb(44, 44, 44);
                                    height: 30px;
                                    width: 100px;
                                ''')

                            msgBox.addButton(resizeFirst, QtWidgets.QMessageBox.ButtonRole.YesRole)
                            msgBox.addButton(resizeSecond, QtWidgets.QMessageBox.ButtonRole.NoRole)
                            msgBox.addButton(stackAsIs, QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
                            msgBox.addButton(cancel, QtWidgets.QMessageBox.ButtonRole.RejectRole)
                            msgBox.setStyleSheet('''
                                background-color: rgb(22, 22, 22);
                            ''')
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

    def OnLandscapePanoramaToolButton(self, checked):
        if checked:
            self.InitTool()
            if self.image_viewer._current_filename:

                pixmap = self.getCurrentLayerLatestPixmap()
                first = self.QPixmapToImage(pixmap)

                if pixmap:

                    # Open second image
                    filepath, _ = QFileDialog.getOpenFileName(self, "Open Image")
                    if len(filepath) and os.path.isfile(filepath):
                        import cv2
                        second = cv2.imread(filepath)

                        # Stitch the pair of images
                        import ImageStitching
                        import numpy as np
                        import cv2
                        first = np.asarray(first)
                        print(first.shape, second.shape)
                        b1, g1, r1, _ = cv2.split(np.asarray(first))
                        dst = None
                        try:
                            dst = ImageStitching.stitch_image_pair(np.dstack((r1, g1, b1)), second, stitch_direc=1)
                        except ImageStitching.NotEnoughMatchPointsError as e:
                            # show dialog with error
                            pass
                        
                        if dst is not None:
                            dst = cv2.cvtColor(dst, cv2.COLOR_BGR2RGB)

                            print(dst.shape)
                            dst = Image.fromarray(dst).convert("RGBA")

                            # Save result
                            updatedPixmap = self.ImageToQPixmap(dst)
                            self.image_viewer.setImage(updatedPixmap, True, "Landscape Panorama", "Tool", None, None)
        self.LandscapePanoramaToolButton.setChecked(False)

    def OnFlipLeftRightToolButton(self, checked):
        if checked:
            self.InitTool()
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Flip Left-Right", "Tool", None, None)
        self.FlipLeftRightToolButton.setChecked(False)

    def OnFlipTopBottomToolButton(self, checked):
        if checked:
            self.InitTool()
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Flip Top-Bottom", "Tool", None, None)
        self.FlipTopBottomToolButton.setChecked(False)

    def OnRectSelectToolButton(self, checked):
        self.InitTool()
        self.EnableTool("select_rect") if checked else self.DisableTool("select_rect")

    def OnPathSelectToolButton(self, checked):
        self.InitTool()
        self.EnableTool("select_path") if checked else self.DisableTool("select_path")

    def OnSpotRemovalToolButton(self, checked):
        self.InitTool()
        self.EnableTool("spot_removal") if checked else self.DisableTool("spot_removal")

    @QtCore.pyqtSlot()
    def onBackgroundRemovalCompleted(self, tool):
        output = tool.output
        if output is not None:
            # Save new pixmap
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "Background Removal")

        self.BackgroundRemovalToolButton.setChecked(False)
        del tool
        tool = None

    def OnBackgroundRemovalToolButton(self, checked):
        if checked:
            self.InitTool()
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolBackgroundRemoval import QToolBackgroundRemoval
            widget = QToolBackgroundRemoval(None, image, self.onBackgroundRemovalCompleted)
            widget.show()

    @QtCore.pyqtSlot()
    def onPortraitModeBackgroundBlurCompleted(self, tool):
        backgroundRemoved = None
        if tool.backgroundRemoved:
            backgroundRemoved = tool.backgroundRemoved
            backgroundRemoved = self.ImageToQPixmap(backgroundRemoved)

        output = tool.output
        if output is not None and backgroundRemoved is not None:

            # Depth prediction output
            # Blurred based on predicted depth
            updatedPixmap = self.ImageToQPixmap(output)

            # Draw foreground on top of the blurred background
            painter = QtGui.QPainter(updatedPixmap)
            painter.drawPixmap(QtCore.QPoint(), backgroundRemoved)
            painter.end()

            self.image_viewer.setImage(updatedPixmap, True, "Portrait Mode Background Blur")

        self.PortraitModeBackgroundBlurToolButton.setChecked(False)
        del tool
        tool = None

    def OnPortraitModeBackgroundBlurToolButton(self, checked):
        if checked:
            self.InitTool()
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolPortraitMode import QToolPortraitMode

            # Run human segmentation with alpha matting
            widget = QToolPortraitMode(None, image, self.onPortraitModeBackgroundBlurCompleted)
            widget.show()

    @QtCore.pyqtSlot()
    def onGrayscaleBackgroundCompleted(self, tool):
        foreground = None
        foregroundPixmap = None

        if tool.output:
            foreground = tool.output
            foregroundPixmap = self.ImageToQPixmap(foreground)

        background = self.QPixmapToImage(self.getCurrentLayerLatestPixmap())
        if foreground is not None and background is not None:

            # Depth prediction output
            # Blurred based on predicted depth
            # Grayscale the background
            from PIL import ImageOps
            background = ImageOps.grayscale(background)
            backgroundPixmap = self.ImageToQPixmap(background)

            # Draw foreground on top of the blurred background
            painter = QtGui.QPainter(backgroundPixmap)
            painter.drawPixmap(QtCore.QPoint(), foregroundPixmap)
            painter.end()

            self.image_viewer.setImage(backgroundPixmap, True, "Grayscale Background")

        self.GrayscaleBackgroundToolButton.setChecked(False)
        del tool
        tool = None

    def OnGrayscaleBackgroundToolButton(self, checked):
        if checked:
            self.InitTool()
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolGrayscaleBackground import QToolGrayscaleBackground

            # Run human segmentation with alpha matting
            widget = QToolGrayscaleBackground(None, image, self.onGrayscaleBackgroundCompleted)
            widget.show()

    @QtCore.pyqtSlot()
    def onHumanSegmentationCompleted(self, tool):
        output = tool.output
        if output is not None:
            # Save new pixmap
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "Human Segmentation")

        self.HumanSegmentationToolButton.setChecked(False)
        del tool
        tool = None

    def OnHumanSegmentationToolButton(self, checked):
        if checked:
            self.InitTool()
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolHumanSegmentation import QToolHumanSegmentation
            widget = QToolHumanSegmentation(None, image, self.onHumanSegmentationCompleted)
            widget.show()

    @QtCore.pyqtSlot()
    def OnColorizerCompleted(self, tool):
        if tool:
            output = tool.output
            if output is not None:

                # Show Interactive Colorization widget
                currentPixmap = self.getCurrentLayerLatestPixmap()
                image = self.QPixmapToImage(currentPixmap)
                import numpy as np
                import cv2
                import torch

                image = np.asarray(image)
                print("Original image size", image.shape)
                h, w, c = image.shape
                max_width = max(h, w)
                b, g, r, a = cv2.split(image)

                import ColorizerMain
                colorizerWidget = ColorizerMain.IColoriTUI(
                    None,
                    viewer=self.image_viewer,
                    alphaChannel=a,
                    color_model=output, 
                    im_bgr=np.dstack((b, g, r)),
                    load_size=224, win_size=720, device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
                colorizerWidget.setWindowModality(Qt.WindowModality.ApplicationModal)

                colorizerWidget.setStyleSheet('''
                    background-color: rgb(44, 44, 44)
                ''')

                colorizerWidget.showMaximized()

                # Create a local event loop for this widget
                loop = QtCore.QEventLoop()
                colorizerWidget.destroyed.connect(loop.quit)
                loop.exec() # wait

            self.ColorizerToolButton.setChecked(False)
            del tool
            tool = None

    def OnColorizerToolButton(self, checked):
        if checked:
            self.InitTool()
            from QToolColorizer import QToolColorizer
            widget = QToolColorizer(None, None, self.OnColorizerCompleted)
            widget.show()

    @QtCore.pyqtSlot()
    def onSuperResolutionCompleted(self, tool):
        output = tool.output
        if output is not None:
            # Save new pixmap
            output = Image.fromarray(output)
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "Super Resolution")

        self.SuperResolutionToolButton.setChecked(False)
        del tool
        tool = None

    def OnSuperResolutionToolButton(self, checked):
        if checked:
            self.InitTool()
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolSuperResolution import QToolSuperResolution
            widget = QToolSuperResolution(None, image, self.onSuperResolutionCompleted)
            widget.show()

    @QtCore.pyqtSlot()
    def OnAnimeGanV2Completed(self, tool):
        output = tool.output
        if output is not None:
            # Save new pixmap
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "Anime GAN v2")

        self.AnimeGanV2ToolButton.setChecked(False)
        del tool
        tool = None

    def OnAnimeGanV2ToolButton(self, checked):
        if checked:
            self.InitTool()
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolAnimeGANv2 import QToolAnimeGANv2
            widget = QToolAnimeGANv2(None, image, self.OnAnimeGanV2Completed)
            widget.show()

    @QtCore.pyqtSlot()
    def onWhiteBalanceCompleted(self, tool):
        output = tool.output
        if output is not None:
            # Save new pixmap
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "White Balance")

        self.WhiteBalanceToolButton.setChecked(False)
        del tool
        tool = None

    def OnWhiteBalanceToolButton(self, checked):
        if checked:
            self.InitTool()
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolWhiteBalance import QToolWhiteBalance
            widget = QToolWhiteBalance(None, image, self.onWhiteBalanceCompleted)
            widget.show()

    def OnSlidersToolButton(self, checked):
        if checked:
            self.InitTool()
            class SlidersScrollWidget(QtWidgets.QScrollArea):
                def __init__(self, parent, mainWindow):
                    QtWidgets.QScrollArea.__init__(self, parent)
                    self.parent = parent
                    self.closed = False
                    self.mainWindow = mainWindow

                def closeEvent(self, event):
                    self.destroyed.emit()
                    event.accept()
                    self.closed = True
                    self.mainWindow.SlidersToolButton.setChecked(False)
                    self.mainWindow.image_viewer.setImage(self.mainWindow.image_viewer.pixmap(), True, "Sliders")

            self.slidersScroll = SlidersScrollWidget(None, self)
            self.slidersContent = QtWidgets.QWidget()
            self.slidersScroll.setWidget(self.slidersContent)
            self.slidersScroll.setWidgetResizable(True)
            self.slidersLayout = QtWidgets.QFormLayout(self.slidersContent)

            # Filter sliders
            filter_label = QLabel("Basic")
            self.slidersLayout.addWidget(filter_label)
        
            # Enhance sliders
            self.AddRedColorSlider(self.slidersLayout)
            self.AddGreenColorSlider(self.slidersLayout)
            self.AddBlueColorSlider(self.slidersLayout)
            self.AddTemperatureSlider(self.slidersLayout)
            self.AddColorSlider(self.slidersLayout)
            self.AddBrightnessSlider(self.slidersLayout)
            self.AddContrastSlider(self.slidersLayout)
            self.AddSharpnessSlider(self.slidersLayout)

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
            self.slidersLayout.addWidget(filter_label)

            # State of filter sliders
            self.GaussianBlurRadius = 0

            self.AddGaussianBlurSlider(self.slidersLayout)

            self.slidersScroll.setStyleSheet('''
                background-color: rgb(44, 44, 44);
            ''')
            self.slidersScroll.setMinimumWidth(300)
            self.slidersScroll.setWindowTitle("Adjust")

            self.slidersScroll.show()

            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.slidersScroll.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.slidersScroll.hide()

        self.SlidersToolButton.setChecked(False)

    def OnCurveEditorToolButton(self, checked):
        if checked:
            self.InitTool()
            self.CurveWidget = QCurveWidget.QCurveWidget(None, self.image_viewer)
            self.CurveWidget.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.CurveWidget.show()

            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.CurveWidget.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.CurveWidget.hide()

        self.CurveEditorToolButton.setChecked(False)

    def OnInstagramFiltersToolButton(self, checked):
        if checked:
            self.InitTool()

            class QInstagramToolDockWidget(QtWidgets.QDockWidget):
                def __init__(self, parent, mainWindow):
                    QtWidgets.QDockWidget.__init__(self, parent)
                    self.parent = parent
                    self.closed = False
                    self.mainWindow = mainWindow
                    self.setWindowTitle("Filters")

                def closeEvent(self, event):
                    self.destroyed.emit()
                    event.accept()
                    self.closed = True
                    self.mainWindow.InstagramFiltersToolButton.setChecked(False)
                    self.mainWindow.image_viewer.setImage(self.mainWindow.image_viewer.pixmap(), True, "Instagram Filters")

            self.EnableTool("instagram_filters") if checked else self.DisableTool("instagram_filters")
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolInstagramFilters import QToolInstagramFilters
            tool = QToolInstagramFilters(self, image)
            self.filtersDock = QInstagramToolDockWidget(None, self)
            self.filtersDock.setWidget(tool)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.filtersDock)

            widget = self.filtersDock

            widget.show()

            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.filtersDock.destroyed.connect(loop.quit)
            tool.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.DisableTool("instagram_filters")
            self.filtersDock.hide()

    def OnEraserToolButton(self, checked):
        self.InitTool()
        self.EnableTool("eraser") if checked else self.DisableTool("eraser")

    def OnBlurToolButton(self, checked):
        self.InitTool()
        self.EnableTool("blur") if checked else self.DisableTool("blur")

    def EnableTool(self, tool):
        for key, value in self.tools.items():
            if key == tool:
                button = getattr(self, value["tool"])
                button.setChecked(True)
                self.setToolButtonStyleChecked(button)
                setattr(self.image_viewer, value["var"], True)
            else:
                # Disable the other tools
                button = getattr(self, value["tool"])
                button.setChecked(False)
                self.setToolButtonStyleUnchecked(button)
                setattr(self.image_viewer, value["var"], False)
                if "destructor" in value:
                    getattr(self.image_viewer, value["destructor"])()

    def DisableTool(self, tool):
        value = self.tools[tool]
        button = getattr(self, value["tool"])
        button.setChecked(False)
        self.setToolButtonStyleUnchecked(button)
        setattr(self.image_viewer, value["var"], False)
        if "destructor" in value:
            getattr(self.image_viewer, value["destructor"])()

        if tool in ["blur", "spot_removal"]:
            # The cursor overlay is being rendered in the view
            # Remove it
            pixmap = self.getCurrentLayerLatestPixmap()
            self.image_viewer.setImage(pixmap, False)

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

    def OnOpen(self):
        # Load an image file to be displayed (will popup a file dialog).
        self.image_viewer.numLayersCreated = 1
        self.image_viewer.currentLayer = 0
        self.image_viewer.layerHistory = {
            0: []
        }
        self.image_viewer.open()
        if self.image_viewer._current_filename != None:
            size = self.image_viewer.currentPixmapSize()
            if size:
                w, h = size.width(), size.height()
                self.statusBar.showMessage(str(w) + "x" + str(h))
            self.InitTool()
            self.DisableAllTools()
            filename = self.image_viewer._current_filename
            filename = os.path.basename(filename)
            # self.image_viewer.OriginalImage = self.image_viewer.pixmap()
            self.updateHistogram()
            self.createLayersDock()
            for button in self.ToolButtons:
                button.setEnabled(True)

    def createLayersDock(self):
        if self.layerListDock:
            self.removeDockWidget(self.layerListDock)
            self.layerListDock.layerButtons = []
            self.layerListDock.numLayers = 1
            self.layerListDock.currentLayer = 0

        from QLayerList import QLayerList
        self.layerListDock = QLayerList("Layers", self)
        self.layerListDock.setTitleBarWidget(QtWidgets.QWidget())
        self.layerListDock.setFixedWidth(170)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.layerListDock)
        self.image_viewer.layerListDock = self.layerListDock

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
        self.image_viewer.save(name[0])
        filename = self.image_viewer._current_filename
        filename = os.path.basename(filename)

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
            # self.image_viewer.OriginalImage = self.image_viewer.pixmap()

            self.updateHistogram()
            self.createLayersDock()
            for button in self.ToolButtons:
                button.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    gui = Gui()
    app.setStyleSheet('''
    QWidget {
        background-color: rgb(44, 44, 44);
        color: white;
    }
    QMainWindow { 
        background-color: rgb(44, 44, 44); 
    }
    QGraphicsView { 
        background-color: rgb(22, 22, 22); 
    }
    QDockWidget { 
        background-color: rgb(44, 44, 44); 
    }
    QToolButton {
        border: none;
        color: white;
        background-color: rgb(44, 44, 44);
    }
    QToolButton:pressed {
        border-width: 1px;
        border-color: rgb(22, 22, 22);
        background-color: rgb(22, 22, 22);
        border-style: solid;
    }
    QPushButton {
        border: none;
        color: white;
        background-color: rgb(44, 44, 44);
    }
    QPushButton:pressed {
        border-width: 1px;
        border-color: rgb(22, 22, 22);
        background-color: rgb(22, 22, 22);
        border-style: solid;
    }
    QLabel {
        background-color: rgb(22, 22, 22);
        color: white;
    }
    ''');
    app.setWindowIcon(QtGui.QIcon("icons/logo.png"))
    sys.exit(app.exec())

if __name__ == '__main__':
    # https://stackoverflow.com/questions/71458968/pyqt6-how-to-set-allocation-limit-in-qimagereader
    os.environ['QT_IMAGEIO_MAXALLOC'] = "1024"
    # QtGui.QImageReader.setAllocationLimit(0)

    main()
