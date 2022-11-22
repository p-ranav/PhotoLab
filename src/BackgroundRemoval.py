import io
import os
import typing
from PIL import Image
from pymatting.alpha.estimate_alpha_cf import estimate_alpha_cf
from pymatting.foreground.estimate_foreground_ml import estimate_foreground_ml
from pymatting.util.util import stack_images
from scipy.ndimage.morphology import binary_erosion
import moviepy.editor as mpy
import numpy as np
import torch
import torch.nn.functional
import torch.nn.functional
import BackgroundRemovalDetect, BackgroundRemovalU2net

DEVICE = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

U2NET_MODEL_LOCATION="models"

class Net(torch.nn.Module):
    def __init__(self, model_name):
        super(Net, self).__init__()
        net = BackgroundRemovalU2net.U2NET(3, 1)
        path = os.path.join(U2NET_MODEL_LOCATION, model_name)
        net.load_state_dict(torch.load(path, map_location=torch.device(DEVICE)))
        net.to(device=DEVICE, dtype=torch.float32, non_blocking=True)
        net.eval()
        self.net = net

    def forward(self, block_input: torch.Tensor):
        image_data = block_input.permute(0, 3, 1, 2)
        original_shape = image_data.shape[2:]
        image_data = torch.nn.functional.interpolate(image_data, (320, 320), mode='bilinear')
        image_data = (image_data / 255 - 0.485) / 0.229
        out = self.net(image_data)[0][:, 0:1]
        ma = torch.max(out)
        mi = torch.min(out)
        out = (out - mi) / (ma - mi) * 255
        out = torch.nn.functional.interpolate(out, original_shape, mode='bilinear')
        out = out[:, 0]
        out = out.to(dtype=torch.uint8, device=torch.device('cpu'), non_blocking=True).detach()
        return out


def alpha_matting_cutout(
    img,
    mask,
    foreground_threshold,
    background_threshold,
    erode_structure_size,
    base_size,
):
    size = img.size

    img.thumbnail((base_size, base_size), Image.LANCZOS)
    mask = mask.resize(img.size, Image.LANCZOS)

    img = np.asarray(img)
    mask = np.asarray(mask)

    # guess likely foreground/background
    is_foreground = mask > foreground_threshold
    is_background = mask < background_threshold

    # erode foreground/background
    structure = None
    if erode_structure_size > 0:
        structure = np.ones((erode_structure_size, erode_structure_size), dtype=np.int)

    is_foreground = binary_erosion(is_foreground, structure=structure)
    is_background = binary_erosion(is_background, structure=structure, border_value=1)

    # build trimap
    # 0   = background
    # 128 = unknown
    # 255 = foreground
    trimap = np.full(mask.shape, dtype=np.uint8, fill_value=128)
    trimap[is_foreground] = 255
    trimap[is_background] = 0

    # build the cutout image
    img_normalized = img / 255.0
    trimap_normalized = trimap / 255.0

    img_normalized = img_normalized[:,:,:3] # remove alpha channel

    alpha = estimate_alpha_cf(img_normalized, trimap_normalized)
    foreground = estimate_foreground_ml(img_normalized, alpha)
    cutout = stack_images(foreground, alpha)

    cutout = np.clip(cutout * 255, 0, 255).astype(np.uint8)
    cutout = Image.fromarray(cutout)
    cutout = cutout.resize(size, Image.LANCZOS)

    return cutout


def naive_cutout(img, mask):
    empty = Image.new("RGBA", (img.size), 0)
    cutout = Image.composite(img, empty, mask.resize(img.size, Image.LANCZOS))
    return cutout


def get_model(model_name):
    if model_name == "u2netp":
        return BackgroundRemovalDetect.load_model(model_name="u2netp")
    if model_name == "u2net_human_seg":
        return BackgroundRemovalDetect.load_model(model_name="u2net_human_seg")
    else:
        return BackgroundRemovalDetect.load_model(model_name="u2net")


def remove(
    data,
    model_name="u2net_human_seg",
    alpha_matting=False,
    alpha_matting_foreground_threshold=240,
    alpha_matting_background_threshold=10,
    alpha_matting_erode_structure_size=10,
    alpha_matting_base_size=500,
):
    model = get_model(model_name)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    mask = BackgroundRemovalDetect.predict(model, np.array(img)).convert("L")

    if alpha_matting:
        cutout = alpha_matting_cutout(
            img,
            mask,
            alpha_matting_foreground_threshold,
            alpha_matting_background_threshold,
            alpha_matting_erode_structure_size,
            alpha_matting_base_size,
        )
    else:
        cutout = naive_cutout(img, mask)

    bio = io.BytesIO()
    cutout.save(bio, "PNG")

    return bio.getbuffer()

def remove2(
    img,
    progressSignal,
    model_name="u2net",
    alpha_matting=True,
    alpha_matting_foreground_threshold=200,
    alpha_matting_background_threshold=10,
    alpha_matting_erode_structure_size=10,
    alpha_matting_base_size=1000,
):
    progressSignal.emit(20, "Loading model " + model_name)
    model = get_model(model_name)

    progressSignal.emit(30, "Performing prediction with " + model_name)
    mask = BackgroundRemovalDetect.predict(model, np.array(img)).convert("L")

    progressSignal.emit(40, "Generated mask")

    if alpha_matting:
        cutout = alpha_matting_cutout(
            img,
            mask,
            alpha_matting_foreground_threshold,
            alpha_matting_background_threshold,
            alpha_matting_erode_structure_size,
            alpha_matting_base_size,
        )
    else:
        cutout = naive_cutout(img, mask)

    progressSignal.emit(50, "Removing background")

    bio = io.BytesIO()
    cutout.save(bio, "PNG")

    progressSignal.emit(60, "Saving output")

    return Image.open(bio)


def iter_frames(path):
    return mpy.VideoFileClip(path).resize(height=320).iter_frames(dtype="uint8")


@torch.no_grad()
def remove_many(image_data: typing.List[np.array], net: Net):
    image_data = np.stack(image_data)
    image_data = torch.as_tensor(image_data, dtype=torch.float32, device=DEVICE)
    return net(image_data).numpy()
