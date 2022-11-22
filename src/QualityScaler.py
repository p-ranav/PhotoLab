import ctypes
import functools
import multiprocessing
import os
import os.path
import platform
import shutil
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkFont
import webbrowser
from timeit import default_timer as timer
from tkinter import PhotoImage, ttk

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.init as init
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.audio.io import AudioFileClip
from moviepy.video.io import ImageSequenceClip, VideoFileClip
from PIL import Image, ImageDraw, ImageFont
from QualityScalerUtilities import reverse_split, split_image

def create_temp_dir(name_dir):
    if os.path.exists(name_dir):
        shutil.rmtree(name_dir)

    if not os.path.exists(name_dir):
        os.makedirs(name_dir)

def find_by_relative_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(
        os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def image_to_uint(img, n_channels=3):
    #if n_channels == 1:
    #    img = cv2.imread(path, 0)  # cv2.IMREAD_GRAYSCALE
    #    img = np.expand_dims(img, axis=2)  # HxWx1
    #elif n_channels == 3:
    #    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)  # BGR or G
    #    if img.ndim == 2:
    #        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)  # GGG
    #    else:
    #        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # RGB
    return img

def save_image(img, img_path):
    img = np.squeeze(img)
    if img.ndim == 3:
        img = img[:, :, [2, 1, 0]]
    cv2.imwrite(img_path, img)

def uint_to_tensor4(img):
    if img.ndim == 2:
        img = np.expand_dims(img, axis=2)

    #return F.interpolate(torch.from_numpy(np.ascontiguousarray(img)).permute(2, 0, 1).float().div(255.).unsqueeze(0), 256)

    return torch.from_numpy(np.ascontiguousarray(img)).permute(2, 0, 1).float().div(255.).unsqueeze(0)

def tensor_to_uint(img):
    img = img.data.squeeze().float().clamp_(0, 1).cpu().numpy()
    if img.ndim == 3:
        img = np.transpose(img, (1, 2, 0))
    return np.uint8((img*255.0).round())

def delete_tiles(tiles):
    for tile in tiles:
        os.remove(tile.filename)

def prepare_output_filename(img, AI_model, target_file_extension):
    result_path = (img.replace("_resized" + target_file_extension, "").replace(target_file_extension, "") 
                    + "_"  + AI_model  
                    + target_file_extension)
    return result_path

def delete_list_of_files(list_to_delete):
    if len(list_to_delete) > 0:
        for to_delete in list_to_delete:
            if os.path.exists(to_delete):
                os.remove(to_delete)

def adapt_image_for_deeplearning(img, device):
    if 'cpu' in device:
        backend = torch.device('cpu')
    elif 'dml' in device:
        backend = torch.device('dml')
    elif 'cuda' in device:
        backend = torch.device('cuda')

    img = image_to_uint(img, n_channels=3)
    img = uint_to_tensor4(img)
    img = img.to(backend, non_blocking = True)
    return img


## IMAGE

#def resize_image(image_path, resize_factor):
#    new_image_path = image_path.replace(target_file_extension, 
#                                        "_resized" + target_file_extension)

#    old_image = Image.open(image_path)

#    new_width, new_height = old_image.size
#    new_width = int(new_width * resize_factor)
#    new_height = int(new_height * resize_factor)

#    resized_image = old_image.resize((new_width, new_height), 
#                                        resample = Image.LINEAR)
                                    
#    resized_image.save(new_image_path)

#def resize_image_list(image_list, resize_factor):
#    files_to_delete   = []
#    downscaled_images = []
#    how_much_images = len(image_list)

#    index = 1
#    for image in image_list:
#        resized_image_path = image.replace(target_file_extension, 
#                                            "_resized" + target_file_extension)
        
#        resize_image(image, resize_factor)
#        # write_in_log_file("Resizing image " + str(index) + "/" + str(how_much_images)) 

#        downscaled_images.append(resized_image_path)
#        files_to_delete.append(resized_image_path)

#        index += 1

#    return downscaled_images, files_to_delete

# ----------------------- /Utils ------------------------


# ------------------ Neural Net related ------------------


def initialize_weights(net_l, scale=1):
    if not isinstance(net_l, list):
        net_l = [net_l]
    for net in net_l:
        for m in net.modules():
            if isinstance(m, nn.Conv2d):
                init.kaiming_normal_(m.weight, a=0, mode='fan_in')
                m.weight.data *= scale  # for residual block
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                init.kaiming_normal_(m.weight, a=0, mode='fan_in')
                m.weight.data *= scale
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm2d):
                init.constant_(m.weight, 1)
                init.constant_(m.bias.data, 0.0)

def make_layer(block, n_layers):
    layers = []
    for _ in range(n_layers):
        layers.append(block())
    return nn.Sequential(*layers)

class ResidualDenseBlock_5C(nn.Module):
    def __init__(self, nf=64, gc=32, bias=True):
        super(ResidualDenseBlock_5C, self).__init__()
        # gc: growth channel, i.e. intermediate channels
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1, bias=bias)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1, bias=bias)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1, bias=bias)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1, bias=bias)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1, bias=bias)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

        # initialization
        initialize_weights(
            [self.conv1, self.conv2, self.conv3, self.conv4, self.conv5], 0.1)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x

class RRDB(nn.Module):
    '''Residual in Residual Dense Block'''

    def __init__(self, nf, gc=32):
        super(RRDB, self).__init__()
        self.RDB1 = ResidualDenseBlock_5C(nf, gc)
        self.RDB2 = ResidualDenseBlock_5C(nf, gc)
        self.RDB3 = ResidualDenseBlock_5C(nf, gc)

    def forward(self, x):
        out = self.RDB1(x)
        out = self.RDB2(out)
        out = self.RDB3(out)
        return out * 0.2 + x

class RRDBNet(nn.Module):
    def __init__(self, in_nc=3, out_nc=3, nf=64, nb=23, gc=32, sf=4):
        super(RRDBNet, self).__init__()
        RRDB_block_f = functools.partial(RRDB, nf=nf, gc=gc)
        self.sf = sf

        self.conv_first = nn.Conv2d(in_nc, nf, 3, 1, 1, bias=True)
        self.RRDB_trunk = make_layer(RRDB_block_f, nb)
        self.trunk_conv = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)
        # upsampling
        self.upconv1 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)
        if self.sf == 4:
            self.upconv2 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)
        self.HRconv = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)
        self.conv_last = nn.Conv2d(nf, out_nc, 3, 1, 1, bias=True)

        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        fea = self.conv_first(x)
        trunk = self.trunk_conv(self.RRDB_trunk(fea))
        fea = fea + trunk

        fea = self.lrelu(self.upconv1(F.interpolate(
            fea, scale_factor=2, mode='nearest')))
        if self.sf == 4:
            fea = self.lrelu(self.upconv2(F.interpolate(
                fea, scale_factor=2, mode='nearest')))
        out = self.conv_last(self.lrelu(self.HRconv(fea)))

        return out


# ------------------ /Neural Net related ------------------

# ----------------------- Core ------------------------

def check_compatibility(supported_file_dropped_number, not_supported_file_dropped_number, supported_video_dropped_number):
    all_supported  = True
    single_file    = False
    multiple_files = False
    video_files    = False
    more_than_one_video = False

    if not_supported_file_dropped_number > 0:
        all_supported = False

    if supported_file_dropped_number + not_supported_file_dropped_number == 1:
        single_file = True
    elif supported_file_dropped_number + not_supported_file_dropped_number > 1:
        multiple_files = True

    if supported_video_dropped_number == 1:
        video_files = True
        more_than_one_video = False
    elif supported_video_dropped_number > 1:
        video_files = True
        more_than_one_video = True

    return all_supported, single_file, multiple_files, video_files, more_than_one_video

def upscale_image_and_save(img, model, result_path, device, tiles_resolution):
    multiplier_num_tiles = 3

    img_tmp          = cv2.imread(img)
    image_resolution = max(img_tmp.shape[1], img_tmp.shape[0])
    num_tiles        = image_resolution/tiles_resolution

    if num_tiles <= 1:
        num_tiles = 2
    #if num_tiles <= 1:
    #    img_adapted  = adapt_image_for_deeplearning(img, device)
    #    with torch.no_grad():
    #        img_upscaled_tensor = model(img_adapted)
    #        img_upscaled = tensor_to_uint(img_upscaled_tensor)
    #    save_image(img_upscaled, result_path)

    num_tiles = round(num_tiles)
    if (num_tiles % 2) != 0: num_tiles += 1
    num_tiles = round(num_tiles * multiplier_num_tiles)

    num_tiles_applied = int(num_tiles/2)
    how_many_tiles = int(pow(num_tiles/2, 2))

    split_image(img, num_tiles_applied, num_tiles_applied)

    print("Num tiles:", how_many_tiles)
    print(img)

    basename, ext = os.path.splitext(img)

    tiles = []
    for index in range(how_many_tiles):
        tiles.append(basename + "_" + str(index) + ext)

    with torch.no_grad():
        for tile in tiles:
            tile_adapted  = adapt_image_for_deeplearning(tile, device)
            tile_upscaled = tensor_to_uint(model(tile_adapted))
            save_image(tile_upscaled, tile)
            print("Upscaled", tile)

    reverse_split(tiles, num_tiles_applied, num_tiles_applied, result_path, True, False)
    print("Done upscale_image_and_save")

def upscale_image(img, model, device, tiles_resolution, progressSignal):
    multiplier_num_tiles = 3

    img_tmp          = np.asarray(img)
    image_resolution = max(img_tmp.shape[1], img_tmp.shape[0])
    num_tiles        = image_resolution/tiles_resolution

    if num_tiles <= 1:
        progressSignal.emit(55, "Adapting image for deep learning")
        img_adapted  = adapt_image_for_deeplearning(img, device)
        with torch.no_grad():
            progressSignal.emit(60, "Scaling the quality...")
            img_upscaled_tensor = model(img_adapted)
            del img_adapted
            progressSignal.emit(90, "Upscaling completed")
            img_upscaled = tensor_to_uint(img_upscaled_tensor)
            del img_upscaled_tensor
            progressSignal.emit(95, "Postprocessing image...")
        return Image.fromarray(img_upscaled)
    else:
        num_tiles = round(num_tiles)
        if (num_tiles % 2) != 0: num_tiles += 1
        num_tiles = round(num_tiles * multiplier_num_tiles)

        num_tiles_applied = int(num_tiles/2)
        how_many_tiles = int(pow(num_tiles/2, 2))

        progressSignal.emit(55, "Splitting image into " + str(how_many_tiles) + " tiles")

        # Build a list of tiles from image
        tiles = split_image(img, num_tiles_applied, num_tiles_applied)

        # Convert to np arrays
        tiles = [np.asarray(im) for im in tiles]

        upscaled_tiles = []

        currentProgress = 60
        progressPerTile = float(40) / len(tiles)
        i = 0

        with torch.no_grad():
            for tile in tiles:
                progressSignal.emit(currentProgress, "Upscaling tile {}/{}".format(i + 1, len(tiles)))
                tile_adapted  = adapt_image_for_deeplearning(tile, device)
                tile_upscaled = tensor_to_uint(model(tile_adapted))
                del tile
                del tile_adapted
                # Clean up CUDA resources
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                upscaled_tiles.append(tile_upscaled)

                i += 1
                currentProgress = int(currentProgress + progressPerTile)

        del tiles

        upscaled_tiles = [Image.fromarray(arr) for arr in upscaled_tiles]

        return reverse_split(upscaled_tiles, num_tiles_applied, num_tiles_applied)

def optimize_torch():
    torch.autograd.set_detect_anomaly(False)
    torch.autograd.profiler.profile(False)
    torch.autograd.profiler.emit_nvtx(False)

def prepare_AI_model(AI_model, device):
    if 'cpu' in device:
        backend = torch.device('cpu')
    elif 'cuda' in device:
        backend = torch.device('cuda')
    elif 'dml' in device:
        backend = torch.device('dml')

    model_path = os.path.join('models', AI_model + '.pth')

    if "x2" in AI_model: upscale_factor = 2
    elif "x4" in AI_model: upscale_factor = 4

    model = RRDBNet(in_nc = 3, out_nc = 3, nf = 64, 
                    nb = 23, gc = 32, sf = upscale_factor)
    model.load_state_dict(torch.load(model_path), strict=True)
    model.eval()

    for _, v in model.named_parameters():
        v.requires_grad = False
        
    model = model.to(backend, non_blocking = True)

    return model

supported_file_list     = ['.jpg', '.jpeg', '.JPG', '.JPEG',
                            '.png', '.PNG',
                            '.webp', '.WEBP',
                            '.bmp', '.BMP',
                            '.tif', '.tiff', '.TIF', '.TIFF',
                            '.mp4', '.MP4',
                            '.webm', '.WEBM',
                            '.mkv', '.MKV',
                            '.flv', '.FLV',
                            '.gif', '.GIF',
                            '.m4v', ',M4V',
                            '.avi', '.AVI',
                            '.mov', '.MOV',
                            '.qt', '.3gp', '.mpg', '.mpeg']

def convert_image_list(image_list, target_file_extension):
    converted_images = []
    for image in image_list:
        image = image.strip()
        converted_img = convert_image_and_save(image, target_file_extension)
        converted_images.append(converted_img)

    return converted_images

def convert_image_and_save(image_to_prepare, target_file_extension):
    image_to_prepare = image_to_prepare.replace("{", "").replace("}", "")
    new_image_path = image_to_prepare

    for file_type in supported_file_list:
        new_image_path = new_image_path.replace(file_type, target_file_extension)

    cv2.imwrite(new_image_path, cv2.imread(image_to_prepare))
    return 

def process_upscale_multiple_images_qualityscaler(image_list, AI_model, resize_factor, device, tiles_resolution, target_file_extension):
    try:
        # start = timer()
        
        # write_in_log_file('...')

        optimize_torch()

        # write_in_log_file('Resizing images')
        # image_list = convert_image_list(image_list, target_file_extension)
        # image_list, files_to_delete = resize_image_list(image_list, resize_factor)

        done_images     = 0

        # write_in_log_file('Upscaling...')
        for img in image_list:
            print("Preparing AI model")
            model = prepare_AI_model(AI_model, device)
            name, ext = os.path.splitext(img)

            result_path = name + "_upscaled" + ext 
            print("Upscaling and writing to", result_path)
            upscale_image_and_save(img, model, 
                                    result_path, device,    
                                    tiles_resolution)
            print("Done")
            break

            done_images += 1
            # write_in_log_file("Upscaled images " + str(done_images) + "/" + str(how_many_images))
                
        # write_in_log_file("Upscale completed [" + str(round(timer() - start)) + " sec.]")

        # delete_list_of_files(files_to_delete)
    except Exception as e:
        print(str(e))
        # write_in_log_file('Error while upscaling' + '\n\n' + str(e))