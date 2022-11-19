from QTool import QTool

class QToolColorizer(QTool):
    def __init__(self, parent=None, toolInput=None, onCompleted=None):
        super(QToolColorizer, self).__init__(parent, "Image Colorization", 
                                             "Colorize black and white images with learned deep priors\nhttps://github.com/richzhang/colorization", 
                                             "images/Colorizer_03.jpg", self.onRun, toolInput, onCompleted)

        self.parent = parent
        self.output = None

    def onRun(self, progressSignal, args):
        image = args[0]

        import ColorizerUtil
        import ColorizerSiggraph17Model
        import torch
        import cv2
        import numpy as np
        from PIL import Image

        progressSignal.emit(10, "Checking CUDA capability")
        useGpu = torch.cuda.is_available()
        device = "cuda" if useGpu else "cpu"

        i = 0
        max_attempts = 2 # once on CUDA, once on CPU

        while i < max_attempts:
            try:
                progressSignal.emit(20, "Loading colorizer model")

                # Load colorizer
                colorizer_siggraph17 = ColorizerSiggraph17Model.siggraph17(pretrained=True).eval()
                if(useGpu):
                    colorizer_siggraph17.cuda()

                progressSignal.emit(30, "Loading current pixmap")

                # Preprocess
                image = ColorizerUtil.load_img(image)
                b, g, r, a = cv2.split(image)

                progressSignal.emit(40, "Preprocessing image")

                (tens_l_orig, tens_l_rs) = ColorizerUtil.preprocess_img(np.dstack((b, g, r)), HW=(256,256))
                if(useGpu):
                    tens_l_rs = tens_l_rs.cuda()

                progressSignal.emit(50, "Running colorizer on " + "cuda" if useGpu else "cpu")

                # colorizer outputs 256x256 ab map
                # resize and concatenate to original L channel
                img_bw = ColorizerUtil.postprocess_tens(tens_l_orig, torch.cat((0*tens_l_orig,0*tens_l_orig),dim=1))
                output = ColorizerUtil.postprocess_tens(tens_l_orig, colorizer_siggraph17(tens_l_rs).cpu())

                del image
                del tens_l_rs
                del tens_l_orig
                del img_bw

                progressSignal.emit(80, "Postprocessing output")

                # Fix RGB channels and recover the alpha channel that was lost earlier
                self.output = np.dstack((output * 255, a)).astype(np.uint8)

                progressSignal.emit(90, "Done")

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