"""extract a branch of the tileset from the full tileset"""
import argparse
import logging
from pathlib import Path
import numpy as np
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from py3dtiles.tileset.tileset import TileSet, Tile
from py3dtiles.tileset import BoundingVolumeBox
from gltflib.gltf import GLTF
from pyproj import Transformer

LOG: logging.Logger = logging.getLogger(__name__)


class TilesetExtractor:
    """extract a branch of the tileset from the full tileset"""

    INPUT_DIR: Path = Path(".")
    OUTPUT_DIR: Path = Path(".")
    root_uri: Path = Path(".")
    with_neighbours: bool = False
    TILE_PBAR = tqdm(desc="Tiles checked", unit=" tile")

    def __init__(self, find_name: str) -> None:
        self.find_name = find_name

    def search_tileset(self, tileset: TileSet) -> bool:
        """search tileset"""
        if tileset.root_uri is not None:
            self.root_uri = tileset.root_uri
        return self.search_tile(tileset.root_tile)

    def search_tile(self, tile: Tile) -> bool:
        """search tile"""
        self.TILE_PBAR.update()
        if self.search_tile_content(tile):
            return True
        if self.search_tile_children(tile):
            return True
        return False

    def search_tile_content(self, tile: Tile) -> bool:
        """search tile content"""
        if tile.content is None:
            return False
        uri_: str = tile.content["uri"]
        if uri_[0] == "/":
            uri_ = uri_[1:]
        uri: Path = self.INPUT_DIR / uri_
        if not uri.exists():
            # try tileset root dir
            uri = self.root_uri / uri_
        if self.find_name in uri_:
            LOG.warning("File %s found", self.find_name)
            return True
        if not uri.exists():
            LOG.info("File %s does not exist", uri)
            tile.content = None
            return False
        if uri.suffix == ".json":
            tileset: TileSet = TileSet.from_file(uri)
            root_uri: Path = self.root_uri
            if self.search_tileset(tileset):
                Path.mkdir(
                    self.OUTPUT_DIR
                    / Path.relative_to(uri, self.INPUT_DIR).parent,
                    parents=True,
                    exist_ok=True,
                )
                tileset.write_as_json(
                    self.OUTPUT_DIR / Path.relative_to(uri, self.INPUT_DIR)
                )
                return True
            self.root_uri = root_uri
        return False

    def search_tile_children(self, tile: Tile) -> bool:
        """search tile children"""
        for child in tile.children:
            if not self.search_tile(child):
                continue
            if self.with_neighbours:
                self.with_neighbours = False
            else:
                tile.children = [child]
            return True
        return False

    def extract_tileset(self, tileset_name: str) -> bool:
        """extract tileset"""
        LOG.info("Loading tileset")
        Path.mkdir(self.OUTPUT_DIR, parents=True, exist_ok=True)
        tileset: TileSet = TileSet.from_file(self.INPUT_DIR / tileset_name)
        if self.search_tileset(tileset):
            LOG.info("Writing tileset")
            tileset.write_as_json(self.OUTPUT_DIR / "extract.json")
            return True
        return False


class LatLongExtractor(TilesetExtractor):
    """extract a branch of the tileset from the full tileset by lat long"""

    ECEF_WGS84: Transformer = Transformer.from_crs("EPSG:4978", "EPSG:4326")

    def __init__(self, bounds: np.ndarray) -> None:
        self.bounds: np.ndarray = bounds

    @staticmethod
    def get_gltf_coords(gltf: GLTF) -> list[tuple[float, float]]:
        """get list of lat longs from gltf"""
        if (
            gltf.model.scene is None
            or gltf.model.scenes is None
            or len(gltf.model.scenes) == 0
            or gltf.model.nodes is None
        ):
            return []
        scene = gltf.model.scenes[gltf.model.scene]
        if scene.nodes is None or len(scene.nodes) == 0:
            return []
        coords: list[tuple[float, float]] = []
        lat: float
        long: float
        for node_index in scene.nodes:
            node = gltf.model.nodes[node_index]
            if node.translation is None:
                continue
            # y-up to z-up
            cartesian: tuple[float, float, float] = (
                node.translation[0],
                -node.translation[2],
                node.translation[1],
            )
            lat, long, _ = LatLongExtractor.ECEF_WGS84.transform(*cartesian)
            coords.append((lat, long))
        return coords

    @staticmethod
    def get_tile_centre_coords(tile: Tile) -> tuple[float, float]:
        """get lat long of centre from tile bounding volume"""
        volume = tile.bounding_volume
        if not isinstance(volume, BoundingVolumeBox):
            raise ValueError("Bounding volume is not a box")
        x, y, z = volume.get_center()
        lat, long, _ = LatLongExtractor.ECEF_WGS84.transform(x, y, z)
        return (lat, long)

    @staticmethod
    def check_tile_centre_in_bounds(tile: Tile, bounds: np.ndarray) -> bool:
        """check if tile centre is in bounds"""
        if tile.bounding_volume is None:
            return False
        lat, long = LatLongExtractor.get_tile_centre_coords(tile)
        lat1, lat2 = sorted(bounds.transpose()[0])
        long1, long2 = sorted(bounds.transpose()[1])
        if lat1 <= lat <= lat2 and long1 <= long <= long2:
            return True
        return False

    def search_tile_content(
        self,
        tile: Tile,
    ) -> bool:
        """search tile content"""
        if self.check_tile_centre_in_bounds(tile, self.bounds):
            LOG.warning("Tile within bounds")
            return True
        if tile.content is None:
            return False
        uri_: str = tile.content["uri"]
        if uri_[0] == "/":
            uri_ = uri_[1:]
        uri: Path = self.INPUT_DIR / uri_
        if not uri.exists():
            # try tileset root dir
            uri = self.root_uri / uri_
        if not uri.exists():
            LOG.info("File %s does not exist", uri)
            return False
        if uri.suffix == ".json":
            tileset: TileSet = TileSet.from_file(uri)
            if self.search_tileset(tileset):
                # tileset.write_as_json(cls.OUTPUT_DIR / uri.name)
                Path.mkdir(
                    self.OUTPUT_DIR
                    / Path.relative_to(uri, self.INPUT_DIR).parent,
                    parents=True,
                    exist_ok=True,
                )
                tileset.write_to_directory(
                    self.OUTPUT_DIR / Path.relative_to(uri, self.INPUT_DIR)
                )
                return True
        return False


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        help="filename of tileset",
        default="tileset.json",
    )
    parser.add_argument(
        "-s",
        "--search-name",
        type=str,
        help="name of file to search for",
        # required=True,
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=str,
        help="input directory for tileset",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        help="output directory for tileset",
    )
    parser.add_argument(
        "-n",
        "--with-neighbours",
        action="store_true",
        help="include neighbours",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="increase output verbosity",
    )
    args: argparse.Namespace = parser.parse_args()
    if args.input_dir:
        TilesetExtractor.INPUT_DIR = Path(args.input_dir)
    if args.output_dir:
        TilesetExtractor.OUTPUT_DIR = Path(args.output_dir)
    if args.verbose:
        LOG.setLevel(logging.INFO)
    TilesetExtractor.with_neighbours = args.with_neighbours
    with logging_redirect_tqdm():
        # extractor = TilesetExtractor(args.search_name)
        extractor = LatLongExtractor(
            np.array(((1.348624, 103.846614), (1.352935, 103.851957))),
        )
        if extractor.extract_tileset(args.filename):
            LOG.info("Tileset extracted")
        else:
            LOG.warning("Tileset not extracted")
