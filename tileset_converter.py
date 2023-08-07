from py3dtiles.tileset.tileset import TileSet, MetadataEntity, Schema
import re


def convert_tileset(tileset: TileSet, labels: dict) -> None:
    """convert tileset to 1.1 with groups and schema"""
    tileset.asset.version = "1.1"
    tileset.groups = [
        MetadataEntity(re.sub(r"[^a-zA-Z0-9_]", "_", label))
        for label in labels.values()
    ]
    tileset.schema = Schema.from_dict(
        {
            "id": "schema",
            "classes": {
                re.sub(r"[^a-zA-Z0-9_]", "_", label): {
                    "name": label,
                }
                for label in labels.values()
            },
        }
    )
