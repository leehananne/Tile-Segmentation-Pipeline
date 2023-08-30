"""pipeline for segmenting glb files"""
import argparse
from pathlib import Path
import logging
from PIL.Image import Image
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from py3dtiles.tileset.tileset import TileSet, Tile
from image_segment import ImageSegment
from segment_glb import GLBSegment

from typing import Optional

LOG: logging.Logger = logging.getLogger(__name__)


class Pipeline:
    """pipeline for segmenting glb files in 3d tilesets"""

    INPUT_DIR: Path = Path(".")
    OUTPUT_DIR: Path = Path(".")
    root_uri: Path = Path(".")
    GLB_PBAR = tqdm(desc="GLB files", unit=" .glb")
    TILESET_PBAR = tqdm(desc="Tilesets", unit=" tileset")

    @classmethod
    def reset(cls) -> None:
        """reset counts"""
        cls.GLB_PBAR.reset()
        cls.TILESET_PBAR.reset()

    @staticmethod
    def get_classified_glb(path: Path) -> Optional[GLBSegment]:
        """get meshes segmented"""
        glb = GLBSegment(path)
        try:
            glb.load_meshes()
        except ValueError as err:
            LOG.error("Error loading meshes: %s", err)
            return None
        for mesh in glb.meshes:
            for primitive in tqdm(
                mesh,
                desc="Segmenting textures",
                unit="texture",
                leave=False,
            ):
                texture: Optional[Image] = primitive.get_texture_image()
                if texture is None:
                    LOG.warning("Primitive in %s has no texture", path)
                    continue
                LOG.info("Predicting semantic segmentation")
                primitive.seg = ImageSegment(texture).predict_semantic()
                primitive.classify_points()
        return glb

    @classmethod
    def export_classified_glb(cls, uri: Path) -> None:
        """rewrite tile"""
        uri_: Path = uri.relative_to(cls.INPUT_DIR)
        if (cls.OUTPUT_DIR / uri_).exists():
            LOG.info("GLB directory already exists")
            cls.GLB_PBAR.update()
            return
        glb: Optional[GLBSegment] = cls.get_classified_glb(uri)
        if glb is None:
            return
        glb.export(cls.OUTPUT_DIR / uri_)
        cls.GLB_PBAR.update()

    @classmethod
    def segment_tileset(cls, tileset: TileSet) -> None:
        """segment tileset"""
        LOG.info("Segmenting tileset")
        if tileset.root_uri is not None:
            cls.root_uri = tileset.root_uri
        cls.segment_tile(tileset.root_tile)
        cls.TILESET_PBAR.update()

    @staticmethod
    def segment_tile(tile: Tile) -> None:
        """segment tile"""
        Pipeline.convert_tile_content(tile)
        Pipeline.convert_tile_children(tile)

    @classmethod
    def convert_tile_content(cls, tile: Tile) -> None:
        """convert tile content"""
        if tile.content is None:
            return
        uri_: str = tile.content["uri"]
        if uri_[0] == "/":
            uri_ = uri_[1:]
        uri: Path = cls.INPUT_DIR / uri_
        if not uri.exists():
            # try tileset root dir
            uri = cls.root_uri / uri_
        if not uri.exists():
            LOG.info("File %s does not exist", uri)
            return
        if uri.suffix == ".glb":
            LOG.info("Segmenting tile")
            cls.export_classified_glb(uri)
        if uri.suffix == ".json":
            cls.segment_tileset(TileSet.from_file(uri))

    @classmethod
    def convert_tile_children(cls, tile: Tile) -> None:
        """convert tile children"""
        if tile.children is None:
            return
        for child in tile.children:
            cls.segment_tile(child)

    @classmethod
    def pipeline(cls, path: Path) -> None:
        """pipeline"""
        LOG.info("Starting segmentation")
        LOG.info("Loading tileset")
        tileset: TileSet = TileSet.from_file(cls.INPUT_DIR / path)
        cls.segment_tileset(tileset)
        LOG.info("Segmentation complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Segment a 3D tileset")
    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        help="filename of tileset",
        default="tileset.json",
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
        "-v",
        "--verbose",
        action="store_true",
        help="increase output verbosity",
    )
    args: argparse.Namespace = parser.parse_args()
    if args.input_dir:
        Pipeline.INPUT_DIR = Path(args.input_dir)
    if args.output_dir:
        Pipeline.OUTPUT_DIR = Path(args.output_dir)
    if args.verbose:
        LOG.setLevel(logging.INFO)
    with logging_redirect_tqdm():
        Pipeline.pipeline(Path(args.filename))
