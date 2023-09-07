"""
contains the classification algorithms.

There are many ways to classify the glTF files, and the resulting output
should be an array containing the class of each vertex.
"""

from .image import ImageSegmenter

from .texture_to_vertices import (
    texture_to_vertices,
    texture_to_vertices_trimesh,
)


__all__: list[str] = [
    "ImageSegmenter",
    "texture_to_vertices",
    "texture_to_vertices_trimesh",
]
