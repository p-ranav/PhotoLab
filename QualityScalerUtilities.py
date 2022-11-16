#!usr/bin/env python
from PIL import Image

def split_image(im, rows, cols):
    image = Image.fromarray(im)
    im_width, im_height = image.size
    row_width = int(im_width / rows)
    row_height = int(im_height / cols)

    result = [] # list of tiles; smaller images

    n = 0
    for i in range(0, cols):
        for j in range(0, rows):
            box = (j * row_width, i * row_height, j * row_width +
                   row_width, i * row_height + row_height)
            outp = image.crop(box)
            result.append(outp)
            n += 1

    return result

def reverse_split(images_to_merge, rows, cols):
    image1 = images_to_merge[0]
    new_width = image1.size[0] * cols
    new_height = image1.size[1] * rows

    new_image = Image.new(image1.mode, (new_width, new_height))

    for i in range(0, rows):
        for j in range(0, cols):
            image = images_to_merge[i * cols + j]
            new_image.paste(image, (j * image.size[0], i * image.size[1]))

    return new_image