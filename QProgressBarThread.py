from PyQt6 import QtCore

class QProgressBarThread(QtCore.QThread):
    # Signals to relay thread progress to the main GUI thread
    progressSignal = QtCore.pyqtSignal(int, str)
    completeSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(QProgressBarThread, self).__init__(parent)
        # You can change variables defined here after initialization - but before calling start()
        self.maxRange = 100
        self.taskFunction = None
        self.taskFunctionOutput = None

    def run(self):
        self.taskFunctionOutput = self.taskFunction(self.progressSignal)
        self.completeSignal.emit()