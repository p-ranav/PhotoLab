from QTool import QTool
import os

class QToolBackgroundRemoval(QTool):
    def __init__(self, parent=None, toolInput=None, onCompleted=None):
        super(QToolBackgroundRemoval, self).__init__(parent, "Background Removal", 
                                             "Remove Background from images\nhttps://github.com/nadermx/backgroundremover", 
                                             "images/BackgroundRemoval_06.jpg", 
                                             self.onRun, toolInput, onCompleted, self)

        self.parent = parent
        self.output = None

    def onRun(self, progressSignal, args):
        image = args[0]

        from BackgroundRemoval import remove2
        from FileUtils import merge_files

        # Merge NN model files into pth file if not exists
        if not os.path.exists("models/u2net.pth"):
            merge_files("u2net.pth", "models")

        progressSignal.emit(10, "Loading current pixmap")
        self.output = remove2(image, progressSignal, model_name="u2net")