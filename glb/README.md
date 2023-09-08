# Reading, segmenting and writing glTF 2.0 files.

This module contains a set of functions for reading, segmenting and writing glTF 2.0 files. It is intended to be used as a library for other applications, although it can be used as a standalone tool for decompressing glTF 2.0 files as well as for segmenting them into smaller files.

The functionality is built on [gltflib](https://github.com/lukas-shawford/gltflib) as well as [trimesh](https://github.com/mikedh/trimesh). Decompression of the Draco compressed data is achieved using [DracoPy](https://github.com/seung-lab/DracoPy), a python wrapper for [Google's Draco](https://github.com/google/draco) library.

However, in general trimesh is not used as it is a higher level library and does not support the decompression of glTF 2.0 files, and the loss of translation information inside the glTF which is required to position the 3D model on the globe. Henceforth, most of the scripts uses gltflib which is a lower level library allowing direct access to the buffers and the decompression of the Draco compressed data.

## Installation

As aforementioned, the following dependencies should be installed:

-   [gltflib](https://github.com/lukas-shawford/gltflib)
-   [trimesh](https://github.com/mikedh/trimesh)
-   [DracoPy](https://github.com/seung-lab/DracoPy)
-   Pillow
-   numpy

## Usage

### `decompress.py`

The Draco compressed glb file can be decompressed using the `GLBDecompress` class in this file. Loading a compressed glb file with `GLBDecompress` will attempt to decompress the data and match it to each primitive within the glTF. Each `PrimitiveDecompress` thus contains decompressed data under the `data` attribute which is a `MeshData` object.

Instantiate a GLBDecompress with the path of the compressed glb file. This will load the glb file and set the `glb` for the `BufferAccessor` class to the loaded glb in order to access and retrieve bytes from the buffer.

The `load_meshes()` method will load each mesh within the glb and subsequently instantiates a `PrimitiveDecompress` object for each primitive within the mesh. The `PrimitiveDecompress` object will attempt to decompress the data and match it to the primitive.

The `export()` method will export the decompressed glb file to the specified path.

```python

from glb import GLBDecompress

glb = GLBDecompress(Path('path/to/file.glb'))
glb.load_meshes()
glb.export(Path('output/path/file.glb'))

```

### `extract_textures.py`

Texture images can be retrieved from the glTF file using the `glb_to_pillow()` method which returns a list of Pillow images. The functions are based off [this issue in the gltflib repository](https://github.com/lukas-shawford/gltflib/issues/175).

The raw bytes can also be retrieved instead using `get_gltf_image_data()` which requires the glTF object as well as the glTF Image object to be retrieved.

```python

from gltflib.gltf import GLTF
from glb import glb_to_pillow

gltf: GLTF = GLTF.load(file)
glb_to_pillow(gltf, save, savepath)

```

### `get_vertices.py`

This relies on trimesh and should be avoided as it does not support the decompression of glTF 2.0 files, and the loss of translation information inside the glTF which is required to position the 3D model on the globe.

Nevertheless, segmentation of glTF files can be performed via trimesh using the `MeshSegment` class, which can export the segmented meshes to the specified path.

```python

from glb import MeshSegment

meshes: list[MeshSegment] = MeshSegment.load_by_path(Path("model.gltf"))
for mesh in meshes:
    # ADD VERTICES TO CLASS HERE
    mesh.vertices_to_class = list_of_classes
    mesh.export_submeshes(Path("output"))

```

### `segment.py`

Based on the `GLBDecompress` and `PrimitiveDecompress` classes, the `GLBSegment` class can be used to segment the glTF file into smaller glTF files. Upon loading the meshes, each `PrimitiveSegment` can be assigned a list of classes for each vertex, after which running `export()` or `export_submeshes()` will export the segmented glTF files to the specified path.

Running `export()` will export the entire glTF file with the metadata for each vertex class being appended to the buffer, as well as adding accessors and buffer views for the extension `EXT_mesh_features`. Currently this requires the `Attributes` class in gltflib to be modified to include the `_FEATURE_ID_0` attribute

Running `export_submeshes()` will export each submesh as a separate file according to class. Vertices and faces of the same class are grouped together and subsequently exported as one glTF file, and is repeated for each class.

```python

from glb import GLBSegment

glb = GLBSegment(Path('path/to/file.glb'))
glb.load_meshes()
# ADD VERTICES TO CLASS HERE
for mesh in glb.meshes:
    for primitive in mesh:
        primitive.vertices_to_class = np.random.randint(
            0, 10, primitive.data.points.shape[0]
        ).tolist()

# export multiple glb files by class
glb.export_submeshes(Path('output/path/file.glb'))
# export single glb file with metadata
glb.export(Path('output/path/file.glb'))

```
