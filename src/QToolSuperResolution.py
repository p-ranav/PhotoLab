from QTool import QTool

class QToolSuperResolution(QTool):
    def __init__(self, parent=None, toolInput=None, onCompleted=None):
        super(QToolSuperResolution, self).__init__(parent, "Super-Resolution", 
                                             "Reconstruct detailed high-res counterpart from a low-res image\nhttps://github.com/cszn/BSRGAN", 
                                             "images/SuperResolution.jpg", 
                                             self.onRun, toolInput, onCompleted, self)

        self.parent = parent
        self.output = None

    def onRun(self, progressSignal, args):
        image = args[0]

        import torch
        import QualityScaler
        import ColorizerUtil
        import cv2
        import numpy as np

        progressSignal.emit(10, "Loading current pixmap")

        image = ColorizerUtil.load_img(image)
        b, g, r, _ = cv2.split(image)
        image_np = np.dstack((b, g, r))

        progressSignal.emit(20, "Checking CUDA availability")
            
        useGpu = torch.cuda.is_available()
        device = "cuda" if useGpu else "cpu"

        i = 0
        max_attempts = 2 # once on CUDA, once on CPU

        while i < max_attempts:
            try:

                progressSignal.emit(30, "Setting up torch autograd")

                QualityScaler.optimize_torch()

                model = "BSRGANx4"
                progressSignal.emit(40, "Loading model " + model + " on " + device)

                model = QualityScaler.prepare_AI_model(model, device)
                tiles_resolution = 700 # If the image is smaller than this on both sides, it'll be upscaled without any tiling

                progressSignal.emit(50, "Setting tile resolution " + str(tiles_resolution))

                upscaled = QualityScaler.upscale_image(image_np, model, device, tiles_resolution, progressSignal)

                alpha = np.full((upscaled.height, upscaled.width), 255)
                upscaled_np = np.asarray(upscaled)
                upscaled_rgba = np.dstack((upscaled_np, alpha)).astype(np.uint8)

                i += 1

                self.output = upscaled_rgba
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