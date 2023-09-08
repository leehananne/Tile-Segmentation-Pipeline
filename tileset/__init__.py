"""
contains tileset traverser and converter to 1.1 with groups and schema
"""


from .convert import convert_tileset

from .traverse import TilesetTraverser


__all__: list[str] = [
    "TilesetTraverser",
    "convert_tileset",
]
