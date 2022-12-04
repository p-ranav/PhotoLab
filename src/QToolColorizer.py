#def get_args():
#    parser = argparse.ArgumentParser('Colorization UI', add_help=False)
#    # Directories
#    parser.add_argument('--model_path', type=str, default='path/to/checkpoints', help='checkpoint path of model')
#    parser.add_argument('--target_image', default='path/to/image', type=str, help='validation dataset path')
#    parser.add_argument('--device', default='cpu', help='device to use for testing')

#    # Dataset parameters
#    parser.add_argument('--input_size', default=224, type=int, help='images input size for backbone')

#    # Model parameters
#    parser.add_argument('--model', default='icolorit_base_4ch_patch16_224', type=str, help='Name of model to vis')
#    parser.add_argument('--drop_path', type=float, default=0.0, help='Drop path rate (default: 0.1)')
#    parser.add_argument('--use_rpb', action='store_true', help='relative positional bias')
#    parser.add_argument('--no_use_rpb', action='store_false', dest='use_rpb')
#    parser.set_defaults(use_rpb=True)
#    parser.add_argument('--avg_hint', action='store_true', help='avg hint')
#    parser.add_argument('--no_avg_hint', action='store_false', dest='avg_hint')
#    parser.set_defaults(avg_hint=True)
#    parser.add_argument('--head_mode', type=str, default='cnn', help='head_mode')
#    parser.add_argument('--mask_cent', action='store_true', help='mask_cent')

#    args = parser.parse_args()

#    return args


from QTool import QTool
import os

class QToolColorizer(QTool):
    def __init__(self, parent=None, toolInput=None, onCompleted=None):
        super(QToolColorizer, self).__init__(parent, "Interactive Colorization", 
                                             "Colorize image interactively by leveraging a vision transformer",
                                             "images/Colorizer_08_Interactive.png", 
                                             self.onRun, toolInput, onCompleted, self)
        self.parent = parent
        self.output = None

    def onRun(self, progressSignal):
        import ColorizerMain
        import ColorizerModeling
        from timm.models import create_model
        import torch
        import os
        from FileUtils import merge_files

        # Merge NN model files into pth file if not exists
        if not os.path.exists("models/icolorit_base_4ch_patch16_224.pth"):
            merge_files("icolorit_base_4ch_patch16_224.pth", "models")

        def get_model():
            model = create_model(
                "icolorit_base_4ch_patch16_224",
                pretrained=False,
                drop_path_rate=0.0,
                drop_block_rate=None,
                use_rpb=True,
                avg_hint=True,
                head_mode="cnn",
                mask_cent=False,
            )

            return model

        device = "cuda" if torch.cuda.is_available() else "cpu"

        model = get_model()
        model.to(device)
        checkpoint = torch.load(os.path.join("models", "icolorit_base_4ch_patch16_224.pth"), map_location=torch.device(device))
        model.load_state_dict(checkpoint['model'], strict=False)
        model.eval()
        self.output = model