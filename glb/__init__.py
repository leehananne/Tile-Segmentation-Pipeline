"""
contains functions to load and modify glTF files
"""


from .extract_textures import glb_to_pillow

from .get_vertices import MeshSegment

from .decompress import (
    GLBDecompress,
    PrimitiveDecompress,
    MeshData,
    BufferAccessor,
)

from .segment import GLBSegment, PrimitiveSegment


__all__: list[str] = [
    "glb_to_pillow",
    "MeshSegment",
    "GLBSegment",
    "PrimitiveSegment",
    "GLBDecompress",
    "PrimitiveDecompress",
    "MeshData",
    "BufferAccessor",
]
