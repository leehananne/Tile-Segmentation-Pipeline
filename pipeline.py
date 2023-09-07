"""pipeline for segmenting glb files"""
import argparse
from pathlib import Path
import logging
from typing import Optional
from PIL.Image import Image
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from py3dtiles.tileset.tileset import TileSet, Tile
from classify import ImageSegmenter, texture_to_vertices
from glb import GLBSegment
from tileset import TilesetTraverser, convert_tileset


LOG: logging.Logger = logging.getLogger(__name__)


class Pipeline(TilesetTraverser):
    """pipeline for segmenting glb files in 3D tilesets

    exports each glb file into a new glb file with metadata for each
    subprimitive

    attributes
    ----------
    INPUT_DIR: pathlib.Path
        input directory of the tileset
    OUTPUT_DIR: pathlib.Path
        output directory of the tileset
    root_uri: pathlib.Path
        root uri of the tileset to resolve relative paths
    glb_count: int
        number of glb files segmented
    GLB_PBAR: tqdm.tqdm
        progress bar for glb files
    tileset_count: int
        number of tilesets segmented
    TILESET_PBAR: tqdm.tqdm
        progress bar for tilesets

    examples
    --------
    >>> Pipeline.INPUT_DIR = Path("input")
    >>> Pipeline.OUTPUT_DIR = Path("output")
    >>> Pipeline.pipeline(Path("tileset.json"))

    """

    glb_count: int = 0
    """number of glb files segmented"""

    GLB_PBAR = tqdm(desc="GLB files", unit=" .glb")
    """progress bar for glb files"""

    tileset_count: int = 0
    """number of tilesets segmented"""

    TILESET_PBAR = tqdm(desc="Tilesets", unit=" tileset")
    """progress bar for tilesets"""

    @classmethod
    def reset(cls) -> None:
        """reset the counters and progress bars

        this method should be called before running the pipeline again

        """
        cls.glb_count = 0
        cls.tileset_count = 0
        cls.GLB_PBAR.reset()
        cls.TILESET_PBAR.reset()

    @staticmethod
    def get_classified_glb(path: Path) -> Optional[GLBSegment]:
        """returns a GLBSegment with subprimitives classified by semantic
        segmentation of the texture image

        parameters
        ----------
        path: pathlib.Path
            path to glb file

        returns
        -------
        GLBSegment or None
            GLBSegment with subprimitives classified by semantic segmentation
            of the texture image or None if the GLBSegment could not be loaded

        """
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
                seg = ImageSegmenter(texture).predict_semantic()
                primitive.vertices_to_class = texture_to_vertices(
                    primitive.data.points, primitive.data.tex_coord, seg
                )
        return glb

    @classmethod
    def export_classified_glb(cls, uri: Path) -> None:
        """exports a GLBSegment with subprimitives classified by semantic
        segmentation of the texture image

        parameters
        ----------
        uri: pathlib.Path
            path to glb file

        """
        uri_: Path = uri.relative_to(cls.INPUT_DIR)
        if (cls.OUTPUT_DIR / uri_).exists():
            LOG.info("GLB directory already exists")
            cls.GLB_PBAR.update()
            return
        glb: Optional[GLBSegment] = cls.get_classified_glb(uri)
        if glb is None:
            return
        glb.export(cls.OUTPUT_DIR / uri_)
        cls.glb_count += 1
        cls.GLB_PBAR.update()

    @classmethod
    def segment_tileset(cls, tileset: TileSet) -> None:
        """traverse tileset and segment root tile

        parameters
        ----------
        tileset: py3dtiles.tileset.TileSet
            tileset to traverse

        """
        LOG.info("Segmenting tileset")
        cls.tileset_count += 1
        cls.segment_tile(cls.get_tileset_tile(tileset))
        cls.TILESET_PBAR.update()

    @classmethod
    def segment_tile(cls, tile: Tile) -> None:
        """traverse tile and segment content and children

        parameters
        ----------
        tile: py3dtiles.tile.Tile
            tile to traverse

        """
        cls.convert_tile_content(tile)
        cls.convert_tile_children(tile)

    @classmethod
    def convert_tile_content(cls, tile: Tile) -> None:
        """convert tile content for glb files and tilesets

        if content is a glb file, export a GLBSegment with subprimitives
        classified by semantic segmentation of the texture image. if content is
        a tileset, segment the tileset

        parameters
        ----------
        tile: py3dtiles.tile.Tile
            tile to convert

        """
        uri: Optional[Path] = cls.get_tile_content(tile)
        if uri is None:
            return
        if uri.suffix == ".glb":
            LOG.info("Segmenting tile")
            cls.export_classified_glb(uri)
        if uri.suffix == ".json":
            cls.segment_tileset(TileSet.from_file(uri))

    @classmethod
    def convert_tile_children(cls, tile: Tile) -> None:
        """convert tile children by segmenting each child tile

        parameters
        ----------
        tile: py3dtiles.tile.Tile
            tile to convert

        """
        if tile.children is None:
            return
        for child in tile.children:
            cls.segment_tile(child)

    @classmethod
    def pipeline(cls, path: Path) -> None:
        """
        pipeline for segmenting glb files in 3D tilesets

        exports each glb file into a new glb file with metadata for each
        subprimitive

        parameters
        ----------
        path: pathlib.Path
            path to tileset

        """
        LOG.info("Starting segmentation")
        LOG.info("Loading tileset")
        tileset: TileSet = TileSet.from_file(cls.INPUT_DIR / path)
        cls.segment_tileset(tileset)
        LOG.info("Segmentation complete")


class PipelineSeparate(Pipeline):
    """pipeline for segmenting glb files in 3D tilesets

    exports each subprimitive into a new glb file and exports the tileset
    with updated metadata and content uris

    attributes
    ----------
    INPUT_DIR: pathlib.Path
        input directory of the tileset
    OUTPUT_DIR: pathlib.Path
        output directory of the tileset
    root_uri: pathlib.Path
        root uri of the tileset to resolve relative paths
    glb_count: int
        number of glb files segmented
    GLB_PBAR: tqdm.tqdm
        progress bar for glb files
    tileset_count: int
        number of tilesets segmented
    TILESET_PBAR: tqdm.tqdm
        progress bar for tilesets

    examples
    --------
    >>> PipelineSeparate.INPUT_DIR = Path("input")
    >>> PipelineSeparate.OUTPUT_DIR = Path("output")
    >>> PipelineSeparate.pipeline(Path("tileset.json"))

    """

    @classmethod
    def segment_tileset(cls, tileset: TileSet) -> None:
        LOG.info("Segmenting tileset")
        count: str = hex(cls.tileset_count)[2:]
        cls.tileset_count += 1
        if tileset.root_uri is not None:
            cls.root_uri = tileset.root_uri
        convert_tileset(tileset, ImageSegmenter.get_labels())
        cls.segment_tile(tileset.root_tile)
        cls.write_tileset(tileset, f"tileset_{count}.json")
        cls.TILESET_PBAR.update()

    @classmethod
    def convert_tile_content(cls, tile: Tile) -> None:
        if tile.content is None:
            return
        uri: Optional[Path] = cls.get_tile_content(tile)
        if uri is None:
            return
        if uri.suffix == ".glb":
            LOG.info("Segmenting tile")
            cls.rewrite_tile(tile, uri)
        if uri.suffix == ".json":
            count: str = hex(cls.tileset_count)[2:]
            tile.content["uri"] = f"tileset_{count}.json"
            cls.segment_tileset(TileSet.from_file(uri))

    @classmethod
    def rewrite_tile(cls, tile: Tile, uri: Path) -> None:
        """rewrite tile content and append subprimitives to tile contents

        parameters
        ----------
        tile: py3dtiles.tile.Tile
            tile to rewrite
        uri: pathlib.Path
            path to glb file

        """
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
        glb: Optional[GLBSegment] = cls.get_classified_glb(uri)
        if glb is None:
            return
        LOG.info("Rewriting tile")
        for i, mesh in enumerate(glb.meshes):
            for j, primitive in enumerate(mesh):
                for class_id, subprimitive in primitive.subprimitives.items():
                    _uri: str = f"glb{count}/mesh{i}_{j}_{class_id}.glb"
                    primitive.export_subprimitive(
                        subprimitive, cls.OUTPUT_DIR / _uri
                    )
                    tile.contents.append({"uri": _uri, "group": class_id})
        cls.glb_count += 1
        cls.GLB_PBAR.update()

    @classmethod
    def pipeline(cls, path: Path) -> None:
        """pipeline for segmenting glb files in 3D tilesets

        exports each subprimitive into a new glb file

        parameters
        ----------
        path: pathlib.Path
            path to tileset

        """
        super().pipeline(path)


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
        "-s",
        "--submeshes",
        action="store_true",
        help="export by splitting glb files",
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
        logging.basicConfig(level=logging.INFO)
    with logging_redirect_tqdm():
        if args.submeshes:
            PipelineSeparate.pipeline(Path(args.filename))
        else:
            Pipeline.pipeline(Path(args.filename))
