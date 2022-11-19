from PyQt6 import QtCore, QtGui, QtWidgets
from QProgressBarThread import QProgressBarThread

class QTool(QtWidgets.QWidget):

    completedSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None, onRun=None, toolInput=None, onCompleted=None):
        super(QTool, self).__init__(parent)

        self.parent = parent
        self.onRun = onRun
        self.toolInput = toolInput
        self.onCompleted = onCompleted

        self.titleLabel = QtWidgets.QLabel()
        self.titleLabel.setText("Anime GAN v2")
        self.titleLabel.setStyleSheet("""
            QLabel {
                font-size: 40px;
                }
            """)
        self.titleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.subTitleLabel = QtWidgets.QLabel()
        self.subTitleLabel.setText("Transform photos of real-world scenes into anime style images\nhttps://github.com/bryandlee/animegan2-pytorch")
        self.subTitleLabel.setStyleSheet("""
            QLabel {
                font-size: 20px;
                }
            """)

        self.progressWidgetLayout = QtWidgets.QVBoxLayout()
        self.progressBarLabel = QtWidgets.QLabel("")

        self.setMaximumWidth(500)
        self.setMaximumHeight(500)

        self.toolImageLabel = QtWidgets.QLabel()
        image = QtGui.QImage()
        image.load("images/AnimeGanV2_05.jpg")
        image = image.scaled(800, 800, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        pixmap = QtGui.QPixmap.fromImage(image)
        self.toolImageLabel.setPixmap(pixmap)

        # self.progressBarLayout = QtWidgets.QVBoxLayout()
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setMinimumWidth(300)
        self.progressBar.setMinimumHeight(50)

        self.controlButtons = QtWidgets.QWidget()
        self.hbox = QtWidgets.QHBoxLayout()
        self.startButton = QtWidgets.QPushButton(self)
        font = self.startButton.font()
        font.setPointSize(12)
        self.startButton.setText("Start")
        self.startButton.setFont(font)
        self.startButton.setMinimumHeight(25)
        self.startButton.clicked.connect(self.start)
        self.cancelButton = QtWidgets.QPushButton(self)
        self.cancelButton.setText("Cancel")
        self.cancelButton.setFont(font)
        self.cancelButton.setMinimumHeight(25)
        self.cancelButton.clicked.connect(self.stop)
        self.hbox.addWidget(self.startButton, QtCore.Qt.AlignmentFlag.AlignRight)
        self.hbox.addWidget(self.cancelButton, QtCore.Qt.AlignmentFlag.AlignRight)
        self.controlButtons.setLayout(self.hbox)

        self.progressWidgetLayout.addWidget(self.titleLabel, QtCore.Qt.AlignmentFlag.AlignCenter)
        self.progressWidgetLayout.addWidget(self.subTitleLabel)
        self.progressWidgetLayout.addWidget(self.toolImageLabel)
        self.progressWidgetLayout.addWidget(self.controlButtons, QtCore.Qt.AlignmentFlag.AlignRight)

        self.setLayout(self.progressWidgetLayout)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)

        # Initialize the thread
        self.progressBarThread = QProgressBarThread()

        self.completedSignal.connect(self.onCompleted)

    @QtCore.pyqtSlot(int, str)
    def updateProgressBar(self, e, label):
        self.progressBar.setValue(e)
        self.progressBarLabel.setText(label)

    def start(self):
        self.controlButtons.hide()
        self.progressWidgetLayout.addWidget(self.progressBarLabel)
        self.progressWidgetLayout.addWidget(self.progressBar)

        self.progressBarLabel.setText("Starting")
        self.show()

        if not self.progressBarThread.isRunning():
            self.progressBarThread.maxRange = 1000
            self.progressBarThread.progressSignal.connect(self.updateProgressBar)
            self.progressBarThread.taskFunction = self.onRun
            if self.toolInput:
                self.progressBarThread.taskFunctionArgs = [self.toolInput]
            self.progressBarThread.start()

    def stop(self):
        self.progressBar.setValue(100)
        self.hide()
        self.completedSignal.emit()

    def closeEvent(self, event):
        self.stop()
        event.accept()