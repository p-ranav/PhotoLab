![image](https://user-images.githubusercontent.com/8450091/205416740-8a602d77-cee5-4c51-b9aa-597b97ad999d.png)

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
