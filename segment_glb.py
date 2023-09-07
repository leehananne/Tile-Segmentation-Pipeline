"""segment glb with draco compression"""
import argparse
from pathlib import Path

import numpy as np
from glb import GLBSegment


def main(glb_path: Path, output_dir: Path, submeshes: bool) -> None:
    """main"""
    glb = GLBSegment(glb_path)
    glb.load_meshes()
    # ADD VERTICES TO CLASS HERE
    for mesh in glb.meshes:
        for primitive in mesh:
            primitive.vertices_to_class = np.random.randint(
                0, 10, primitive.data.points.shape[0]
            ).tolist()
    if submeshes:
        glb.export_submeshes(output_dir)
    else:
        glb.export(output_dir / glb_path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Segment GLB")
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="GLB file to segment",
        default="model.glb",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        help="Output directory",
        default="output",
    )
    parser.add_argument(
        "-s",
        "--submeshes",
        action="store_true",
        help="Export submeshes",
    )
    args: argparse.Namespace = parser.parse_args()
    main(Path(args.file), Path(args.output_dir), args.submeshes)
