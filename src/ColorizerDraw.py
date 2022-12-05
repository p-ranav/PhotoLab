import datetime
import glob
import os
import sys

import cv2
import numpy as np
import torch
from einops import rearrange
from PyQt6.QtCore import QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication, QFileDialog, QWidget
from skimage import color

from ColorizerLabGamut import snap_ab
from ColorizerUiControl import UIControl

class GUIDraw(QWidget):

    # Signals
    update_color = pyqtSignal(str)
    update_gammut = pyqtSignal(object)
    used_colors = pyqtSignal(object)
    update_ab = pyqtSignal(object)
    update_result = pyqtSignal(object)

    def __init__(self, model=None, load_size=224, win_size=512, device='cpu'):
        QWidget.__init__(self)
        self.image_file = None
        self.pos = None
        self.model = model
        self.win_size = win_size
        self.load_size = load_size
        self.device = device
        self.setFixedSize(win_size, win_size)
        self.uiControl = UIControl(win_size=win_size, load_size=load_size)
        self.move(win_size, win_size)
        self.movie = True
        self.init_color()  # initialize color
        self.im_gray3 = None
        self.eraseMode = False
        self.ui_mode = 'none'   # stroke or point
        self.image_loaded = False
        self.use_gray = True
        self.total_images = 0
        self.image_id = 0
        self.saveResult = False
        
    def clock_count(self):
        self.count_secs -= 1
        self.update()

    def init_result(self, im_bgr):
        # self.read_image(image_file.encode('utf-8'))  # read an image
        self.read_image(im_bgr)  # read an image
        self.reset()

    def get_batches(self, img_dir):
        self.img_list = glob.glob(os.path.join(img_dir, '*.JPEG'))
        self.total_images = len(self.img_list)
        img_first = self.img_list[0]
        self.init_result(img_first)

    def nextImage(self):
        self.save_result()
        self.image_id += 1
        if self.image_id == self.total_images:
            print('you have finished all the results')
            sys.exit()
        img_current = self.img_list[self.image_id]
        # self.reset()
        self.init_result(img_current)
        self.reset_timer()

    def read_image(self, im_bgr):
        # self.result = None
        self.image_loaded = True
        self.im_full = im_bgr.copy()
        # get image for display
        h, w, c = self.im_full.shape
        ar = float(w) / float(h)

        max_width = max(h, w)
        r = self.win_size / float(max_width)
        self.scale = float(self.win_size) / self.load_size
        print('scale = %f' % self.scale)
        rw = int(round(r * w / 4.0) * 4)
        rh = int(round(r * h / 4.0) * 4)

        self.im_win = cv2.resize(self.im_full, (rw, rh), interpolation=cv2.INTER_CUBIC)

        self.dw = int((self.win_size - rw) // 2)
        self.dh = int((self.win_size - rh) // 2)
        self.win_w = rw
        self.win_h = rh

        print("rw,rh", (rw, rh))
        print("dw,dh", (self.dw, self.dh))
        print("w,h", (w, h))

        self.uiControl.setImageSize((rw, rh))
        im_gray = cv2.cvtColor(im_bgr, cv2.COLOR_BGR2GRAY)
        self.im_gray3 = cv2.cvtColor(im_gray, cv2.COLOR_GRAY2BGR)

        self.gray_win = cv2.resize(self.im_gray3, (rw, rh), interpolation=cv2.INTER_CUBIC)
        im_bgr = cv2.resize(im_bgr, (self.load_size, self.load_size), interpolation=cv2.INTER_CUBIC)
        self.im_rgb = cv2.cvtColor(im_bgr, cv2.COLOR_BGR2RGB)
        lab_win = color.rgb2lab(self.im_win[:, :, ::-1])

        self.im_lab = color.rgb2lab(im_bgr[:, :, ::-1])
        self.im_l = self.im_lab[:, :, 0]
        self.l_win = lab_win[:, :, 0]
        self.im_ab = self.im_lab[:, :, 1:]
        self.im_size = self.im_rgb.shape[0:2]

        self.im_ab0 = np.zeros((2, self.load_size, self.load_size))
        self.im_mask0 = np.zeros((1, self.load_size, self.load_size))
        self.brushWidth = 2 * self.scale

    def update_im(self):
        self.update()
        QApplication.processEvents()

    def update_ui(self, move_point=True):
        if self.ui_mode == 'none':
            return False
        is_predict = False
        snap_qcolor = self.calibrate_color(self.user_color, self.pos)
        self.color = snap_qcolor
        # self.emit(SIGNAL('update_color'), str('background-color: %s' % self.color.name()))
        self.update_color.emit(str('background-color: %s' % self.color.name()))

        if self.ui_mode == 'point':
            if move_point:
                self.uiControl.movePoint(self.pos, snap_qcolor, self.user_color, self.brushWidth)
            else:
                self.user_color, self.brushWidth, isNew = self.uiControl.addPoint(self.pos, snap_qcolor, self.user_color, self.brushWidth)
                if isNew:
                    is_predict = True
                    # self.predict_color()

        if self.ui_mode == 'stroke':
            self.uiControl.addStroke(self.prev_pos, self.pos, snap_qcolor, self.user_color, self.brushWidth)
        if self.ui_mode == 'erase':
            isRemoved = self.uiControl.erasePoint(self.pos)
            if isRemoved:
                is_predict = True
                # self.predict_color()
        return is_predict

    def reset(self):
        self.ui_mode = 'none'
        self.pos = None
        self.result = None
        self.user_color = None
        self.color = None
        self.uiControl.reset()
        self.init_color()
        self.compute_result()
        self.update()

    def scale_point(self, pnt):
        x = int((pnt.x() - self.dw) / float(self.win_w) * self.load_size)
        y = int((pnt.y() - self.dh) / float(self.win_h) * self.load_size)
        print(pnt, (x, y))
        return x, y

    def valid_point(self, pnt):
        if pnt is None:
            print('WARNING: no point\n')
            return None
        else:
            if pnt.x() >= self.dw and pnt.y() >= self.dh and pnt.x() < self.win_size - self.dw and pnt.y() < self.win_size - self.dh:
                x = int(np.round(pnt.x()))
                y = int(np.round(pnt.y()))
                return QPoint(x, y)
            else:
                print('WARNING: invalid point (%d, %d)\n' % (pnt.x(), pnt.y()))
                return None

    def init_color(self):
        self.user_color = QColor(128, 128, 128)  # default color red
        self.color = self.user_color

    def change_color(self, pos=None):
        print("Changing color at", pos)
        if pos is not None:
            x, y = self.scale_point(pos)
            L = self.im_lab[y, x, 0]
            # self.emit(SIGNAL('update_gamut'), L)
            self.update_gammut.emit(L)

            used_colors = self.uiControl.used_colors()
            # self.emit(SIGNAL('used_colors'), used_colors)
            self.used_colors.emit(used_colors)

            snap_color = self.calibrate_color(self.user_color, pos)
            c = np.array((snap_color.red(), snap_color.green(), snap_color.blue()), np.uint8)
            # self.emit(SIGNAL('update_ab'), c)
            self.update_ab.emit(c)

    def calibrate_color(self, c, pos):
        x, y = self.scale_point(pos)

        # snap color based on L color
        color_array = np.array((c.red(), c.green(), c.blue())).astype(
            'uint8')
        mean_L = self.im_l[y, x]
        snap_color = snap_ab(mean_L, color_array)
        snap_qcolor = QColor(snap_color[0], snap_color[1], snap_color[2])
        return snap_qcolor

    def set_color(self, c_rgb):
        c = QColor(c_rgb[0], c_rgb[1], c_rgb[2])
        self.user_color = c
        snap_qcolor = self.calibrate_color(c, self.pos)
        self.color = snap_qcolor
        # self.emit(SIGNAL('update_color'), str('background-color: %s' % self.color.name()))
        self.update_color.emit(str('background-color: %s' % self.color.name()))
        self.uiControl.update_color(snap_qcolor, self.user_color)
        self.compute_result()

    def erase(self):
        self.eraseMode = not self.eraseMode

    def load_image(self):
        img_path = QFileDialog.getOpenFileName(self, 'load an input image')[0]
        if img_path is not None and os.path.exists(img_path):
            self.init_result(img_path)

    def save_result(self):
        self.saveResult = True

    def enable_gray(self):
        self.use_gray = not self.use_gray
        self.update()

    def compute_result(self):
        im, mask = self.uiControl.get_input()
        im_mask0 = mask > 0.0
        self.im_mask0 = im_mask0.transpose((2, 0, 1)) # (1, H, W)
        im_lab = color.rgb2lab(im).transpose((2, 0, 1))#(3, H, W)
        self.im_ab0 = im_lab[1:3, :, :]

        # _im_lab is 1) normalized 2) a torch tensor
        _im_lab = self.im_lab.transpose((2,0,1))
        _im_lab = np.concatenate(((_im_lab[[0], :, :]-50) / 100, _im_lab[1:, :, :] / 110), axis=0)
        _im_lab = torch.from_numpy(_im_lab).type(torch.FloatTensor).to(self.device)

        # _img_mask is 1) normalized ab 2) flipped mask
        _img_mask = np.concatenate((self.im_ab0 / 110, (255-self.im_mask0) / 255), axis=0)
        _img_mask = torch.from_numpy(_img_mask).type(torch.FloatTensor).to(self.device)

        # _im_lab is the full color image, _img_mask is the ab_hint+mask
        ab = self.model(_im_lab.unsqueeze(0), _img_mask.unsqueeze(0))
        ab = rearrange(ab, 'b (h w) (p1 p2 c) -> b (h p1) (w p2) c', 
                        h=self.load_size//self.model.patch_size, w=self.load_size//self.model.patch_size,
                        p1=self.model.patch_size, p2=self.model.patch_size)[0]
        if torch.cuda.is_available():
            ab = ab.cpu()
        ab = ab.detach().numpy()

        ab_win = cv2.resize(ab, (self.win_w, self.win_h), interpolation=cv2.INTER_CUBIC)
        ab_win = ab_win * 110
        pred_lab = np.concatenate((self.l_win[..., np.newaxis], ab_win), axis=2)
        pred_rgb = (np.clip(color.lab2rgb(pred_lab), 0, 1) * 255).astype('uint8')
        self.result = pred_rgb
        # self.emit(SIGNAL('update_result'), self.result)
        self.update_result.emit(self.result)
        self.update()

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.fillRect(event.rect(), QColor(49, 54, 49))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.use_gray or self.result is None:
            im = self.gray_win
        else:
            im = self.result

        if im is not None:
            qImg = QImage(im.tostring(), im.shape[1], im.shape[0], QImage.Format.Format_RGB888)
            painter.drawImage(self.dw, self.dh, qImg)

        self.uiControl.update_painter(painter)
        painter.end()

    def wheelEvent(self, event):
         d = event.angleDelta().y() / 120
         self.brushWidth = min(4.05 * self.scale, max(0, self.brushWidth + d * self.scale))
         self.update_ui(move_point=True)
         self.update()

    def is_same_point(self, pos1, pos2):
        if pos1 is None or pos2 is None:
            return False
        dx = pos1.x() - pos2.x()
        dy = pos1.y() - pos2.y()
        d = dx * dx + dy * dy
        # print('distance between points = %f' % d)
        return d < 25

    def mousePressEvent(self, event):
        print('mouse press', event.pos())
        pos = self.valid_point(event.pos())

        if pos is not None:
            if event.button() == Qt.MouseButton.LeftButton:
                self.pos = pos
                self.ui_mode = 'point'
                self.change_color(pos)
                self.update_ui(move_point=False)
                self.compute_result()

            if event.button() == Qt.MouseButton.RightButton:
                # draw the stroke
                self.pos = pos
                self.ui_mode = 'erase'
                self.update_ui(move_point=False)
                self.compute_result()

    def mouseMoveEvent(self, event):
        self.pos = self.valid_point(event.pos())
        if self.pos is not None:
            if self.ui_mode == 'point':
                self.update_ui(move_point=True)
                self.compute_result()

    def mouseReleaseEvent(self, event):
        pass

    def sizeHint(self):
        return QSize(self.win_size, self.win_size)  # 28 * 8
