""" QtImageViewer.py: PyQt image viewer widget based on QGraphicsView with mouse zooming/panning and ROIs.
"""

import os.path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, pyqtSignal, QEvent, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainterPath, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QSizePolicy, \
    QGraphicsItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem, QGraphicsPolygonItem

# numpy is optional: only needed if you want to display numpy 2d arrays as images.
try:
    import numpy as np
except ImportError:
    np = None

# qimage2ndarray is optional: useful for displaying numpy 2d arrays as images.
# !!! qimage2ndarray requires PyQt5.
#     Some custom code in the viewer appears to handle the conversion from numpy 2d arrays,
#     so qimage2ndarray probably is not needed anymore. I've left it here just in case.
try:
    import qimage2ndarray
except ImportError:
    qimage2ndarray = None

__author__ = "Marcel Goldschen-Ohm <marcel.goldschen@gmail.com>"
__version__ = '2.0.0'

from QCropItem import QCropItem
import random
from PIL import Image, ImageFilter, ImageDraw
from PIL.ImageQt import ImageQt

class QtImageViewer(QGraphicsView):
    """ PyQt image viewer widget based on QGraphicsView with mouse zooming/panning and ROIs.
    Image File:
    -----------
    Use the open("path/to/file") method to load an image file into the viewer.
    Calling open() without a file argument will popup a file selection dialog.
    Image:
    ------
    Use the setImage(im) method to set the image data in the viewer.
        - im can be a QImage, QPixmap, or NumPy 2D array (the later requires the package qimage2ndarray).
        For display in the QGraphicsView the image will be converted to a QPixmap.
    Some useful image format conversion utilities:
        qimage2ndarray: NumPy ndarray <==> QImage    (https://github.com/hmeine/qimage2ndarray)
        ImageQt: PIL Image <==> QImage  (https://github.com/python-pillow/Pillow/blob/master/PIL/ImageQt.py)
    Mouse:
    ------
    Mouse interactions for zooming and panning is fully customizable by simply setting the desired button interactions:
    e.g.,
        regionZoomButton = Qt.LeftButton  # Drag a zoom box.
        zoomOutButton = Qt.RightButton  # Pop end of zoom stack (double click clears zoom stack).
        panButton = Qt.MiddleButton  # Drag to pan.
        wheelZoomFactor = 1.25  # Set to None or 1 to disable mouse wheel zoom.
    To disable any interaction, just disable its button.
    e.g., to disable panning:
        panButton = None
    ROIs:
    -----
    Can also add ellipse, rectangle, line, and polygon ROIs to the image.
    ROIs should be derived from the provided EllipseROI, RectROI, LineROI, and PolygonROI classes.
    ROIs are selectable and optionally moveable with the mouse (see setROIsAreMovable).
    TODO: Add support for editing the displayed image contrast.
    TODO: Add support for drawing ROIs with the mouse.
    """

    # Mouse button signals emit image scene (x, y) coordinates.
    # !!! For image (row, column) matrix indexing, row = y and column = x.
    # !!! These signals will NOT be emitted if the event is handled by an interaction such as zoom or pan.
    # !!! If aspect ratio prevents image from filling viewport, emitted position may be outside image bounds.
    leftMouseButtonPressed = pyqtSignal(float, float)
    leftMouseButtonReleased = pyqtSignal(float, float)
    middleMouseButtonPressed = pyqtSignal(float, float)
    middleMouseButtonReleased = pyqtSignal(float, float)
    rightMouseButtonPressed = pyqtSignal(float, float)
    rightMouseButtonReleased = pyqtSignal(float, float)
    leftMouseButtonDoubleClicked = pyqtSignal(float, float)
    rightMouseButtonDoubleClicked = pyqtSignal(float, float)

    # Emitted upon zooming/panning.
    viewChanged = pyqtSignal()

    # Emitted on mouse motion.
    # Emits mouse position over image in image pixel coordinates.
    # !!! setMouseTracking(True) if you want to use this at all times.
    mousePositionOnImageChanged = pyqtSignal(QPoint)

    # Emit index of selected ROI
    roiSelected = pyqtSignal(int)

    def __init__(self, parent):
        QGraphicsView.__init__(self)
        
        self.parent = parent

        # Image is displayed as a QPixmap in a QGraphicsScene attached to this QGraphicsView.
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Better quality pixmap scaling?
        # self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        # Displayed image pixmap in the QGraphicsScene.
        self._current_filename = None
        self._image = None

        # Image aspect ratio mode.
        #   Qt.IgnoreAspectRatio: Scale image to fit viewport.
        #   Qt.KeepAspectRatio: Scale image to fit inside viewport, preserving aspect ratio.
        #   Qt.KeepAspectRatioByExpanding: Scale image to fill the viewport, preserving aspect ratio.
        self.aspectRatioMode = Qt.AspectRatioMode.KeepAspectRatio

        # Scroll bar behaviour.
        #   Qt.ScrollBarAlwaysOff: Never shows a scroll bar.
        #   Qt.ScrollBarAlwaysOn: Always shows a scroll bar.
        #   Qt.ScrollBarAsNeeded: Shows a scroll bar only when zoomed.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Interactions (set buttons to None to disable interactions)
        # !!! Events handled by interactions will NOT emit *MouseButton* signals.
        #     Note: regionZoomButton will still emit a *MouseButtonReleased signal on a click (i.e. tiny box).
        self.regionZoomButton = Qt.MouseButton.LeftButton  # Drag a zoom box.
        self.zoomOutButton = Qt.MouseButton.RightButton # Pop end of zoom stack (double click clears zoom stack).
        self.panButton = Qt.MouseButton.MiddleButton  # Drag to pan.
        self.wheelZoomFactor = 1.25  # Set to None or 1 to disable mouse wheel zoom.
        self.zoomLevel = 1

        # Stack of QRectF zoom boxes in scene coordinates.
        # !!! If you update this manually, be sure to call updateViewer() to reflect any changes.
        self.zoomStack = []

        # Flags for active zooming/panning.
        self._isZooming = False
        self._isPanning = False

        self._isLeftMouseButtonPressed = False

        # Flags for color picking
        self._isColorPicking = False

        # Flags for painting
        self._isPainting = False
        self.paintBrushSize = 43

        # Flags for filling
        self._isFilling = False

        # Flags for rectangle select
        # Set to true when using the rectangle select tool with toolbar
        self._isSelectingRect = False
        self._isSelectingRectStarted = False
        self._selectRectItem = None
        self._selectRect = None

        # Flags for active selecting
        # Set to true when using the select tool with toolbar
        self._isSelectingPath = False
        self.selectPoints = []
        self.path = None
        self.pathSelected = None
        self.selectPainterPaths = []
        self.pathItem = None
        self.pathPointItem = None
        self.selectPainterPointPaths = []

        self._isCropping = False

        # Flags for spot removal tool
        self._isRemovingSpots = False
        self._targetSelected = False
        self._sourcePos = None
        self._targetPos = None
        self.spotsBrushSize = 10
        self.spotRemovalSimilarityThreshold = 10

        # Flags for blur tool
        self._isBlurring = False
        self.blurBrushSize = 43

        # Flags for erasing
        self._isErasing = False
        self.eraserBrushSize = 43

        # Store temporary position in screen pixels or scene units.
        self._pixelPosition = QPoint()
        self._scenePosition = QPointF()
        self._lastMousePositionInScene = QPointF()

        # Track mouse position. e.g., For displaying coordinates in a UI.
        self.setMouseTracking(True)

        # ROIs.
        self.ROIs = []

        # # For drawing ROIs.
        # self.drawROI = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # self.OriginalImage = None

        self.ColorPicker = None

        ##############################################################################################
        ##############################################################################################
        # Layers
        ##############################################################################################
        ##############################################################################################

        self.layerHistory = {
            0: []    
        }
        self.currentLayer = 0
        self.numLayersCreated = 1

        self.checkerBoard = None
        self.checkerBoardWidth = 0
        self.checkerBoardHeight = 0

        # Reference to dock widget that shows layer list
        self.layerListDock = None

    def sizeHint(self):
        return QSize(900, 600)

    def hasImage(self):
        """ Returns whether the scene contains an image pixmap.
        """
        return self._image is not None

    def clearImage(self):
        """ Removes the current image pixmap from the scene if it exists.
        """
        if self.hasImage():
            self.scene.removeItem(self._image)
            self._image = None

    def pixmap(self):
        """ Returns the scene's current image pixmap as a QPixmap, or else None if no image exists.
        :rtype: QPixmap | None
        """
        if self.hasImage():
            return self._image.pixmap()
        return None

    def currentPixmapSize(self):
        pixmap = self.pixmap()
        if pixmap:
            return pixmap.size()
        else:
            return None

    def image(self):
        """ Returns the scene's current image pixmap as a QImage, or else None if no image exists.
        :rtype: QImage | None
        """
        if self.hasImage():
            return self._image.pixmap().toImage()
        return None

    def getCurrentLayerPixmapBeforeChangeTo(self, changeName):
        if self.currentLayer in self.layerHistory:
            history = self.layerHistory[self.currentLayer]
            i = len(history)
            while i > 0:
                entry = history[i - 1]
                if entry["note"] != changeName:
                    return entry["pixmap"]
                i -= 1
        return None

    def undoCurrentLayerLatestChange(self):
        if self.currentLayer in self.layerHistory:
            history = self.layerHistory[self.currentLayer]
            if len(history) > 1:
                previous = history[-2]
                latest = history[-1]

                if latest["type"] == "Tool" and latest["note"] == "Path Select":
                    # Undo path selection
                    if self.path:
                        self.path.clear()

                    for pathItem in self.selectPainterPaths:
                        if pathItem and pathItem in self.scene.items():
                            self.scene.removeItem(pathItem)

                    for pathPointItem in self.selectPainterPointPaths:
                        if pathPointItem and pathPointItem in self.scene.items():
                            self.scene.removeItem(pathPointItem)

                    if previous["note"] == "Path Select":
                        self.selectPoints, self.selectPainterPaths, self.selectPainterPointPaths = previous["value"]
                        if len(self.selectPoints) > 1:
                            self.buildPath(addToHistory=False)

                            # Remove the last entry from the history
                            self.layerHistory[self.currentLayer] = history[:-1]
                        else:
                            # Remove the last 2 entries from the history
                            self.layerHistory[self.currentLayer] = history[:-2]
                            self.selectPoints = []
                            self.selectPainterPaths = []
                            self.selectPainterPointPaths = []
                    else:
                        # Previous is not a path select
                        # Remove the last 2 entries from the history
                        self.layerHistory[self.currentLayer] = history[:-1]
                        self.selectPoints = []
                        self.selectPainterPaths = []
                        self.selectPainterPointPaths = []

                elif previous["type"] == "Slider":
                    if previous["value"]:
                        slider = getattr(self.parent, previous["object"])
                        slider.setValue(previous["value"])
                        setattr(self.parent, previous["object"], slider)

                        # Remove the last two entries
                        self.layerHistory[self.currentLayer] = history[:-2]
                        self.setImage(previous["pixmap"], True, previous["note"], previous["type"], previous["value"], previous["object"])
                        # Update GUI object value, e.g., slider setting
                
                        if len(self.layerHistory[self.currentLayer]) == 0:
                            self.layerHistory[self.currentLayer].append(previous)
                else:
                    # Generic undo
                    # Remove the last two entries
                    self.layerHistory[self.currentLayer] = history[:-2]
                    self.setImage(previous["pixmap"], True, previous["note"], previous["type"], previous["value"], previous["object"])
                    # Update GUI object value, e.g., slider setting
                
                    if len(self.layerHistory[self.currentLayer]) == 0:
                        self.layerHistory[self.currentLayer].append(previous)

    def getCurrentLayerLatestPixmap(self):
        if self.currentLayer in self.layerHistory:
            # Layer name checks out
            history = self.layerHistory[self.currentLayer]
            
            # History structure
            #
            # List of objects
            # {
            #    "note"   : "Crop",
            #    "pixmap" : QPixmap(...)
            #    "type"   : "Tool" or "Slider"
            #    "value"  : None or some value e.g., 10
            #    "object" : Relevant object, e.g., brightnessSlider <- will be used to update parent.brightnessSlider.setValue(...)
            # }

            if len(history) > 0:
                # Get most recent
                entry = history[-1]
                if "pixmap" in entry:
                    return entry["pixmap"]
        return None

    def getCurrentLayerPreviousPixmap(self):
        if self.currentLayer in self.layerHistory:
            # Layer name checks out
            history = self.layerHistory[self.currentLayer]
            
            # History structure
            #
            # List of objects
            # {
            #    "note"   : "Crop",
            #    "pixmap" : QPixmap(...)
            #    "type"   : "Tool" or "Slider"
            #    "value"  : None or some value e.g., 10
            #    "object" : Relevant object, e.g., brightnessSlider <- will be used to update parent.brightnessSlider.setValue(...)
            # }

            if len(history) > 1:
                # Get most recent
                entry = history[-2]
                if "pixmap" in entry:
                    return entry["pixmap"]
        return None

    def getCurrentLayerLatestPixmapBeforeSliderChange(self):
        if self.currentLayer in self.layerHistory:
            # Layer name checks out
            history = self.layerHistory[self.currentLayer]
            
            # History structure
            #
            # List of objects
            # {
            #    "note"   : "Crop",
            #    "pixmap" : QPixmap(...)
            #    "Type"   : "Tool" or "Slider"
            #    "value"  : None or some value e.g., 10
            #    "object" : Relevant object, e.g., brightnessSlider <- will be used to update parent.brightnessSlider.setValue(...)
            # }

            i = len(history)
            while i > 0:
                entry = history[i - 1]
                if "pixmap" in entry and entry["type"] != "Slider":
                    return entry["pixmap"]
                i -= 1

        return None

    def getCurrentLayerLatestPixmapBeforeLUTChange(self):
        if self.currentLayer in self.layerHistory:
            # Layer name checks out
            history = self.layerHistory[self.currentLayer]
            
            # History structure
            #
            # List of objects
            # {
            #    "note"   : "Crop",
            #    "pixmap" : QPixmap(...)
            #    "Type"   : "Tool" or "Slider"
            #    "value"  : None or some value e.g., 10
            #    "object" : Relevant object, e.g., brightnessSlider <- will be used to update parent.brightnessSlider.setValue(...)
            # }

            i = len(history)
            while i > 0:
                entry = history[i - 1]
                if "pixmap" in entry and entry["note"] != "LUT":
                    return entry["pixmap"]
                i -= 1

        return None

    def addToHistory(self, pixmap, explanationOfChange, typeOfChange, valueOfChange, objectOfChange):
        self.layerHistory[self.currentLayer].append({
            "note": explanationOfChange,
            "pixmap": pixmap,
            "type": typeOfChange,
            "value": valueOfChange,
            "object": objectOfChange
        })

    def duplicateCurrentLayer(self):
        if self.currentLayer in self.layerHistory:
            history = self.layerHistory[self.currentLayer]
            if len(history) > 0:
                latest = history[-1]

                # Create a new layer with latest as the starting point
                self.currentLayer = self.numLayersCreated
                self.numLayersCreated += 1
                self.layerHistory[self.currentLayer] = []
                self.addToHistory(latest["pixmap"], "Open", None, None, None)

    def setImage(self, image, addToHistory=True, explanationOfChange="", typeOfChange=None, valueOfChange=None, objectOfChange=None):
        """ Set the scene's current image pixmap to the input QImage or QPixmap.
        Raises a RuntimeError if the input image has type other than QImage or QPixmap.
        :type image: QImage | QPixmap
        """
        if type(image) is QPixmap:
            pixmap = image
        elif type(image) is QImage:
            pixmap = QPixmap.fromImage(image)
        elif (np is not None) and (type(image) is np.ndarray):
            if qimage2ndarray is not None:
                qimage = qimage2ndarray.array2qimage(image, True)
                pixmap = QPixmap.fromImage(qimage)
            else:
                image = image.astype(np.float32)
                image -= image.min()
                image /= image.max()
                image *= 255
                image[image > 255] = 255
                image[image < 0] = 0
                image = image.astype(np.uint8)
                height, width, _ = image.shape
                bytes = image.tobytes()
                qimage = QImage(bytes, width, height, QImage.Format.Format_Grayscale8)
                pixmap = QPixmap.fromImage(qimage)
        else:
            raise RuntimeError("ImageViewer.setImage: Argument must be a QImage, QPixmap, or numpy.ndarray.")

        # Add to layer history
        if addToHistory:
            if self.layerListDock:
                # Update the layer button pixmap to the new 
                self.layerListDock.setButtonPixmap(pixmap)
            self.addToHistory(pixmap.copy(), explanationOfChange, typeOfChange, valueOfChange, objectOfChange)
        
        ##########################################################################################
        # Grid for transparent images
        #########################################################################################

        # https://stackoverflow.com/a/67073067
        def checkerboard(w, h):
            from itertools import chain
            from math import ceil
            from PIL import Image

            m, n = (int(w / 100), int(h / 100))             # Checker dimension (x, y)

            if m < 100:
                if m == 0:
                    m = 1
                m *= 100/m
                m = int(m)
                n = int(m * h / w)
            elif n < 100:
                if n == 0:
                    n = 1
                n *= 100/n 
                n = int(n)
                m = int(n * w / h)

            c1 = (225, 255, 255, 0)                  # First color
            c2 = (83, 83, 83)                        # Second color
            mode = 'L' if isinstance(c1, int) else 'RGBA'   # Mode from first color

            # Generate pixel-wise checker, even x dimension
            if m % 2 == 0:
                pixels = [[c1, c2] for i in range(int(m/2))] + \
                         [[c2, c1] for i in range(int(m/2))]
                pixels = [list(chain(*pixels)) for i in range(ceil(n/2))]

            # Generate pixel-wise checker, odd x dimension
            else:
                pixels = [[c1, c2] for i in range(ceil(m*n/2))]

            # Generate final Pillow-compatible pixel values
            pixels = list(chain(*pixels))[:(m*n)]

            # Generate Pillow image from pixel values, resize to final image size, and save
            checker = Image.new(mode, (m, n))
            checker.putdata(pixels)
            checker = checker.resize((w, h), Image.NEAREST)
            return checker

        original = pixmap.copy()

        width = pixmap.width()
        height = pixmap.height()

        if not self.checkerBoard:
            self.checkerBoard = checkerboard(width, height)
            self.checkerBoard = self.ImageToQPixmap(self.checkerBoard)
        else:
            if self.checkerBoardHeight != height or self.checkerBoardWidth != width:
                self.checkerBoard = checkerboard(width, height)
                self.checkerBoard = self.ImageToQPixmap(self.checkerBoard)
        if self.checkerBoard:
            painter = QPainter(pixmap)
            painter.drawPixmap(QPoint(), self.checkerBoard)
            painter.drawPixmap(QPoint(), original)
            painter.end()

        #########################################################################################
        
        if self.hasImage():
            self._image.setPixmap(pixmap)
        else:
            self._image = self.scene.addPixmap(pixmap)

        # Better quality pixmap scaling?
        # !!! This will distort actual pixel data when zoomed way in.
        #     For scientific image analysis, you probably don't want this.
        # self._pixmap.setTransformationMode(Qt.SmoothTransformation)

        self.setSceneRect(QRectF(pixmap.rect()))  # Set scene size to image size.
        self.updateViewer()
        if getattr(self.parent, "UpdateHistogramPlot", None):
            self.parent.UpdateHistogramPlot()

    # Nikon NEF raw file
    def read_nef(self, path):
        import rawpy
        image = QtGui.QImage()
        with rawpy.imread(path) as raw:
            src = raw.postprocess(rawpy.Params(use_camera_wb=True))
            h, w, ch = src.shape
            bytesPerLine = ch * w
            buf = src.data.tobytes() # or bytes(src.data)
            image = QtGui.QImage(buf, w, h, bytesPerLine, QtGui.QImage.Format.Format_RGB888)
        return image.copy()

    def open(self, filepath=None):
        """ Load an image from file.
        Without any arguments, loadImageFromFile() will pop up a file dialog to choose the image file.
        With a fileName argument, loadImageFromFile(fileName) will attempt to load the specified image file directly.
        """
        if filepath is None:
            filepath, dummy = QFileDialog.getOpenFileName(self, "Open image file.")
        if len(filepath) and os.path.isfile(filepath):
            self._current_filename = filepath
            
            if filepath.lower().endswith(".nef"):
                image = self.read_nef(filepath)
                self.setImage(image, True, "Open")
            else:
                image = QImage(filepath)
                self.setImage(image, True, "Open")

    def save(self, filepath=None):
        path = self._current_filename
        if filepath:
            path = filepath
            self._current_filename = path

        self.pixmap().save(path, None, 100)

    def updateViewer(self):
        """ Show current zoom (if showing entire image, apply current aspect ratio mode).
        """
        if not self.hasImage():
            return
        if len(self.zoomStack):
            self.fitInView(self.zoomStack[-1], self.aspectRatioMode)  # Show zoomed rect.
        else:
            self.fitInView(self.sceneRect(), self.aspectRatioMode)  # Show entire image.

    def clearZoom(self):
        if len(self.zoomStack) > 0:
            self.zoomStack = []
            self.updateViewer()
            self.viewChanged.emit()

    def resizeEvent(self, event):
        """ Maintain current zoom on resize.
        """
        self.updateViewer()

    def QPixmapToImage(self, pixmap):
        width = pixmap.width()
        height = pixmap.height()
        image = pixmap.toImage()

        byteCount = image.bytesPerLine() * height
        data = image.constBits().asstring(byteCount)
        return Image.frombuffer('RGBA', (width, height), data, 'raw', 'BGRA', 0, 1)

    def QImageToImage(self, qimage):
        width = qimage.width()
        height = qimage.height()
        image = qimage

        byteCount = image.bytesPerLine() * height
        data = image.constBits().asstring(byteCount)
        return Image.frombuffer('RGBA', (width, height), data, 'raw', 'BGRA', 0, 1)

    def ImageToQPixmap(self, image):
        return QPixmap.fromImage(ImageQt(image))

    def QImageToCvMat(self, incomingImage):
        '''  Converts a QImage into an opencv MAT format  '''

        incomingImage = incomingImage.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)

        width = incomingImage.width()
        height = incomingImage.height()

        ptr = incomingImage.bits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        return arr

    def mousePressEvent(self, event):
        """ Start mouse pan or zoom mode.
        """
        # Ignore dummy events. e.g., Faking pan with left button ScrollHandDrag.
        dummyModifiers = Qt.KeyboardModifier(Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
                                             | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)
        if event.modifiers() == dummyModifiers:
            QGraphicsView.mousePressEvent(self, event)
            event.accept()
            return

        if event.button() == self.regionZoomButton:
            self._isLeftMouseButtonPressed = True

        # # Draw ROI
        # if self.drawROI is not None:
        #     if self.drawROI == "Ellipse":
        #         # Click and drag to draw ellipse. +Shift for circle.
        #         pass
        #     elif self.drawROI == "Rect":
        #         # Click and drag to draw rectangle. +Shift for square.
        #         pass
        #     elif self.drawROI == "Line":
        #         # Click and drag to draw line.
        #         pass
        #     elif self.drawROI == "Polygon":
        #         # Click to add points to polygon. Double-click to close polygon.
        #         pass

        if self._isColorPicking:
            self.performColorPick(event)
        elif self._isPainting:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self.performPaint(event)
        elif self._isErasing:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self.performErase(event)
        elif self._isFilling:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self.performFill(event)
        elif self._isSelectingRect:
            if not self._isSelectingRectStarted:
                # Start dragging a region crop box?
                if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                    self._isSelectingRectStarted = True
                    
                    self._pixelPosition = event.pos()  # store pixel position
                    self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                    QGraphicsView.mousePressEvent(self, event)
                    event.accept()
                    return
            else:
                event.ignore()
        elif self._isSelectingPath:
            # TODO: https://stackoverflow.com/questions/63568214/qpainter-delete-previously-drawn-shapes
            #
            #
            # Start dragging a region crop box?
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self._pixelPosition = event.pos()  # store pixel position
                self.selectPoints.append(QPointF(self.mapToScene(event.pos())))
                QGraphicsView.mousePressEvent(self, event)
                self.buildPath()
                event.accept()
                return
        elif self._isRemovingSpots:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                if not self._targetSelected:
                    # Target selected

                    # Save the target position
                    self._targetPos = self.mapToScene(event.pos())
                    self._targetPos = (int(self._targetPos.x()), int(self._targetPos.y()))
                    # Set toggle
                    self._targetSelected = True
                    self.showSpotRemovalResultAtMousePosition(event)
                else:
                    self.removeSpots(event)
        elif self._isBlurring:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self.blur(event)
        else:
            # Zoom
            # Start dragging a region zoom box?
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self._pixelPosition = event.pos()  # store pixel position
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                QGraphicsView.mousePressEvent(self, event)
                event.accept()
                self._isZooming = True
                return

            if (self.zoomOutButton is not None) and (event.button() == self.zoomOutButton):
                if len(self.zoomStack):
                    self.zoomStack.pop()
                    self.updateViewer()
                    self.viewChanged.emit()
                event.accept()
                return

        # Start dragging to pan?
        if (self.panButton is not None) and (event.button() == self.panButton):
            self._pixelPosition = event.pos()  # store pixel position
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            if self.panButton == Qt.MouseButton.LeftButton:
                QGraphicsView.mousePressEvent(self, event)
            else:
                # ScrollHandDrag ONLY works with LeftButton, so fake it.
                # Use a bunch of dummy modifiers to notify that event should NOT be handled as usual.
                self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
                dummyModifiers = Qt.KeyboardModifier(Qt.KeyboardModifier.ShiftModifier
                                                     | Qt.KeyboardModifier.ControlModifier
                                                     | Qt.KeyboardModifier.AltModifier
                                                     | Qt.KeyboardModifier.MetaModifier)
                dummyEvent = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(event.pos()), Qt.MouseButton.LeftButton,
                                         event.buttons(), dummyModifiers)
                self.mousePressEvent(dummyEvent)
            sceneViewport = self.mapToScene(self.viewport().rect()).boundingRect().intersected(self.sceneRect())
            self._scenePosition = sceneViewport.topLeft()
            event.accept()
            self._isPanning = True
            return

        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.MouseButton.LeftButton:
            self.leftMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.middleMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightMouseButtonPressed.emit(scenePos.x(), scenePos.y())

        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """ Stop mouse pan or zoom mode (apply zoom if valid).
        """
        # Ignore dummy events. e.g., Faking pan with left button ScrollHandDrag.
        dummyModifiers = Qt.KeyboardModifier(Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
                                             | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)
        if event.modifiers() == dummyModifiers:
            QGraphicsView.mouseReleaseEvent(self, event)
            event.accept()
            return

        if event.button() == self.regionZoomButton:
            self._isLeftMouseButtonPressed = False

        if self._isSelectingRect:
            if self._isSelectingRectStarted:
                # Finish dragging a region crop box?
                if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                    QGraphicsView.mouseReleaseEvent(self, event)
                    self._selectRect = self.scene.selectionArea().boundingRect().intersected(self.sceneRect())
                    # Clear current selection area (i.e. rubberband rect).
                    self.scene.setSelectionArea(QPainterPath())
                    self.setDragMode(QGraphicsView.DragMode.NoDrag)
                    # If zoom box is 3x3 screen pixels or smaller, do not zoom and proceed to process as a click release.
                    zoomPixelWidth = abs(event.pos().x() - self._pixelPosition.x())
                    zoomPixelHeight = abs(event.pos().y() - self._pixelPosition.y())
                    if zoomPixelWidth > 3 and zoomPixelHeight > 3:
                        if self._selectRect.isValid() and (self._selectRect != self.sceneRect()):
                            # Create a new crop item using user-drawn rectangle
                            pixmap = self.getCurrentLayerLatestPixmap()
                            if self._selectRectItem:
                                self._selectRectItem.setRect(self._selectRect)
                            else:
                                self._selectRectItem = QCropItem(self._image, self._selectRect, (pixmap.width(), pixmap.height()))
        else:
            # Finish dragging a region zoom box?
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                QGraphicsView.mouseReleaseEvent(self, event)
                zoomRect = self.scene.selectionArea().boundingRect().intersected(self.sceneRect())
                # Clear current selection area (i.e. rubberband rect).
                self.scene.setSelectionArea(QPainterPath())
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                # If zoom box is 3x3 screen pixels or smaller, do not zoom and proceed to process as a click release.
                zoomPixelWidth = abs(event.pos().x() - self._pixelPosition.x())
                zoomPixelHeight = abs(event.pos().y() - self._pixelPosition.y())
                if zoomPixelWidth > 3 and zoomPixelHeight > 3:
                    if zoomRect.isValid() and (zoomRect != self.sceneRect()):
                        self.zoomStack.append(zoomRect)
                        self.updateViewer()
                        self.viewChanged.emit()
                        event.accept()
                        self._isZooming = False
                        return

        # Finish panning?
        if (self.panButton is not None) and (event.button() == self.panButton):
            if self.panButton == Qt.MouseButton.LeftButton:
                QGraphicsView.mouseReleaseEvent(self, event)
            else:
                # ScrollHandDrag ONLY works with LeftButton, so fake it.
                # Use a bunch of dummy modifiers to notify that event should NOT be handled as usual.
                self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
                dummyModifiers = Qt.KeyboardModifier(Qt.KeyboardModifier.ShiftModifier
                                                     | Qt.KeyboardModifier.ControlModifier
                                                     | Qt.KeyboardModifier.AltModifier
                                                     | Qt.KeyboardModifier.MetaModifier)
                dummyEvent = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(event.pos()),
                                         Qt.MouseButton.LeftButton, event.buttons(), dummyModifiers)
                self.mouseReleaseEvent(dummyEvent)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            if len(self.zoomStack) > 0:
                sceneViewport = self.mapToScene(self.viewport().rect()).boundingRect().intersected(self.sceneRect())
                delta = sceneViewport.topLeft() - self._scenePosition
                self.zoomStack[-1].translate(delta)
                self.zoomStack[-1] = self.zoomStack[-1].intersected(self.sceneRect())
                self.viewChanged.emit()
            event.accept()
            self._isPanning = False
            return

        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.MouseButton.LeftButton:
            self.leftMouseButtonReleased.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.middleMouseButtonReleased.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightMouseButtonReleased.emit(scenePos.x(), scenePos.y())

        QGraphicsView.mouseReleaseEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """ Show entire image.
        """
        # Zoom out on double click?
        if (self.zoomOutButton is not None) and (event.button() == self.zoomOutButton):
            self.clearZoom()
            event.accept()
            return

        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.MouseButton.LeftButton:
            self.leftMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())

        QGraphicsView.mouseDoubleClickEvent(self, event)

    def wheelEvent(self, event):
        if self.wheelZoomFactor is not None:
            if self.wheelZoomFactor == 1:
                return
            if event.angleDelta().y() < 0:
                # zoom in
                if len(self.zoomStack) == 0:
                    self.zoomStack.append(self.sceneRect())
                elif len(self.zoomStack) > 1:
                    del self.zoomStack[:-1]
                zoomRect = self.zoomStack[-1]
                center = zoomRect.center()
                zoomRect.setWidth(zoomRect.width() / self.wheelZoomFactor)
                zoomRect.setHeight(zoomRect.height() / self.wheelZoomFactor)
                zoomRect.moveCenter(center)
                self.zoomStack[-1] = zoomRect.intersected(self.sceneRect())
                self.updateViewer()
                self.viewChanged.emit()
                self.zoomLevel += 1
            else:
                # zoom out
                if len(self.zoomStack) == 0:
                    # Already fully zoomed out.
                    return
                if len(self.zoomStack) > 1:
                    del self.zoomStack[:-1]
                zoomRect = self.zoomStack[-1]
                center = zoomRect.center()
                zoomRect.setWidth(zoomRect.width() * self.wheelZoomFactor)
                zoomRect.setHeight(zoomRect.height() * self.wheelZoomFactor)
                zoomRect.moveCenter(center)
                self.zoomStack[-1] = zoomRect.intersected(self.sceneRect())
                if self.zoomStack[-1] == self.sceneRect():
                    self.zoomStack = []
                self.updateViewer()
                self.viewChanged.emit()
                self.zoomLevel -= 1
            event.accept()
            return

        QGraphicsView.wheelEvent(self, event)

    def mouseMoveEvent(self, event):

        # Emit updated view during panning.
        if self._isPanning:
            QGraphicsView.mouseMoveEvent(self, event)
            if len(self.zoomStack) > 0:
                sceneViewport = self.mapToScene(self.viewport().rect()).boundingRect().intersected(self.sceneRect())
                delta = sceneViewport.topLeft() - self._scenePosition
                self._scenePosition = sceneViewport.topLeft()
                self.zoomStack[-1].translate(delta)
                self.zoomStack[-1] = self.zoomStack[-1].intersected(self.sceneRect())
                self.updateViewer()
                self.viewChanged.emit()
        elif self._isPainting:
            if self.scene:
                self._lastMousePositionInScene = QPointF(self.mapToScene(event.pos()))
            self.renderCursorOverlay(self._lastMousePositionInScene, self.paintBrushSize)
            if self._isLeftMouseButtonPressed:
                self.performPaint(event)
        elif self._isErasing:
            if self.scene:
                self._lastMousePositionInScene = QPointF(self.mapToScene(event.pos()))
            self.renderCursorOverlay(self._lastMousePositionInScene, self.eraserBrushSize)
            if self._isLeftMouseButtonPressed:
                self.performErase(event)
        elif self._isFilling:
            pass
            # TODO: Change cursor to a paint bucket?
        elif self._isRemovingSpots:
            if not self._targetSelected:
                # Show ROI
                # Make mouse red
                if self.scene:
                    self._lastMousePositionInScene = QPointF(self.mapToScene(event.pos()))
                self.renderCursorOverlay(self._lastMousePositionInScene, self.spotsBrushSize)
            if self._targetSelected:
                # A target has been selected
                # Show blemish fix around the mouse position
                # If the user is happy with the result, they will click again and the fix
                # will be placed
                self.showSpotRemovalResultAtMousePosition(event)
        elif self._isBlurring:
            if self.scene:
                self._lastMousePositionInScene = QPointF(self.mapToScene(event.pos()))
            self.renderCursorOverlay(self._lastMousePositionInScene, self.blurBrushSize)

        scenePos = self.mapToScene(event.pos())
        if self.sceneRect().contains(scenePos):
            # Pixel index offset from pixel center.
            x = int(round(scenePos.x() - 0.5))
            y = int(round(scenePos.y() - 0.5))
            imagePos = QPoint(x, y)
        else:
            # Invalid pixel position.
            imagePos = QPoint(-1, -1)
        self.mousePositionOnImageChanged.emit(imagePos)

        QGraphicsView.mouseMoveEvent(self, event)

    def enterEvent(self, event):
        self.setCursor(Qt.CursorShape.CrossCursor)

    def leaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def addROIs(self, rois):
        for roi in rois:
            self.scene.addItem(roi)
            self.ROIs.append(roi)

    def deleteROIs(self, rois):
        for roi in rois:
            self.scene.removeItem(roi)
            self.ROIs.remove(roi)
            del roi

    def clearROIs(self):
        for roi in self.ROIs:
            self.scene.removeItem(roi)
        del self.ROIs[:]

    def roiClicked(self, roi):
        for i in range(len(self.ROIs)):
            if roi is self.ROIs[i]:
                self.roiSelected.emit(i)
                break

    def setROIsAreMovable(self, tf):
        if tf:
            for roi in self.ROIs:
                roi.setFlags(roi.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        else:
            for roi in self.ROIs:
                roi.setFlags(roi.flags() & ~QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def addSpots(self, xy, radius):
        for xy_ in xy:
            x, y = xy_
            spot = EllipseROI(self)
            spot.setRect(x - radius, y - radius, 2 * radius, 2 * radius)
            self.scene.addItem(spot)
            self.ROIs.append(spot)

    def keyPressEvent(self, event):
        if self._isPainting:
            if event.key() == Qt.Key.Key_BracketLeft:
                self.paintBrushSize -= 3
                if self.paintBrushSize < 1:
                    self.paintBrushSize = 1
                self.renderCursorOverlay(self._lastMousePositionInScene, self.paintBrushSize)
            elif event.key() == Qt.Key.Key_BracketRight:
                self.paintBrushSize += 3
                self.renderCursorOverlay(self._lastMousePositionInScene, self.paintBrushSize)
        if self._isErasing:
            if event.key() == Qt.Key.Key_BracketLeft:
                self.eraserBrushSize -= 3
                if self.eraserBrushSize < 1:
                    self.eraserBrushSize = 1
                self.renderCursorOverlay(self._lastMousePositionInScene, self.eraserBrushSize)
            elif event.key() == Qt.Key.Key_BracketRight:
                self.eraserBrushSize += 3
                self.renderCursorOverlay(self._lastMousePositionInScene, self.eraserBrushSize)
        elif self._isRemovingSpots:
            if event.key() == Qt.Key.Key_BracketLeft:
                self.spotsBrushSize -= 3
                if self.spotsBrushSize < 1:
                    self.spotsBrushSize = 1
                self.renderCursorOverlay(self._lastMousePositionInScene, self.spotsBrushSize)
            elif event.key() == Qt.Key.Key_BracketRight:
                self.spotsBrushSize += 3
                self.renderCursorOverlay(self._lastMousePositionInScene, self.spotsBrushSize)
        elif self._isBlurring:
            if event.key() == Qt.Key.Key_BracketLeft:
                self.blurBrushSize -= 1
                if self.blurBrushSize < 1:
                    self.blurBrushSize = 3
                self.renderCursorOverlay(self._lastMousePositionInScene, self.blurBrushSize)
            elif event.key() == Qt.Key.Key_BracketRight:
                self.blurBrushSize += 3
                self.renderCursorOverlay(self._lastMousePositionInScene, self.blurBrushSize)

        event.accept()

    def performColorPick(self, event):
        currentPixmap = self.getCurrentLayerLatestPixmap()
        currentImage = self.QPixmapToImage(currentPixmap)
        pixelAccess = currentImage.load()
        scene_pos = self.mapToScene(event.pos())
        x = scene_pos.x()
        y = scene_pos.y()
        r, g, b, _ = pixelAccess[x, y]
        self.ColorPicker.setRGB((r, g, b))

    def performPaint(self, event):
        currentPixmap = self.getCurrentLayerLatestPixmap().copy()
        currentImage = currentPixmap.toImage()
        scene_pos = self.mapToScene(event.pos())
        x = scene_pos.x()
        y = scene_pos.y()
        w = currentImage.width()
        h = currentImage.height()

        brush_size = self.paintBrushSize
        sample_size = 2 * brush_size
        r, g, b = self.ColorPicker.getRGB()

        # Find neighbor pixels in a circle around (x, y)
        pixels = []
        for i in range(int(x - sample_size), int(x + sample_size)):
            for j in range(int(y - sample_size), int(y + sample_size)):
                dist = (i - x) * (i - x) + (j - y) * (j - y)

                if dist <= brush_size * brush_size:
                    # point is inside circle

                    # is the point inside the image?
                    if i >= 0 and i < w and j >= 0 and j < h:
                        pixels.append([i, j])

        # For each point, update the pixel by averaging
        for point in pixels:
            i, j = point
            currentImage.setPixelColor(i, j, QtGui.QColor(int(r), int(g), int(b), 255))

        # Update the pixmap
        self.setImage(currentImage, True, "Paint")

    def performFill(self, event):
        currentPixmap = self.getCurrentLayerLatestPixmap().copy()
        currentImage = self.QPixmapToImage(currentPixmap)
        pixelAccess = currentImage.load()
        scene_pos = self.mapToScene(event.pos())
        x = scene_pos.x()
        y = scene_pos.y()

        # https://stackoverflow.com/questions/8629085/qt-pyqt-other-how-do-i-change-specific-colors-in-a-pixmap

        r, g, b, _ = pixelAccess[x, y]
        cr, cg, cb = self.ColorPicker.getRGB()

        mask = currentPixmap.createMaskFromColor(QtGui.QColor(r, g, b), Qt.MaskMode.MaskOutColor)

        p = QPainter(currentPixmap)
        p.setPen(QtGui.QColor(int(cr), int(cg), int(cb)))
        p.drawPixmap(currentPixmap.rect(), mask, mask.rect())
        p.end()

        # Update the pixmap
        self.setImage(currentPixmap, True, "Fill")

    def exitSelectRect(self):
        # Remove the selected rectangle from the scene
        if self._selectRectItem:
            if self._selectRectItem in self.scene.items():
                self.scene.removeItem(self._selectRectItem)
        # Reset variables
        self._selectRect = None
        self._selectRectItem = None
        self._isSelectingRect = False
        self._isSelectingRectStarted = False

    def exitSelectPath(self):
        self.selectPoints = []
        if self.path:
            self.path.clear()
        for pathItem in self.selectPainterPaths:
            if pathItem and pathItem in self.scene.items():
                self.scene.removeItem(pathItem)

        for pathPointItem in self.selectPainterPointPaths:
            if pathPointItem and pathPointItem in self.scene.items():
                self.scene.removeItem(pathPointItem)

        self.selectPainterPaths = []
        self.selectPainterPointPaths = []
        self.path = None
        self._isSelectingPath = False
        self.pathItem = None
        self.pathPointItem = None

    def performSelectCrop(self):
        self.path.quadTo(self.selectPoints[-1], self.selectPoints[-1])
        self.pathSelected.quadTo(self.selectPoints[-1], self.selectPoints[-1])

        currentImage = self.getCurrentLayerLatestPixmap()
        output = QImage(currentImage.toImage().size(), QImage.Format.Format_ARGB32)
        output.fill(Qt.GlobalColor.transparent)
        painter = QPainter(output)
        painter.setClipPath(self.pathSelected)
        painter.drawImage(QPoint(), currentImage.toImage())
        painter.end()
        # To avoid useless transparent background you can crop it like that:
        output = output.copy(self.pathSelected.boundingRect().toRect())
        self.setImage(output, True, "PathCrop")

        self.selectPoints = []

        if self.path:
            self.path.clear()
            self.pathSelected.clear()
        
        for pathItem in self.selectPainterPaths:
            if pathItem and pathItem in self.scene.items():
                self.scene.removeItem(pathItem)

        for pathPointItem in self.selectPainterPointPaths:
            if pathPointItem and pathPointItem in self.scene.items():
                self.scene.removeItem(pathPointItem)
                
        self.selectPainterPaths = []
        self.selectPainterPointPaths = []
        self.path = None         # Path + boundingRect to make it look nice
        self.pathSelected = None # Just the path, nothing more - used for crop
        self.pathItem = None
        self.pathPointItem = None

    def getSelectedRegionAsPixmap(self):
        self.path.quadTo(self.selectPoints[-1], self.selectPoints[-1])
        self.pathSelected.quadTo(self.selectPoints[-1], self.selectPoints[-1])

        currentImage = self.getCurrentLayerLatestPixmap()
        output = QImage(currentImage.toImage().size(), QImage.Format.Format_ARGB32)
        output.fill(Qt.GlobalColor.transparent)
        painter = QPainter(output)
        painter.setClipPath(self.pathSelected)
        painter.drawImage(QPoint(), currentImage.toImage())
        painter.end()
        
        return QPixmap.fromImage(output)

    def performCrop(self):
        try:
            if self._isSelectingRect and self._isSelectingRectStarted:
                rect = self._selectRectItem.intern_rect.toAlignedRect()

                # Crop the pixmap
                cropQPixmap = self.getCurrentLayerLatestPixmap().copy(rect)

                self.setImage(cropQPixmap, True, "RectCrop")

                self.exitSelectRect()
                self.clearZoom()
                self.viewChanged.emit()
            elif self._isSelectingPath:
                self.performSelectCrop()
                self.exitSelectPath()
                self.clearZoom()
                self.viewChanged.emit()
                # Clean up history
                # Remove the "Path Select" entries
                if self.currentLayer in self.layerHistory:
                    history = self.layerHistory[self.currentLayer]
                    if len(history) > 1:
                        history = [h for h in history if h["note"] != "Path Select"]
                        self.layerHistory[self.currentLayer] = history
            self.parent.DisableAllTools()
        except RuntimeError as e:
            print(e)

    def buildPath(self, addToHistory=True):
        '''
        https://stackoverflow.com/questions/63016214/drawing-multi-point-curve-with-pyqt5
        '''
        factor = 0.25
        cp1 = QPointF(0, 0)
        if self.path in self.scene.items():
            self.scene.removeItem(self.path)
            del self.path
            del self.pathSelected
        self.path = QtGui.QPainterPath()
        self.pathSelected = QtGui.QPainterPath(self.selectPoints[0])
        self.path.addRect(self._image.boundingRect())
        self.path.moveTo(self.selectPoints[0])

        # Create a painter path for the points
        # Add ellipses/circles for each point selected so far
        self.pointPainter = QtGui.QPainterPath()
        maxDim = max(self._image.pixmap().width(), self._image.pixmap().height())
        for point in self.selectPoints:
            squareSide = int(maxDim / 200)
            self.pointPainter.addRect(point.x() - (squareSide / 2), point.y() - (squareSide / 2), squareSide, squareSide)
            # self.pointPainter.addEllipse(point, int(maxDim / 100), int(maxDim / 100))

        for p, current in enumerate(self.selectPoints[1:-1], 1):
            # previous segment
            source = QtCore.QLineF(self.selectPoints[p - 1], current)
            # next segment
            target = QtCore.QLineF(current, self.selectPoints[p + 1])
            targetAngle = target.angleTo(source)
            if targetAngle > 180:
                angle = (source.angle() + source.angleTo(target) / 2) % 360
            else:
                angle = (target.angle() + target.angleTo(source) / 2) % 360

            revTarget = QtCore.QLineF.fromPolar(source.length() * factor, angle + 180).translated(current)
            cp2 = revTarget.p2()

            if p == 1:
                self.path.quadTo(cp2, current)
                self.pathSelected.quadTo(cp2, current)
            else:
                # use the control point "cp1" set in the *previous* cycle
                self.path.cubicTo(cp1, cp2, current)
                self.pathSelected.cubicTo(cp1, cp2, current)

            revSource = QtCore.QLineF.fromPolar(target.length() * factor, angle).translated(current)
            cp1 = revSource.p2()

        # the final curve, that joins to the last point
        if len(self.selectPoints) > 1:
            self.path.quadTo(self.selectPoints[-2], self.selectPoints[-1])
            self.pathSelected.quadTo(self.selectPoints[-2], self.selectPoints[-1])

        self.path.quadTo(self.selectPoints[-1], self.selectPoints[-1])
        self.pathSelected.quadTo(self.selectPoints[-1], self.selectPoints[-1])

        '''
        Alternate simpler solution that does not draw any curves
        just lines:
        if not self.path:
            self.path = QtGui.QPainterPath(self.selectPoints[0])
        if len(self.selectPoints) > 1:
            self.path.quadTo(self.selectPoints[-2], self.selectPoints[-1])
        '''

        penWidth = int(5 / self.zoomLevel)
        
        if len(self.selectPainterPaths):
            # Hide previous pen and brush
            self.selectPainterPaths[-1].setBrush(QtGui.QColor(10, 100, 100, 0))
            self.selectPainterPaths[-1].setPen(QPen(Qt.PenStyle.NoPen))

        self.pathItem = self.scene.addPath(self.path)
        self.selectPainterPaths.append(self.pathItem)

        # Brush and Pen for the selected region
        self.pathItem.setBrush(QtGui.QColor(10, 100, 100, 100))
        self.pathItem.setPen(QPen(Qt.PenStyle.NoPen))

        # Brush and Pen for the selected POINTS
        self.pathPointItem = self.scene.addPath(self.pointPainter)
        self.pathPointItem.setBrush(QtGui.QColor(0, 0, 0, 255))
        self.pathPointItem.setPen(QPen(Qt.PenStyle.NoPen))
        self.selectPainterPointPaths.append(self.pathPointItem)

        if addToHistory:
            self.addToHistory(self.pixmap(), "Path Select", "Tool", [self.selectPoints.copy(), self.selectPainterPaths.copy(), self.selectPainterPointPaths.copy()], None)

    def Luminance(self, pixel):
        return (0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2])

    def isSimilar(self, pixel_a, pixel_b, threshold):
        return abs(self.Luminance(pixel_a) - self.Luminance(pixel_b)) < threshold
    
    def fixBlemish(self, image, source_pos, target_pos, brush_size):
        import cv2
        # Trying to construct a good method to identify a "good" region seems really difficult. 
        # There are multiple factors to consider, such as how big of a search region to include, how to determine proper textured regions vs incorrect near by regions, how to optimize a search, whether to just search until you find one, or try to optimize, etc. 
        # So instead, I will build a tool similar to the Photoshop healing brush tool, where the user manually selects a better region. 
        # Personally, having used photoshop, I actually prefer this method, as it gives the user more control. Plus, since I am more familiar with it, it'll be easier for me to implement.

        image_original = image.copy()
        # Get ROI
        clone_source_roi = image_original[source_pos[1]-brush_size:source_pos[1]+brush_size, source_pos[0]-brush_size:source_pos[0]+brush_size]
        
        # Get mask
        clone_source_mask = np.ones(clone_source_roi.shape, clone_source_roi.dtype) * 255
        # Feather mask
        # clone_source_mask = cv2.GaussianBlur(clone_source_mask, (5, 5), 0, 0)

        # Apply clone
        fix = cv2.seamlessClone(clone_source_roi, image_original, clone_source_mask, target_pos, cv2.NORMAL_CLONE)
        return fix
    
    def showSpotRemovalResultAtMousePosition(self, event):
        import cv2

        currentPixmap = self.getCurrentLayerLatestPixmap().copy()
        currentImage = self.QPixmapToImage(currentPixmap)
        image_view = np.asarray(currentImage)
        scenePos = self.mapToScene(event.pos())
        scenePos = (int(scenePos.x()), int(scenePos.y()))

        b, g, r, a = cv2.split(image_view)
        image_view = np.dstack((b, g, r))

        # Show ROI
        # Show target
        image_view = self.fixBlemish(image_view, scenePos, self._targetPos, self.spotsBrushSize)

        image_view = np.dstack((image_view, a))
        currentImage = Image.fromarray(image_view).convert("RGBA")
        blemishFixedPixmap = self.ImageToQPixmap(currentImage)

        # Show cursor overlay
        # pixmapTmp = currentPixmap.copy()
        cursorPainter = QPainter(blemishFixedPixmap)
        cursorPainter.drawEllipse(QPointF(self._targetPos[0], self._targetPos[1]), self.spotsBrushSize, self.spotsBrushSize)
        cursorPainter.drawEllipse(QPointF(scenePos[0], scenePos[1]), self.spotsBrushSize, self.spotsBrushSize)

        # Draw line
        # Whole bunch of vector code to draw the proper connecting line
        t = np.array(self._targetPos)
        m = np.array(scenePos)
        if np.linalg.norm(t-m) > self.spotsBrushSize * 2:
            # Brushes are far enough to draw lines without error
            # Get vector between points
            v = t - m
            # Normalize vector
            line_vector = v / np.linalg.norm(v)
            # Subtract off the parts that we don't want 
            t = t - line_vector * self.spotsBrushSize
            t = tuple(t.astype(np.int64))
            m = m + line_vector * self.spotsBrushSize
            m = tuple(m.astype(np.int64))
            cursorPainter.drawLine(t[0], t[1], m[0], m[1])

        cursorPainter.end() 
        self.setImage(blemishFixedPixmap, False, "Cursor Overlay")

    def removeSpots(self, event):
        import cv2
        currentPixmap = self.getCurrentLayerLatestPixmap().copy()
        currentImage = self.QPixmapToImage(currentPixmap)
        image_view = np.asarray(currentImage)
        scenePos = self.mapToScene(event.pos())
        scenePos = (int(scenePos.x()), int(scenePos.y()))

        b, g, r, a = cv2.split(image_view)
        image_view = np.dstack((b, g, r))

        image_view = self.fixBlemish(image_view, scenePos, self._targetPos, self.spotsBrushSize)

        image_view = np.dstack((image_view, a))
        currentImage = Image.fromarray(image_view).convert("RGBA")

        # Update the pixmap
        updatedPixmap = self.ImageToQPixmap(currentImage)
        self.setImage(updatedPixmap, True, "Spot Removal")
        self._targetSelected = False
        self._targetPos = None

        return
        
    def blur(self, event):
        brush_size = self.blurBrushSize
        currentPixmap = self.getCurrentLayerLatestPixmap().copy()
        currentImage = self.QPixmapToImage(currentPixmap)
        scene_pos = self.mapToScene(event.pos())
        x = scene_pos.x()
        y = scene_pos.y()

        # Make a mask the same size as the image filled with black
        mask = Image.new('L',currentImage.size)

        # Draw a filled white circle onto the black mask
        draw = ImageDraw.Draw(mask)
        draw.ellipse([x - brush_size, y - brush_size, x + brush_size, y + brush_size],fill=255)

        # Blur the entire image
        blurred = currentImage.filter(ImageFilter.BLUR)

        # Composite blurred image over sharp one within mask
        currentImage = Image.composite(blurred, currentImage, mask)

        # Update the pixmap
        updatedPixmap = self.ImageToQPixmap(currentImage)
        self.setImage(updatedPixmap, True, "Blur")
        # self.OriginalImage = updatedPixmap

    def performErase(self, event):
        currentPixmap = self.getCurrentLayerLatestPixmap().copy()
        currentImage = currentPixmap.toImage()

        # First convert to a format that supports transparency
        # https://stackoverflow.com/questions/16910905/set-alpha-channel-per-pixel-in-qimage
        currentImage = currentImage.convertToFormat(QImage.Format.Format_ARGB32)

        scene_pos = self.mapToScene(event.pos())
        x = scene_pos.x()
        y = scene_pos.y()
        w = currentImage.width()
        h = currentImage.height()

        brush_size = self.eraserBrushSize
        sample_size = 2 * brush_size

        # Find neighbor pixels in a circle around (x, y)
        pixels = []
        for i in range(int(x - sample_size), int(x + sample_size)):
            for j in range(int(y - sample_size), int(y + sample_size)):
                dist = (i - x) * (i - x) + (j - y) * (j - y)

                if dist <= brush_size * brush_size:
                    # point is inside circle

                    # is the point inside the image?
                    if i >= 0 and i < w and j >= 0 and j < h:
                        pixels.append([i, j])

        # For each point, update the pixel by averaging
        for point in pixels:
            i, j = point
            color = QtGui.QColor(255, 255, 255, 0)
            rgba = color.rgba()
            currentImage.setPixel(i, j, rgba)

        # Update the pixmap
        self.setImage(currentImage, True, "Eraser")
    
    def renderCursorOverlay(self, scenePosition, brushSize):
        pixmap = self.getCurrentLayerLatestPixmap()

        if pixmap:
            pixmapTmp = pixmap.copy()
            cursorPainter = QPainter()
            cursorPainter.begin(pixmapTmp)
            brush = QtGui.QBrush()
            brush.setColor(QtGui.QColor(255, 0, 0, 127))
            brush.setStyle(QtCore.Qt.BrushStyle.SolidPattern)
            pen = QtGui.QPen()
            pen.setBrush(brush)
            cursorPainter.setBrush(brush)
            cursorPainter.setPen(pen)
            cursorPainter.drawEllipse(scenePosition, brushSize, brushSize)
            cursorPainter.end() 
            self.setImage(pixmapTmp, False, "Cursor Overlay")

    def paintEvent(self, event):
        if self._isCropping:
            self.performCrop()
            self._isCropping = False
        QGraphicsView.paintEvent(self, event)

class EllipseROI(QGraphicsEllipseItem):

    def __init__(self, viewer):
        QGraphicsItem.__init__(self)
        self._viewer = viewer
        pen = QPen(Qt.yellow)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setFlags(self.GraphicsItemFlag.ItemIsSelectable)

    def mousePressEvent(self, event):
        QGraphicsItem.mousePressEvent(self, event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._viewer.roiClicked(self)


class RectROI(QGraphicsRectItem):

    def __init__(self, viewer):
        QGraphicsItem.__init__(self)
        self._viewer = viewer
        pen = QPen(Qt.GlobalColor.yellow)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setFlags(self.GraphicsItemFlag.ItemIsSelectable)

    def mousePressEvent(self, event):
        QGraphicsItem.mousePressEvent(self, event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._viewer.roiClicked(self)


class LineROI(QGraphicsLineItem):

    def __init__(self, viewer):
        QGraphicsItem.__init__(self)
        self._viewer = viewer
        pen = QPen(Qt.GlobalColor.yellow)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setFlags(self.GraphicsItemFlag.ItemIsSelectable)

    def mousePressEvent(self, event):
        QGraphicsItem.mousePressEvent(self, event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._viewer.roiClicked(self)


class PolygonROI(QGraphicsPolygonItem):

    def __init__(self, viewer):
        QGraphicsItem.__init__(self)
        self._viewer = viewer
        pen = QPen(Qt.GlobalColor.yellow)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setFlags(self.GraphicsItemFlag.ItemIsSelectable)

    def mousePressEvent(self, event):
        QGraphicsItem.mousePressEvent(self, event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._viewer.roiClicked(self)
