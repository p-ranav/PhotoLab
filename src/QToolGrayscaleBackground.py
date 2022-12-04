from QTool import QTool
import os

class QToolGrayscaleBackground(QTool):
    def __init__(self, parent=None, toolInput=None, onCompleted=None):
        super(QToolGrayscaleBackground, self).__init__(parent, "Grayscale Background", 
                                             "Gray out the background to highlight the subject", 
                                             "images/GrayscaleBackground.jpg", 
                                             self.onRun, toolInput, onCompleted, self)

        self.parent = parent
        self.output = None

    def onRun(self, progressSignal, args):
        image = args[0].copy()

        from BackgroundRemoval import remove2
        from FileUtils import merge_files

        # Merge NN model files into pth file if not exists
        if not os.path.exists("models/u2net.pth"):
            merge_files("u2net.pth", "models")

        progressSignal.emit(10, "Loading current pixmap")
        self.output = remove2(image, progressSignal, model_name="u2net")