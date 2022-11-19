from PyQt6 import QtCore, QtGui, QtWidgets
from QProgressBarThread import QProgressBarThread

class QAnimeGANv2(QtWidgets.QWidget):

    net = None
    completedSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None, inputImage=None, onCompleted=None):
        super(QAnimeGANv2, self).__init__(parent)

        self.parent = parent
        self.inputImage = inputImage

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

        self.completedSignal.connect(onCompleted)

        self.output = None

    @QtCore.pyqtSlot(int, str)
    def updateProgressBar(self, e, label):
        self.progressBar.setValue(e)
        self.progressBarLabel.setText(label)

    def threadFunction(self, progressSignal, args):
        from torchvision.transforms.functional import to_tensor, to_pil_image
        from AnimeGANv2Model import Generator as AnimeGanV2Generator
        import torch
        import cv2
        import numpy as np
        from PIL import Image

        # Clean up CUDA resources
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        progressSignal.emit(10, "Checking CUDA capability")
        useGpu = torch.cuda.is_available()
        device = "cuda" if useGpu else "cpu"

        i = 0
        max_attempts = 2 # once on CUDA, once on CPU

        while i < max_attempts:
            try:
                progressSignal.emit(20, "Loading model")

                if QAnimeGANv2.net == None:
                    net = AnimeGanV2Generator()
                    net.load_state_dict(torch.load("models/face_paint_512_v2.pt", map_location=device))
                    net.to(device).eval()

                progressSignal.emit(30, "Loading current pixmap")

                image = args[0]

                progressSignal.emit(40, "Preprocessing image")

                b, g, r, _ = cv2.split(np.asarray(image))
                image_np = np.dstack((b, g, r))
                image_pil = Image.fromarray(image_np)

                with torch.no_grad():
                    progressSignal.emit(50, "Converting to tensor")
                    image_tensor = to_tensor(image_pil).unsqueeze(0) * 2 - 1

                    progressSignal.emit(60, "Running the model on " + device)

                    out = net(image_tensor.to(device), False # <-- upsample_align (Align corners in decoder upsampling layers)
                              ).cpu()
                    out = out.squeeze(0).clip(-1, 1) * 0.5 + 0.5

                    progressSignal.emit(70, "Postprocessing output")

                    out = to_pil_image(out)

                    # Add alpha channel back
                    alpha = np.full((out.height, out.width), 255)
                    out_np = np.dstack((np.asarray(out), alpha)).astype(np.uint8)

                    del image_tensor
                    del net
                    del out

                    i += 1

                    self.output = Image.fromarray(out_np)
                    break

            except RuntimeError as e:
                i += 1
                print(e)
                if device == "cuda":
                    # Retry on CPU
                    progressSignal.emit(10, "Failed to run on CUDA device. Retrying on CPU")
                    device = "cpu"
                    torch.cuda.empty_cache()
                    print("Retrying on CPU")
        self.stop()

    def run(self, image):
        # self.setWindowTitle("Anime GAN v2...")
        self.progressBarLabel.setText("Starting")
        self.show()

        if not self.progressBarThread.isRunning():
            self.progressBarThread.maxRange = 1000
            self.progressBarThread.progressSignal.connect(self.updateProgressBar)
            self.progressBarThread.taskFunction = self.threadFunction
            self.progressBarThread.taskFunctionArgs = [image]
            self.progressBarThread.start()

    def start(self):
        self.controlButtons.hide()
        self.progressWidgetLayout.addWidget(self.progressBarLabel)
        self.progressWidgetLayout.addWidget(self.progressBar)
        self.run(self.inputImage)

    def stop(self):
        self.progressBar.setValue(100)
        self.hide()
        self.completedSignal.emit()

    def closeEvent(self, event):
        self.stop()
        event.accept()