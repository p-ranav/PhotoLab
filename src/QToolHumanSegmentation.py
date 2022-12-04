from QTool import QTool
import os

class QToolHumanSegmentation(QTool):
    def __init__(self, parent=None, toolInput=None, onCompleted=None):
        super(QToolHumanSegmentation, self).__init__(parent, "Human Segmentation", 
                                             "Extract humans from images\nhttps://github.com/nadermx/backgroundremover", 
                                             "images/HumanSegmentation_02.jpg", 
                                             self.onRun, toolInput, onCompleted, self)

        self.parent = parent
        self.output = None

    def onRun(self, progressSignal, args):
        image = args[0]

        from BackgroundRemoval import remove2
        from FileUtils import merge_files

        # Merge NN model files into pth file if not exists
        if not os.path.exists("models/u2net_human_seg.pth"):
            merge_files("u2net_human_seg.pth", "models")

        progressSignal.emit(10, "Loading current pixmap")
        self.output = remove2(image, progressSignal, model_name="u2net_human_seg")