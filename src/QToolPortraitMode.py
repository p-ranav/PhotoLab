from QTool import QTool
import os

class QToolPortraitMode(QTool):
    def __init__(self, parent=None, toolInput=None, onCompleted=None):
        super(QToolPortraitMode, self).__init__(parent, "Portrait Mode", 
                                             "Narrow the depth of field to draw attention to a subject in the photo", 
                                             "images/PortraitMode.jpg", 
                                             self.onRun, toolInput, onCompleted, self)

        self.parent = parent
        self.output = None
        self.backgroundRemoved = None

    def onRun(self, progressSignal, args):
        image = args[0].copy()

        from BackgroundRemoval import remove2
        from FileUtils import merge_files

        # Merge NN model files into pth file if not exists
        if not os.path.exists("models/u2net.pth"):
            merge_files("u2net.pth", "models")

        progressSignal.emit(10, "Loading current pixmap")
        self.backgroundRemoved = remove2(image, progressSignal, model_name="u2net")


        # Run MiDaS depth predictor

        # Merge NN model files into pth file if not exists
        progressSignal.emit(70, "Loading depth predictor")
        if not os.path.exists("models/dpt_large-midas-2f21e586.pt"):
            merge_files("dpt_large-midas-2f21e586.pt", "models")

        import torch
        from torchvision.transforms import Compose
        import numpy as np
        import MiDaS
        import cv2
        from PIL import Image, ImageFilter

        ### Save new pixmap
        ##updatedPixmap = self.ImageToQPixmap(output)

        ## Get current pixmap and apply gaussian blur
        #currentPixmap = self.getCurrentLayerLatestPixmap().copy()
        ## currentPixmap = self.ApplyGaussianBlur(currentPixmap, 5)
        #pil = self.QPixmapToImage(currentPixmap)
        pil = image
        originalPil = pil.copy()
        img = np.asarray(pil)
        b, g, r, a = cv2.split(img)
        img = np.dstack((r, g, b)) / 255.0

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_path = "models/dpt_large-midas-2f21e586.pt"

        ## DPT Hybrid
        #model = MiDaS.DPTDepthModel(
        #    path=model_path,
        #    backbone="vitb_rn50_384",
        #    non_negative=True,
        #)
        #net_w, net_h = 384, 384
        #resize_mode="minimal"
        #normalization = MiDaS.NormalizeImage(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])

        progressSignal.emit(80, "Using depth predictor model " + model_path + " on " + "cuda" if torch.cuda.is_available() else "cpu")

        # DPT Large
        model = MiDaS.DPTDepthModel(
            path=model_path,
            backbone="vitl16_384",
            non_negative=True,
        )
        net_w, net_h = 384, 384
        resize_mode = "minimal"
        normalization = MiDaS.NormalizeImage(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])

        transform = Compose(
            [
                MiDaS.Resize(
                    net_w,
                    net_h,
                    resize_target=None,
                    keep_aspect_ratio=True,
                    ensure_multiple_of=32,
                    resize_method=resize_mode,
                    image_interpolation_method=cv2.INTER_CUBIC,
                ),
                normalization,
                MiDaS.PrepareForNet(),
            ]
        )

        model.eval()
        model.to(device)

        # Prepare input
        img_input = transform({"image": img})["image"]

        # compute
        with torch.no_grad():
            sample = torch.from_numpy(img_input).to(device).unsqueeze(0)

            progressSignal.emit(90, "Predicting depth")

            prediction = model.forward(sample)
            prediction = (
                torch.nn.functional.interpolate(
                    prediction.unsqueeze(1),
                    size=img.shape[:2],
                    mode="bicubic",
                    align_corners=False,
                )
                .squeeze()
                .cpu()
                .numpy()
            )

            img = (prediction / 100).astype(np.uint8)
            pil = Image.fromarray(img).convert('L')

            sharpen = 3
            boxBlur = 5
            bimg = originalPil.filter(ImageFilter.BoxBlur(int(boxBlur)))
            bimg = bimg.filter(ImageFilter.BLUR)

            for _ in range(sharpen):
                bimg = bimg.filter(ImageFilter.SHARPEN)

            self.output = Image.composite(originalPil, bimg, pil)

            # Resize to original pixmap size
            self.output = self.output.resize((args[0].width, args[0].height))

            progressSignal.emit(95, "Postprocessing")