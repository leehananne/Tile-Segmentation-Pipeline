"""traverse a 3d tileset JSON file"""
import logging
from pathlib import Path
from typing import Optional
from py3dtiles.tileset import TileSet, Tile


class TilesetTraverser:
    """traverse a 3D tileset JSON file

    as 3D tiles uri may be relative to the tileset JSON file,
    this class allows to traverse the tileset and tracks the
    root uri of the tileset to resolve relative paths

    attributes
    ----------
    INPUT_DIR: pathlib.Path
        input directory of the tileset
    OUTPUT_DIR: pathlib.Path
        output directory of the tileset
    root_uri: pathlib.Path
        root uri of the tileset to resolve relative paths

    """

    INPUT_DIR: Path = Path(".")
    """input directory of the tileset"""

    OUTPUT_DIR: Path = Path(".")
    """output directory of the tileset"""

    root_uri: Path = Path(".")
    """root uri of the tileset to resolve relative paths"""

    @classmethod
    def get_tileset_tile(cls, tileset: TileSet) -> Tile:
        """retrieve tileset root tile and update root uri

        parameters
        ----------
        tileset: py3dtiles.tileset.TileSet
            tileset to traverse

        returns
        -------
        py3dtiles.tile.Tile
            root tile of the tileset

        """
        if tileset.root_uri is not None:
            cls.root_uri = tileset.root_uri
        return tileset.root_tile

    @classmethod
    def get_tile_content(cls, tile: Tile) -> Optional[Path]:
        """retrieve tile content and resolve relative paths

        parameters
        ----------
        tile: py3dtiles.tile.Tile
            tile to retrieve content from

        returns
        -------
        pathlib.Path or None
            path to tile content or None if not found

        """
        if tile.content is None:
            return None
        uri_: str = tile.content["uri"]
        if uri_[0] == "/":
            uri_ = uri_[1:]
        uri: Path = cls.INPUT_DIR / uri_
        if not uri.exists():
            # try tileset root dir
            uri = cls.root_uri / uri_
        if not uri.exists():
            logging.info("File %s does not exist", uri)
            tile.content = None
            return None
        return uri

    @classmethod
    def write_tileset(cls, tileset: TileSet, name="tileset.json") -> None:
        """write tileset to output directory following input directory
        structure with name as filename

        parameters
        ----------
        tileset: py3dtiles.tileset.TileSet
            tileset to write as JSON
        name: str
            name to save tileset as

        """
        root_uri: Path = tileset.root_uri or cls.root_uri
        rel_path: Path = root_uri.relative_to(cls.INPUT_DIR)
        Path.mkdir(
            cls.OUTPUT_DIR / rel_path,
            parents=True,
            exist_ok=True,
        )
        tileset.write_as_json(cls.OUTPUT_DIR / rel_path / name)
