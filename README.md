![image](https://user-images.githubusercontent.com/8450091/205450952-2c23a413-cdf0-4412-9d24-6a4ef08e3d78.png)

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
