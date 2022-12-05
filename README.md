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

## Example Results

| Before | After |
|--------|-------|
| <img width="500" src="https://user-images.githubusercontent.com/8450091/205533870-db6586ce-4d9c-4a5e-9a0c-99bcf5d99a93.jpeg"> | <img width="500" src="https://user-images.githubusercontent.com/8450091/205533557-cf381bff-e2f7-453a-8da2-ecd63153824a.jpeg"> |
| <img width="500" src="https://user-images.githubusercontent.com/8450091/205533877-588ed525-b44f-4569-999d-e50c8cad8a40.jpeg"> | <img width="500" src="https://user-images.githubusercontent.com/8450091/205533660-16956642-23ef-416b-9635-7e29cbb5b4a9.jpeg"> |
| <img width="500" src="https://user-images.githubusercontent.com/8450091/205540298-c759f3c9-975d-4b86-bec5-2f15dcb8752e.jpeg"> | <img width="500" src="https://user-images.githubusercontent.com/8450091/205540306-8d488f0e-a5a1-4b47-a016-424ba9f11d22.jpeg"> |
| <img width="500" src="https://user-images.githubusercontent.com/8450091/205547688-d10ec660-9380-4cc5-a03a-4d7dd8028ed1.jpeg"> | <img width="500" src="https://user-images.githubusercontent.com/8450091/205547696-856e3b94-06d8-4136-8190-4ca709d5cd72.jpeg"> |
| <img width="500" src="https://user-images.githubusercontent.com/8450091/205549002-9ac4f0a5-1fa0-4efc-a1c1-284b22e89bd2.jpeg"> | <img width="500" src="https://user-images.githubusercontent.com/8450091/205549012-d695b367-8718-47ff-8259-6642b8d59059.jpeg"> |

## Quick Start

Download the pretrained models by running the included download script:

```console
foo:bar$ python download_models.py
```

Start the editor by running:

```console
foo:bar$ python src/main.py
```

## Notes on PyTorch CUDA Support

This project has been testing with `torch==1.11.0+cu113 torchvision-0.12.0+cu113`

```console
foo:bar$ pip install torch==1.11.0+cu113 torchvision==0.12.0+cu113 -f https://download.pytorch.org/whl/torch_stable.html

foo:bar$ python
Python 3.10.8 (tags/v3.10.8:aaaf517, Oct 11 2022, 16:50:30) [MSC v.1933 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license" for more information.
>>> import torch
>>> torch.version.cuda
'11.3'
>>> torch.cuda.is_available()
True
```
