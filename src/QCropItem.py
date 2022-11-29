# https://stackoverflow.com/questions/50775036/pyqt-qgraphicsview-dark-area-outside-rectangle

import sys

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QPainterPath, QPainter
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsPathItem, QApplication, QGraphicsView, QGraphicsScene


class HandleItem(QGraphicsRectItem):
    def __init__(self, position_flags, parent, imageSize):
        w = imageSize[0]
        h = imageSize[1]
        max_dim = max(w, h)
        handleItemSize = int(max_dim / 50)
        if handleItemSize < 4:
            handleItemSize = 4
        start = -1 * int(handleItemSize / 2)
        QGraphicsRectItem.__init__(self, start, start, handleItemSize, handleItemSize, parent)
        self._positionFlags = position_flags

        self.setBrush(QBrush(QColor(81, 168, 220, 200)))
        self.setPen(QPen(QColor(0, 0, 0, 255), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges)

    def positionflags(self):
        return self._positionFlags

    def itemChange(self, change, value):
        retVal = value
        if change == self.GraphicsItemChange.ItemPositionChange:
            retVal = self.restrictPosition(value)
        elif change == self.GraphicsItemChange.ItemPositionHasChanged:
            pos = value
            if self.positionflags() == SizeGripItem.TopLeft:
                self.parentItem().setTopLeft(pos)
            elif self.positionflags() == SizeGripItem.Top:
                self.parentItem().setTop(pos.y())
            elif self.positionflags() == SizeGripItem.TopRight:
                self.parentItem().setTopRight(pos)
            elif self.positionflags() == SizeGripItem.Right:
                self.parentItem().setRight(pos.x())
            elif self.positionflags() == SizeGripItem.BottomRight:
                self.parentItem().setBottomRight(pos)
            elif self.positionflags() == SizeGripItem.Bottom:
                self.parentItem().setBottom(pos.y())
            elif self.positionflags() == SizeGripItem.BottomLeft:
                self.parentItem().setBottomLeft(pos)
            elif self.positionflags() == SizeGripItem.Left:
                self.parentItem().setLeft(pos.x())
        return retVal

    def restrictPosition(self, newPos):
        retVal = self.pos()

        if self.positionflags() & SizeGripItem.Top or self.positionflags() & SizeGripItem.Bottom:
            retVal.setY(newPos.y())

        if self.positionflags() & SizeGripItem.Left or self.positionflags() & SizeGripItem.Right:
            retVal.setX(newPos.x())

        if self.positionflags() & SizeGripItem.Top and retVal.y() > self.parentItem()._rect.bottom():
            retVal.setY(self.parentItem()._rect.bottom())

        elif self.positionflags() & SizeGripItem.Bottom and retVal.y() < self.parentItem()._rect.top():
            retVal.setY(self.parentItem()._rect.top())

        if self.positionflags() & SizeGripItem.Left and retVal.x() > self.parentItem()._rect.right():
            retVal.setX(self.parentItem()._rect.right())

        elif self.positionflags() & SizeGripItem.Right and retVal.x() < self.parentItem()._rect.left():
            retVal.setX(self.parentItem()._rect.left())

        return retVal


class SizeGripItem(QGraphicsItem):
    Top = 0x01
    Bottom = 0x1 << 1
    Left = 0x1 << 2
    Right = 0x1 << 3
    TopLeft = Top | Left
    BottomLeft = Bottom | Left
    TopRight = Top | Right
    BottomRight = Bottom | Right

    handleCursors = {
        TopLeft: Qt.CursorShape.SizeFDiagCursor,
        Top: Qt.CursorShape.SizeVerCursor,
        TopRight: Qt.CursorShape.SizeBDiagCursor,
        Left: Qt.CursorShape.SizeHorCursor,
        Right: Qt.CursorShape.SizeHorCursor,
        BottomLeft: Qt.CursorShape.SizeBDiagCursor,
        Bottom: Qt.CursorShape.SizeVerCursor,
        BottomRight: Qt.CursorShape.SizeFDiagCursor,
    }

    def __init__(self, parent, imageSize):
        QGraphicsItem.__init__(self, parent)
        self._handleItems = []
        self.imageSize = imageSize

        self._rect = QRectF(0, 0, 0, 0)
        if self.parentItem():
            self._rect = self.parentItem().rect()

        for flag in (self.TopLeft, self.Top, self.TopRight, self.Right,
                     self.BottomRight, self.Bottom, self.BottomLeft, self.Left):
            handle = HandleItem(flag, self, imageSize)
            handle.setCursor(self.handleCursors[flag])
            self._handleItems.append(handle)

        self.updateHandleItemPositions()

    def boundingRect(self):
        if self.parentItem():
            return self._rect
        else:
            return QRectF(0, 0, 0, 0)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(127, 127, 127), 2.0, Qt.PenStyle.DashLine))
        painter.drawRect(self._rect)

    def doResize(self):
        self.parentItem().setRect(self._rect)
        self.updateHandleItemPositions()

    def updateHandleItemPositions(self):
        for item in self._handleItems:
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)

            if item.positionflags() == self.TopLeft:
                item.setPos(self._rect.topLeft())
            elif item.positionflags() == self.Top:
                item.setPos(self._rect.left() + self._rect.width() / 2 - 1,
                            self._rect.top())
            elif item.positionflags() == self.TopRight:
                item.setPos(self._rect.topRight())
            elif item.positionflags() == self.Right:
                item.setPos(self._rect.right(),
                            self._rect.top() + self._rect.height() / 2 - 1)
            elif item.positionflags() == self.BottomRight:
                item.setPos(self._rect.bottomRight())
            elif item.positionflags() == self.Bottom:
                item.setPos(self._rect.left() + self._rect.width() / 2 - 1,
                            self._rect.bottom())
            elif item.positionflags() == self.BottomLeft:
                item.setPos(self._rect.bottomLeft())
            elif item.positionflags() == self.Left:
                item.setPos(self._rect.left(),
                            self._rect.top() + self._rect.height() / 2 - 1)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def setTop(self, v):
        self._rect.setTop(v)
        self.doResize()

    def setRight(self, v):
        self._rect.setRight(v)
        self.doResize()

    def setBottom(self, v):
        self._rect.setBottom(v)
        self.doResize()

    def setLeft(self, v):
        self._rect.setLeft(v)
        self.doResize()

    def setTopLeft(self, v):
        self._rect.setTopLeft(v)
        self.doResize()

    def setTopRight(self, v):
        self._rect.setTopRight(v)
        self.doResize()

    def setBottomRight(self, v):
        self._rect.setBottomRight(v)
        self.doResize()

    def setBottomLeft(self, v):
        self._rect.setBottomLeft(v)
        self.doResize()

class QCropItem(QGraphicsPathItem):
    def __init__(self, parent, cropRect, imageSize):
        QGraphicsPathItem.__init__(self, parent)
        self.extern_rect = parent.boundingRect()
        self.intern_rect = cropRect
        self.setBrush(QColor(10, 100, 100, 100))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        SizeGripItem(self, imageSize)
        self.create_path()

    def create_path(self):
        self._path = QPainterPath()
        self._path.addRect(self.extern_rect)
        self._path.moveTo(self.intern_rect.topLeft())
        self._path.addRect(self.intern_rect)
        self.setPath(self._path)


    def rect(self):
        return self.intern_rect

    def setRect(self, rect):
        self.intern_rect = rect
        self.create_path()
