# Classifying Images

This module contains a set of functions for classifying 3D models. Ultimately the result of classification should output a list of classes for each vertex in the 3D model.

An image segmentation approach is used to classify the 3D model. The segmentation model is based on Huggingface's transformers.

## Installation

The following dependencies should be installed:

-   [PyTorch](https://pytorch.org/)
-   [Huggingface transformers](https://github.com/huggingface/transformers)
-   matplotlib
-   numpy
-   Pillow

## Usage

### `image.py`

Image segmentation can be performed using the `ImageSegmenter` class. Using Huggingface's transformers, the URL of the model can be specified and the model will be downloaded and cached. By default, the model is set to `facebook/mask2former-swin-small-cityscapes-semantic`.

Instantiate a `ImageSegmenter` object with a Pillow image. Running `predict_semantic()` will return a numpy array of the predicted classes for each pixel in the image.

There are also methods to visualise the map by overlaying a mask on the image, as well as to save the mask to a specified path.

```python

from classify import ImageSegmenter

image_segment: ImageSegmenter = ImageSegmenter(image)
seg: np.ndarray = image_segment.predict_semantic()
image_segment.save_seg(seg, "map.pt")
image_segment.visualise(seg)

```

### `texture_to_vertices.py`

With the segmentation mask, the vertices of the 3D model can be classified into a list of classes. With a trimesh object, the function `texture_to_vertices_trimesh()` can be used directly on the trimesh object. Else, the function `texture_to_vertices()` requires the array of vertices and array of texture coordinates to be passed in.

Each vertex has a texture coordinate associated with it. The texture coordinate is a 2D coordinate that maps the vertex to a pixel in the segmentation mask. (0, 0) is the top left corner of the image, and (1, 1) is the bottom right corner of the image. The texture coordinate is a float value between 0 and 1.

```python

from classify import texture_to_vertices_trimesh, texture_to_vertices

classes: list[int]  # list of classes for each vertex

classes = texture_to_vertices_trimesh(trimesh_object, seg)
classes = texture_to_vertices(vertices, texture_coordinates, seg)

```
