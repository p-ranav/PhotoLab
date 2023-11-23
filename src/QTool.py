from PyQt6 import QtCore, QtGui, QtWidgets
from QProgressBarThread import QProgressBarThread
import functools

class QTool(QtWidgets.QWidget):

    completedSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None, name="", description="", demoImagePath=None, onRun=None, toolInput=None, onCompleted=None, toolReference=None):
        super(QTool, self).__init__(parent)
        self.setStyleSheet("background-color: rgb(22, 22, 22);")

        self.parent = parent
        self.onRun = onRun
        self.toolInput = toolInput

        self.setWindowTitle(name)

        self.titleLabel = QtWidgets.QLabel()
        self.titleLabel.setText(name)
        self.titleLabel.setStyleSheet("""
            QLabel {
                background-color: rgb(22, 22, 22);
                font-size: 40px;
                }
            """)
        self.titleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.subTitleLabel = QtWidgets.QLabel()
        self.subTitleLabel.setText(description)
        self.subTitleLabel.setStyleSheet("""
            QLabel {
                background-color: rgb(22, 22, 22);
                font-size: 20px;
                }
            """)

        self.progressWidgetLayout = QtWidgets.QVBoxLayout()
        self.progressBarLabel = QtWidgets.QLabel("")

        #self.setMaximumWidth(250)
        #self.setMaximumHeight(250)

        self.toolImageLabel = QtWidgets.QLabel()
        image = QtGui.QImage()
        image.load(demoImagePath)
        image = image.scaled(200, 200, QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding, QtCore.Qt.TransformationMode.SmoothTransformation)
        pixmap = QtGui.QPixmap.fromImage(image)
        self.toolImageLabel.setPixmap(pixmap)
        self.toolImageLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # self.progressBarLayout = QtWidgets.QVBoxLayout()
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setMinimumWidth(300)
        self.progressBar.setMinimumHeight(50)

        self.controlButtons = QtWidgets.QWidget()
        self.hbox = QtWidgets.QHBoxLayout()
        self.startButton = QtWidgets.QPushButton(self)
        self.startButton.setText("Start")
        self.startButton.setMinimumHeight(25)
        self.startButton.clicked.connect(self.start)

        self.cancelButton = QtWidgets.QPushButton(self)
        self.cancelButton.setText("Cancel")
        self.cancelButton.setMinimumHeight(25)
        self.cancelButton.clicked.connect(self.stop)

        buttons = [self.startButton, self.cancelButton]
        for b in buttons:
            b.setStyleSheet('''
                background-color: rgb(44, 44, 44);
                height: 30px;
                width: 100px;
            ''')

        self.hbox.addWidget(self.startButton, QtCore.Qt.AlignmentFlag.AlignRight)
        self.hbox.addWidget(self.cancelButton, QtCore.Qt.AlignmentFlag.AlignRight)
        self.controlButtons.setLayout(self.hbox)
        self.controlButtons.setStyleSheet('''
            height: 30px;
        ''')

        self.progressWidgetLayout.addWidget(self.titleLabel, QtCore.Qt.AlignmentFlag.AlignCenter)
        # self.progressWidgetLayout.addWidget(self.subTitleLabel)
        self.progressWidgetLayout.addWidget(self.toolImageLabel)
        self.progressWidgetLayout.addWidget(self.controlButtons, QtCore.Qt.AlignmentFlag.AlignRight)

        self.setLayout(self.progressWidgetLayout)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)

        # Initialize the thread
        self.progressBarThread = QProgressBarThread()
        self.completedSignal.connect(functools.partial(onCompleted, toolReference))

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
            self.progressBarThread.completeSignal.connect(self.stop)
            self.progressBarThread.taskFunction = self.onRun
            if self.toolInput is not None:
                self.progressBarThread.taskFunctionArgs = [self.toolInput]
            else:
                self.progressBarThread.taskFunctionArgs = []
            self.progressBarThread.start()

    def stop(self):
        self.progressBar.setValue(100)
        self.hide()
        self.completedSignal.emit()

    def closeEvent(self, event):
        self.stop()
        event.accept()