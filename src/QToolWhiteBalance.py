from QTool import QTool
import os

class QToolWhiteBalance(QTool):
    def __init__(self, parent=None, toolInput=None, onCompleted=None):
        super(QToolWhiteBalance, self).__init__(parent, "White Balance Correction", 
                                             "Correct a camera image that has been improperly white balanced\nhttps://github.com/mahmoudnafifi/WB_sRGB",
                                             "images/WhiteBalance_08.jpg", 
                                             self.onRun, toolInput, onCompleted, self)

        self.parent = parent
        self.output = None

    def onRun(self, progressSignal, args):
        # https://github.com/mahmoudnafifi/WB_sRGB
        import cv2
        import WhiteBalance
        import numpy as np
        from PIL import Image

        progressSignal.emit(10, "Loading current pixmap")
        image = args[0]
        image_ndarray = np.asarray(image)
        b, g, r, a = cv2.split(image_ndarray)

        # use gamut_mapping = 1 for scaling, 2 for clipping (our paper's results
        # reported using clipping). If the image is over-saturated, scaling is
        # recommended.
        gamut_mapping = 2

        wbModel = WhiteBalance.WBsRGB(gamut_mapping=gamut_mapping)

        self.output = wbModel.correctImage(np.dstack((r, g, b)))
        self.output = (self.output * 255).astype(np.uint8)
        b, g, r = cv2.split(self.output)
        self.output = np.dstack((r, g, b, a))
        self.output = Image.fromarray(self.output)