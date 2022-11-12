""" QtImageViewer.py: PyQt image viewer widget based on QGraphicsView with mouse zooming/panning and ROIs.
"""

import os.path

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, pyqtSignal, QEvent, QSize
    from PyQt6.QtGui import QImage, QPixmap, QPainterPath, QMouseEvent, QPainter, QPen
    from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QSizePolicy, \
        QGraphicsItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem, QGraphicsPolygonItem
except ImportError:
    try:
        from PyQt5.QtCore import Qt, QRect, QRectF, QPoint, QPointF, pyqtSignal, QEvent, QSize
        from PyQt5.QtGui import QImage, QPixmap, QPainterPath, QMouseEvent, QPainter, QPen
        from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QSizePolicy, \
            QGraphicsItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem, QGraphicsPolygonItem
    except ImportError:
        raise ImportError("Requires PyQt (version 5 or 6)")

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
from math import sin, radians
from PIL import Image, ImageFilter
from QColorPicker import QColorPicker
from PIL.ImageQt import ImageQt
import cv2
import random

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
        self.zoomOutButton = Qt.MouseButton.RightButton  # Pop end of zoom stack (double click clears zoom stack).
        self.panButton = Qt.MouseButton.MiddleButton  # Drag to pan.
        self.wheelZoomFactor = 1.25  # Set to None or 1 to disable mouse wheel zoom.
        self.zoomLevel = 1

        # Stack of QRectF zoom boxes in scene coordinates.
        # !!! If you update this manually, be sure to call updateViewer() to reflect any changes.
        self.zoomStack = []

        # Flags for active zooming/panning.
        self._isZooming = False
        self._isPanning = False
        
        # Flags for active cropping
        # Set to true when using the crop tool with toolbar
        self._isCropping = False
        self._cropItem = None
        self._cropRect = None

        # Flags for active selecting
        # Set to true when using the select tool with toolbar
        self._isSelecting = False
        self.selectPoints = []
        self.path = None
        self.selectPixmap = None
        self.selectPainterPaths = []
        self._shiftPressedWhileSelecting = False

        # Flags for spot removal tool
        self._isRemovingSpots = False

        # Store temporary position in screen pixels or scene units.
        self._pixelPosition = QPoint()
        self._scenePosition = QPointF()

        # Track mouse position. e.g., For displaying coordinates in a UI.
        # self.setMouseTracking(True)

        # ROIs.
        self.ROIs = []

        # # For drawing ROIs.
        # self.drawROI = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.OriginalImage = None

        self.ColorPicker = None

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

    def image(self):
        """ Returns the scene's current image pixmap as a QImage, or else None if no image exists.
        :rtype: QImage | None
        """
        if self.hasImage():
            return self._image.pixmap().toImage()
        return None

    def setImage(self, image):
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
                height, width = image.shape
                bytes = image.tobytes()
                qimage = QImage(bytes, width, height, QImage.Format.Format_Grayscale8)
                pixmap = QPixmap.fromImage(qimage)
        else:
            raise RuntimeError("ImageViewer.setImage: Argument must be a QImage, QPixmap, or numpy.ndarray.")
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

    def open(self, filepath=None):
        """ Load an image from file.
        Without any arguments, loadImageFromFile() will pop up a file dialog to choose the image file.
        With a fileName argument, loadImageFromFile(fileName) will attempt to load the specified image file directly.
        """
        if filepath is None:
            filepath, dummy = QFileDialog.getOpenFileName(self, "Open image file.")
        if len(filepath) and os.path.isfile(filepath):
            self._current_filename = filepath
            image = QImage(filepath)
            self.setImage(image)

    def save(self, filepath=None):
        path = self._current_filename
        if filepath:
            path = filepath

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

        # self.ColorPicker.setRGB((r, g, b))
        # self.setImage(currentPixmap.toImage())

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

        if self._isCropping:
            # Start dragging a region crop box?
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self._pixelPosition = event.pos()  # store pixel position
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                QGraphicsView.mousePressEvent(self, event)
                event.accept()
                self._isCropping = True
                
                # Remove previous crop
                if self._cropItem:
                    self.scene.removeItem(self._cropItem)

                return
        if self._isSelecting:
            # TODO: https://stackoverflow.com/questions/63568214/qpainter-delete-previously-drawn-shapes
            #
            #
            # Start dragging a region crop box?
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                if self.selectPixmap == None:
                    self.selectPixmap = self.pixmap()
                self._pixelPosition = event.pos()  # store pixel position
                self.selectPoints.append(QPointF(self.mapToScene(event.pos())))
                QGraphicsView.mousePressEvent(self, event)
                self.buildPath()
                event.accept()
                self._isSelecting = True
                return
        elif self._isRemovingSpots:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self.removeSpots(event)
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

        if not self._isCropping:
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
        else:
            # Finish dragging a region crop box?
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                QGraphicsView.mouseReleaseEvent(self, event)
                self._cropRect = self.scene.selectionArea().boundingRect().intersected(self.sceneRect())
                # Clear current selection area (i.e. rubberband rect).
                self.scene.setSelectionArea(QPainterPath())
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                # If zoom box is 3x3 screen pixels or smaller, do not zoom and proceed to process as a click release.
                zoomPixelWidth = abs(event.pos().x() - self._pixelPosition.x())
                zoomPixelHeight = abs(event.pos().y() - self._pixelPosition.y())
                if zoomPixelWidth > 3 and zoomPixelHeight > 3:
                    if self._cropRect.isValid() and (self._cropRect != self.sceneRect()):
                        # Create a new crop item using user-drawn rectangle
                        self._cropItem = QCropItem(self._image, self._cropRect)

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
        elif self._isSelecting:
            if self._shiftPressedWhileSelecting:
                self.selectPoints.append(QPointF(self.mapToScene(event.pos())))
                self.buildPath()

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
                print(i)
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
        if self._isCropping:
            if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
                # Crop the pixmap
                cropQPixmap = self.pixmap().copy(self._cropRect.toAlignedRect())

                # Crop the original image as well
                self.OriginalImage = self.OriginalImage.copy(self._cropRect.toAlignedRect())

                self.setImage(cropQPixmap)

                # Remove crop item
                if self._cropItem:
                    if self._cropItem in self.scene.items():
                        self.scene.removeItem(self._cropItem)
                del self._cropItem
                self._cropItem = None

                self.updateViewer()
                self.viewChanged.emit()
                event.accept()

            elif event.key() == Qt.Key_Escape:
                # If cropping
                # Leave crop mode
                if self._cropItem:
                    if self._cropItem in self.scene.items():
                        self.scene.removeItem(self._cropItem)
                del self._cropItem
                self._cropItem = None

        elif self._isSelecting:
            if event.key() == Qt.Key_Shift:
                self._shiftPressedWhileSelecting = True

            if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:

                # if len(self.selectPoints) > 1:
                #     self.path.quadTo(self.selectPoints[-2], self.selectPoints[-1])

                self.path.quadTo(self.selectPoints[-1], self.selectPoints[-1])

                output = QImage(self.pixmap().toImage().size(), QImage.Format_ARGB32)
                output.fill(Qt.transparent)
                painter = QPainter(output)
                painter.setClipPath(self.path)
                painter.drawImage(QPoint(), self.pixmap().toImage())
                painter.end()
                # To avoid useless transparent background you can crop it like that:
                output = output.copy(self.path.boundingRect().toRect())
                self.setImage(output)
                self.selectPoints = []

                self.path.clear()
                for pathItem in self.selectPainterPaths:
                    if pathItem and pathItem in self.scene.items():
                        self.scene.removeItem(pathItem)
                
                self.selectPainterPaths = []
                self.path = None

            elif event.key() == Qt.Key_Escape:
                self.selectPoints = []
                self.path.clear()
                for pathItem in self.selectPainterPaths:
                    if pathItem and pathItem in self.scene.items():
                        self.scene.removeItem(pathItem)
                self.selectPainterPaths = []
                self.path = None

        event.accept()

    def keyReleaseEvent(self, event):
        if self._isSelecting:
            if event.key() == Qt.Key_Shift:
                self._shiftPressedWhileSelecting = False

    def buildPath(self):
        '''
        https://stackoverflow.com/questions/63016214/drawing-multi-point-curve-with-pyqt5
        '''
        factor = 0.05
        cp1 = QPointF(0, 0)
        if self.path in self.scene.items():
            self.scene.removeItem(self.path)
            del self.path
        self.path = QtGui.QPainterPath(self.selectPoints[0])
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
            else:
                # use the control point "cp1" set in the *previous* cycle
                self.path.cubicTo(cp1, cp2, current)

            revSource = QtCore.QLineF.fromPolar(target.length() * factor, angle).translated(current)
            cp1 = revSource.p2()

        # the final curve, that joins to the last point
        if len(self.selectPoints) > 1:
            self.path.quadTo(self.selectPoints[-2], self.selectPoints[-1])

        self.path.quadTo(self.selectPoints[-1], self.selectPoints[-1])

        '''
        Alternate simpler solution that does not draw any curves
        just lines:
        if not self.path:
            self.path = QtGui.QPainterPath(self.selectPoints[0])
        if len(self.selectPoints) > 1:
            self.path.quadTo(self.selectPoints[-2], self.selectPoints[-1])
        '''
      
        
        self.pathItem = self.scene.addPath(self.path)
        self.selectPainterPaths.append(self.pathItem)

        penWidth = int(5 / self.zoomLevel)

        self.pathItem.setPen(
            QtGui.QPen(
                QtGui.QColor(255, 255, 255, 127),
                penWidth if penWidth > 0 else 1,
                QtCore.Qt.SolidLine,
                QtCore.Qt.RoundCap,
                QtCore.Qt.RoundJoin,
            )
        )
        self.pathItem.setBrush(QtGui.QColor(255, 0, 0, 10))

    def removeSpots(self, event):
        currentPixmap = self._image.pixmap()
        currentImage = self.QPixmapToImage(currentPixmap)
        pixelAccess = currentImage.load()
        scene_pos = self.mapToScene(event.pos())
        x = scene_pos.x()
        y = scene_pos.y()

        THRESHOLD = 18

        def luminance(pixel):
            return (0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2])

        def is_similar(pixel_a, pixel_b, threshold):
            return abs(luminance(pixel_a) - luminance(pixel_b)) < threshold

        # Prepare numpy array of a small region of the image
        # around the point where the user clicked
        # Perform K-means clustering and find the average color
        # of this small image
        # Set the pixel of the area to be that average color
        # https://stackoverflow.com/questions/43111029/how-to-find-the-average-colour-of-an-image-in-python-with-opencv
        def dominant_rgb(x, y, sample_size):
            small_image = currentPixmap.toImage().copy(QRect(QPoint(int(x - sample_size), int(y - sample_size)), QPoint(int(x + sample_size), int(y + sample_size))))
            small_image_numpy = self.QImageToCvMat(small_image)
            pixels = np.float32(small_image_numpy.reshape(-1, 4))

            n_colors = 5
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
            flags = cv2.KMEANS_RANDOM_CENTERS

            _, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, flags)
            _, counts = np.unique(labels, return_counts=True)

            dominant = palette[np.argmax(counts)]
            return dominant

        # Prepare numpy array of a small region of the image
        # around the point where the user clicked
        # Perform K-means clustering and find the average color
        # of this small image
        # Set the pixel of the area to be that average color
        # https://stackoverflow.com/questions/43111029/how-to-find-the-average-colour-of-an-image-in-python-with-opencv
        def average_rgb(x, y, sample_size):

            ## Find neighbor pixels in a circle around (x, y)
            #neighbors = []
            #for i in range(int(x - sample_size), int(x + sample_size)):
            #    for j in range(int(y - sample_size), int(y + sample_size)):
            #        dist = (i - x) * (i - x) + (j - y) * (j - y)
            #        if dist <= brush_size:
            #            # point is inside circle
            #            neighbors.append(pixelAccess[i, j])
            
            #average = np.mean(np.array(neighbors), axis=0)
            #return average

            small_image = currentPixmap.toImage().copy(QRect(QPoint(int(x - sample_size), int(y - sample_size)), QPoint(int(x + sample_size), int(y + sample_size))))
            small_image_pillow = self.QImageToImage(small_image)
            small_image_pillow = small_image_pillow.filter(ImageFilter.SMOOTH)
            small_image_pillow = small_image_pillow.filter(ImageFilter.SMOOTH_MORE)
            small_image = self.ImageToQPixmap(small_image_pillow).toImage()
            small_image_numpy = self.QImageToCvMat(small_image)
            average = small_image_numpy.mean(axis=0).mean(axis=0)
            return average

        dominant = dominant_rgb(x, y, 1)
        # average = average_rgb(x, y, 60)

        brush_size = 200
        if self.zoomLevel > 0:
            brush_size = int(brush_size / self.zoomLevel)

        # Find neighbor pixels in a circle around (x, y)
        neighbors = []
        for i in range(int(x - brush_size), int(x + brush_size)):
            for j in range(int(y - brush_size), int(y + brush_size)):
                dist = (i - x) * (i - x) + (j - y) * (j - y)

                # Introduce some randomnes in the distance check
                if dist <= brush_size + random.randint(0, 15):
                    # point is inside circle
                    neighbors.append([i, j])

        # Sort the list of neighbors by distance
        neighbors.sort(key=lambda p: (p[0] - x) * (p[0] - x) + (p[1] - y) * (p[1] - y))

        # For each point, update the pixel by averaging
        for point in neighbors:
            i, j = point
            sample_size = int(brush_size / 10)
            pr, pg, pb, _ = pixelAccess[i, j] # current neighbor pixel inside the brush circle
            ar, ag, ab, _ = average_rgb(i, j, sample_size)
            dr, dg, db, _ = dominant # pixelAccess[x, y]
            if is_similar((dr, dg, db), (pr, pg, pb), 15):
                # Update this pixel
                rr = 0
                if ar > 150:
                    rr = random.randint(-3, 3)
                rg = 0
                if ag > 150:
                    rg = random.randint(-3, 3)
                rb = 0
                if ab > 150:
                    rb = random.randint(-3, 3)
                pixelAccess[i, j] = (int(ar + rr), int(ag + rg), int(ab + rb))

        #average_sample_size = int(brush_size / 10)
        #for ny in range(int(x-average_sample_size), int(x+average_sample_size)):
        #    for nx in range(int(y-average_sample_size), int(y+average_sample_size)):    
        #        if nx > 0 and nx < currentImage.width and nx + 2 < currentImage.width:
        #            if ny > 0 and ny < currentImage.height and nx + 2 < currentImage.height:
        #                px1 = pixelAccess[nx, ny] #0/0
        #                px2 = pixelAccess[nx, ny+1] #0/1
        #                px3 = pixelAccess[nx, ny+2] #0/2
        #                px4 = pixelAccess[nx+1, ny] #1/0
        #                px5 = pixelAccess[nx+1, ny+1] #1/1
        #                px6 = pixelAccess[nx+1, ny+2] #1/2
        #                px7 = pixelAccess[nx+2, ny] #2/0
        #                px8 = pixelAccess[nx+2, ny+1] #2/1
        #                px9 = pixelAccess[nx+2, ny+2] #2/2

        #                average = np.average([px1, px2, px3, px4, px5, px6, px7, px8, px9], axis=0)
        #                ar = int(average[0])
        #                ag = int(average[1])
        #                ab = int(average[2])
        #                # Update this pixel
        #                rr = 0
        #                if ar > 200:
        #                    rr = random.randint(-3, 3)
        #                rg = 0
        #                if ag > 200:
        #                    rg = random.randint(-3, 3)
        #                rb = 0
        #                if ab > 200:
        #                    rb = random.randint(-3, 3)
        #                pixelAccess[nx, ny] = (int(ar + rr), int(ag + rg), int(ab + rb))

        # Update the pixmap
        updatedPixmap = self.ImageToQPixmap(currentImage)
        updatedPixmap.save("test.png", "PNG", 100);
        self.setImage(updatedPixmap)
        self.OriginalImage = updatedPixmap

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