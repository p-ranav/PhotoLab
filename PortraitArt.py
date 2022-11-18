from PIL import Image
import torch

# https://github.com/bryandlee/animegan2-pytorch
# load models
# model_celeba = torch.hub.load("bryandlee/animegan2-pytorch:main", "generator", pretrained="celeba_distill")
model_facev1 = torch.hub.load("bryandlee/animegan2-pytorch:main", "generator", pretrained="face_paint_512_v1")
model_facev2 = torch.hub.load("bryandlee/animegan2-pytorch:main", "generator", pretrained="face_paint_512_v2")
# model_paprika = torch.hub.load("bryandlee/animegan2-pytorch:main", "generator", pretrained="paprika")

face2paint = torch.hub.load("bryandlee/animegan2-pytorch:main", "face2paint", size=512)

INPUT_IMG = "test/test.jpg" # input_image jpg/png 
img = Image.open(INPUT_IMG).convert("RGB")

# out_celeba = face2paint(model_celeba, img)
out_facev1 = face2paint(model_facev1, img)
out_facev2 = face2paint(model_facev2, img)
# out_paprika = face2paint(model_paprika, img)

# save images
# out_celeba.save("out_celeba.jpg")
out_facev1.save("out_facev1.jpg")
out_facev2.save("out_facev2.jpg")
# out_paprika.save("out_paprika.jpg")