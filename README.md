# PhotoLab

<img width="1100" src="https://user-images.githubusercontent.com/8450091/205468402-4240ad49-1449-4882-96a7-e27d9ec446b7.png">

| Anime Style | Interactive Colorization |
| ----------- | -------------------------|
| <img width="500" src="https://user-images.githubusercontent.com/8450091/205465788-86902f1a-0953-4f3b-8c7a-4d4f2dc25713.jpg"> | <img width="500" src="https://user-images.githubusercontent.com/8450091/205465819-58834a02-a437-4b47-93c8-ff3f3fc0672b.png"> |

| Portrait Mode | Grayscale Background |
|---------------| -------------------- |
| <img width="500" src="https://user-images.githubusercontent.com/8450091/205465880-b9549d26-aaf7-46dc-967f-d79148ac1f03.jpg"> | <img width="500" src="https://user-images.githubusercontent.com/8450091/205465881-fb1a61c7-734c-4c7d-b11c-edb14bf2deaa.jpg"> |

| Super-Resolution |
| ---------------- |
| <img width="1100" src="https://user-images.githubusercontent.com/8450091/205465965-6dc7cb45-d69d-4cd5-a7b0-f14f824a1227.jpg"> |

| White Balance Correction |
| -------------------------|
| <img width="1100" src="https://user-images.githubusercontent.com/8450091/205467129-64a3fad4-c4c6-4578-ba07-16e79dd94bd3.jpg"> |

| Instagram Filters | Bezier Curves and Selective Editing |
| ------------------| ------------------------------------|
| <img width="500" src="https://user-images.githubusercontent.com/8450091/205467832-fd167e86-6b26-4d61-9fc8-bfd3ae5851cf.png"> | <img width="500" src="https://user-images.githubusercontent.com/8450091/205506806-c99a64d5-c34b-470d-adbf-11de2f6790a5.png"> |

| Spot Removal | Exposure Adjustment |
| -------------| --------------------|
| <img width="500" src="https://user-images.githubusercontent.com/8450091/205468098-5fadd963-6c4e-4b1c-b430-4e989dab6fff.jpeg"> | <img width="500" src="https://user-images.githubusercontent.com/8450091/205470366-d85543ce-8d4a-4f02-926d-df1df0c4c07f.png"> |

### Quick Start

Install dependencies using pip. If you have a CUDA-enabled device, install the appropriate version of [CUDA](https://developer.nvidia.com/cuda-downloads) and [PyTorch](https://pytorch.org/).

```console
foo:bar$ pip install -r requirements.txt
```

Download the pretrained models by running the included download script:

```console
foo:bar$ python download_models.py
```

Start the editor by running:

```console
foo:bar$ python src/main.py
```

### Generate requirements.txt

```
pipreqs --force --encoding=utf-8-sig .
```

### Notes on PyTorch CUDA Support

If using a CUDA compatible device, make sure to install a version of CUDA that is compatible with the GPU that is available. Then install pytorch.

On my laptop with a mobile GTX 1070, I installed CUDA 9.2. Then, I installed PyTorch 1.13.0:

```console
foo:bar$ pip install torch==1.11.0+cu113 -f https://download.pytorch.org/whl/torch_stable.html
```

Confirm CUDA support by running:

```console
Python 3.10.8 (tags/v3.10.8:aaaf517, Oct 11 2022, 16:50:30) [MSC v.1933 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license" for more information.
>>> import torch
>>> torch.version.cuda
'11.7'
>>> torch.cuda.is_available()
True
```
