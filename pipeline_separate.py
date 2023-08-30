"""pipeline for segmenting glb files"""
import argparse
from pathlib import Path
import logging
from PIL.Image import Image
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from py3dtiles.tileset.tileset import TileSet, Tile
from tileset_converter import convert_tileset
from image_segment import ImageSegment
from segment_glb_separate import GLBSegment, MeshSegment

from typing import Optional

LOG: logging.Logger = logging.getLogger(__name__)


class Pipeline:
    """pipeline for segmenting glb files in 3d tilesets"""

    INPUT_DIR: Path = Path(".")
    OUTPUT_DIR: Path = Path(".")
    root_uri: Path = Path(".")
    glb_count: int = 0
    GLB_PBAR = tqdm(desc="GLB files", unit=" .glb")
    tileset_count: int = 0
    TILESET_PBAR = tqdm(desc="Tilesets", unit=" tileset")

    @classmethod
    def reset(cls) -> None:
        """reset counts"""
        cls.glb_count = 0
        cls.tileset_count = 0
        cls.GLB_PBAR.reset()
        cls.TILESET_PBAR.reset()

    @staticmethod
    def get_meshes_segmented(path: Path) -> list[MeshSegment]:
        """get meshes segmented"""
        glb = GLBSegment(path)
        try:
            glb.load_meshes()
        except ValueError as err:
            LOG.error("Error loading meshes: %s", err)
            return []
        meshes: list[MeshSegment] = glb.meshes
        for i, mesh in enumerate(
            tqdm(
                meshes,
                desc="Segmenting textures",
                unit="texture",
                leave=False,
            )
        ):
            texture: Optional[Image] = mesh.get_texture_image()
            if texture is None:
                LOG.warning("Mesh %s has no texture", i)
                continue
            LOG.info("Predicting semantic segmentation")
            mesh.seg = ImageSegment(texture).predict_semantic()
        return meshes

    @classmethod
    def rewrite_tile(cls, tile: Tile, uri: Path) -> None:
        """rewrite tile"""
        tile.content = None
        if tile.contents is None:
            tile.contents = []
        count: str = hex(cls.glb_count)[2:]
        if (cls.OUTPUT_DIR / f"glb{count}").exists():
            LOG.info("GLB directory already exists")
            for file in (cls.OUTPUT_DIR / f"glb{count}").iterdir():
                tile.contents.append(
                    {
                        "uri": f"glb{count}/{file.name}",
                        "group": int(file.stem.split("_")[1]),
                    }
                )
            cls.glb_count += 1
            cls.GLB_PBAR.update()
            return
        meshes: list[MeshSegment] = cls.get_meshes_segmented(uri)
        LOG.info("Rewriting tile")
        for i, mesh in enumerate(meshes):
            for class_id, submesh in tqdm(
                mesh.submeshes.items(),
                desc="Exporting submeshes",
                unit="submesh",
                leave=False,
            ):
                _uri: str = f"glb{count}/mesh{i}_{class_id}.glb"
                mesh.export_submesh(submesh, cls.OUTPUT_DIR / _uri)
                tile.contents.append({"uri": _uri, "group": class_id})
        cls.glb_count += 1
        cls.GLB_PBAR.update()

    @classmethod
    def segment_tileset(cls, tileset: TileSet) -> None:
        """segment tileset"""
        LOG.info("Segmenting tileset")
        count: str = hex(cls.tileset_count)[2:]
        cls.tileset_count += 1
        if tileset.root_uri is not None:
            cls.root_uri = tileset.root_uri
        convert_tileset(tileset, ImageSegment.get_labels())
        cls.segment_tile(tileset.root_tile)
        tileset.write_as_json(cls.OUTPUT_DIR / f"tileset_{count}.json")
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
            cls.rewrite_tile(tile, uri)
        if uri.suffix == ".json":
            count: str = hex(cls.tileset_count)[2:]
            tile.content["uri"] = f"tileset_{count}.json"
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
