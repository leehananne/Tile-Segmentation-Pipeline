# Tileset Traverser and Converter

This module enables the traversal of a tileset and the conversion of the tileset into a 3D model.

The [`py3dtiles`](../py3dtiles/) module is a modified version of the [py3dtiles](https://gitlab.com/Oslandia/py3dtiles) module. To partially support 3D Tiles version 1.1, additional classes were made in accordance to the [glTF specification and schema](https://github.com/CesiumGS/3d-tiles/tree/main/specification/schema).

The primary enhancements in the 3D Tiles version 1.1 include:

-   Semantic metadata at multiple granularities;
-   Implicit tiling for improved analytics and random access to tiles;
-   Multiple contents per tile to support layering and content groupings; and
-   Direct references to glTF content for better integration with the glTF ecosystem.

## Installation

No additional dependencies are required, other than the modified py3dtiles module which is already in this repository.

## Usage

### `convert.py`

To support the adding of multiple contents per tile, the tileset has to be converted to version 1.1 and metadata has to be added. The `convert_tileset()` function performs the conversion and adds the groups and schema required. Labels corresponding to the classes can be added to the tileset by passing in a list of labels.

```python

from py3dtiles.tileset import TileSet
from tileset import convert_tileset

tileset: TileSet
labels: dict[int, str]  # dictionary of labels for each class
tileset.convert_tileset(tileset, labels)

```

### `traverse.py`

As 3D tiles content URIs may be relative to the tileset JSON file, the `TilesetTraverser` class allows the traversal of the tileset and tracks the
root URI of the tileset to resolve relative paths.

The `TilesetTraverser` class contains class attributes `INPUT_DIR` and `OUTPUT_DIR` which are the input and output directories respectively, which helps to resolve the relative paths, and to allow exporting of the tileset to a different directory.

Upon retrieving the tileset root tile with `get_tileset_tile()`, the root URI is updated to that of the tileset. Retrieving the tile content via `get_tile_content()` will then obtain the URI of the content and attempt to resolve the relative path with the root URI.

```python

from py3dtiles.tileset import TileSet
from tileset import TilesetTraverser

tileset: TileSet
root_tile = TilesetTraverser.get_tileset_tile(tileset)
content = TilesetTraverser.get_tile_content(root_tile)

```