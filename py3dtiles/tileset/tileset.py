from __future__ import annotations

import json
from pathlib import Path
from typing import Generator, Literal, TYPE_CHECKING

from py3dtiles.typing import (
    AssetDictType,
    GeometricErrorType,
    TilesetDictType,
    MetadataEntityDictType,
    PropertyType,
    ClassDictType,
    EnumValueDictType,
    EnumDictType,
    SchemaDictType,
)
from .root_property import RootProperty
from .tile import Tile

if TYPE_CHECKING:
    from .content import TileContent
    from typing_extensions import Self


class MetadataEntity(RootProperty[MetadataEntityDictType]):
    def __init__(self, _class: str) -> None:
        super().__init__()
        self._class: str = _class
        self.properties: PropertyType | None = None

    @classmethod
    def from_dict(cls, metadata_dict: MetadataEntityDictType) -> Self:
        metadata = cls(metadata_dict["class"])
        metadata.set_properties_from_dict(metadata_dict)
        metadata.properties = metadata_dict.get("properties")

        return metadata

    def to_dict(self) -> MetadataEntityDictType:
        metadata_dict: MetadataEntityDictType = {"class": self._class}

        metadata_dict = self.add_root_properties_to_dict(metadata_dict)

        if self.properties is not None:
            metadata_dict["properties"] = self.properties

        return metadata_dict


class Class(RootProperty[ClassDictType]):
    def __init__(self) -> None:
        super().__init__()
        self.name: str | None = None
        self.description: str | None = None
        self.properties: PropertyType | None = None

    @classmethod
    def from_dict(cls, class_dict: ClassDictType) -> Self:
        _class = cls()
        _class.set_properties_from_dict(class_dict)
        _class.name = class_dict.get("name")
        _class.description = class_dict.get("description")
        _class.properties = class_dict.get("properties")

        return _class

    def to_dict(self) -> ClassDictType:
        class_dict: ClassDictType = {}

        class_dict = self.add_root_properties_to_dict(class_dict)

        if self.name is not None:
            class_dict["name"] = self.name

        if self.description is not None:
            class_dict["description"] = self.description

        if self.properties is not None:
            class_dict["properties"] = self.properties

        return class_dict


class EnumValue(RootProperty[EnumValueDictType]):
    def __init__(self, name: str, value: int) -> None:
        super().__init__()
        self.name: str = name
        self.description: str | None = None
        self.value: int = value

    @classmethod
    def from_dict(cls, enum_value_dict: EnumValueDictType) -> Self:
        enum_value = cls(enum_value_dict["name"], enum_value_dict["value"])
        enum_value.set_properties_from_dict(enum_value_dict)
        enum_value.description = enum_value_dict.get("description")

        return enum_value

    def to_dict(self) -> EnumValueDictType:
        enum_value_dict: EnumValueDictType = {
            "name": self.name,
            "value": self.value,
        }

        enum_value_dict = self.add_root_properties_to_dict(enum_value_dict)

        if self.description is not None:
            enum_value_dict["description"] = self.description

        return enum_value_dict


class Enum(RootProperty[EnumDictType]):
    def __init__(self, values: list[EnumValue]) -> None:
        super().__init__()
        self.name: str | None = None
        self.description: str | None = None
        self.values: list[EnumValue] = values

    @classmethod
    def from_dict(cls, enum_dict: EnumDictType) -> Self:
        enum = cls(
            [EnumValue.from_dict(value) for value in enum_dict["values"]]
        )
        enum.set_properties_from_dict(enum_dict)
        enum.name = enum_dict.get("name")
        enum.description = enum_dict.get("description")

        return enum

    def to_dict(self) -> EnumDictType:
        enum_dict: EnumDictType = {
            "values": [value.to_dict() for value in self.values]
        }

        enum_dict = self.add_root_properties_to_dict(enum_dict)

        if self.name is not None:
            enum_dict["name"] = self.name

        if self.description is not None:
            enum_dict["description"] = self.description

        return enum_dict


class Schema(RootProperty[SchemaDictType]):
    def __init__(self, id: str) -> None:
        super().__init__()
        self.id: str = id
        self.name: str | None = None
        self.description: str | None = None
        self.version: str | None = None
        self.classes: dict[str, Class] | None = None
        self.enums: dict[str, Enum] | None = None

    @classmethod
    def from_dict(cls, schema_dict: SchemaDictType) -> Self:
        schema = cls(schema_dict["id"])
        schema.set_properties_from_dict(schema_dict)
        schema.name = schema_dict.get("name")
        schema.description = schema_dict.get("description")
        schema.version = schema_dict.get("version")
        if "classes" in schema_dict:
            schema.classes = {
                key: Class.from_dict(class_dict)
                for key, class_dict in schema_dict["classes"].items()
            }
        if "enums" in schema_dict:
            schema.enums = {
                key: Enum.from_dict(enum_dict)
                for key, enum_dict in schema_dict["enums"].items()
            }
        return schema

    def to_dict(self) -> SchemaDictType:
        schema_dict: SchemaDictType = {"id": self.id}

        schema_dict = self.add_root_properties_to_dict(schema_dict)

        if self.name is not None:
            schema_dict["name"] = self.name

        if self.description is not None:
            schema_dict["description"] = self.description

        if self.version is not None:
            schema_dict["version"] = self.version

        if self.classes is not None:
            schema_dict["classes"] = {
                key: _class.to_dict() for key, _class in self.classes.items()
            }

        if self.enums is not None:
            schema_dict["enums"] = {
                key: enum.to_dict() for key, enum in self.enums.items()
            }

        return schema_dict


class Asset(RootProperty[AssetDictType]):
    def __init__(
        self,
        version: Literal["1.0", "1.1"] = "1.0",
        tileset_version: str | None = None,
    ) -> None:
        super().__init__()
        self.version: Literal["1.0", "1.1"] = version
        self.tileset_version: str | None = tileset_version

    @classmethod
    def from_dict(cls, asset_dict: AssetDictType) -> Self:
        asset = cls(asset_dict["version"])
        if "tilesetVersion" in asset_dict:
            asset.tileset_version = asset_dict["tilesetVersion"]

        asset.set_properties_from_dict(asset_dict)

        return asset

    def to_dict(self) -> AssetDictType:
        asset_dict: AssetDictType = {"version": self.version}

        asset_dict = self.add_root_properties_to_dict(asset_dict)

        if self.tileset_version is not None:
            asset_dict["tilesetVersion"] = self.tileset_version

        return asset_dict


class TileSet(RootProperty[TilesetDictType]):
    def __init__(
        self,
        geometric_error: float = 500,
        root_uri: Path | None = None,
    ) -> None:
        super().__init__()
        self.asset = Asset(version="1.0")
        self.geometric_error: GeometricErrorType = geometric_error
        self.root_tile = Tile()
        self.root_uri: Path | None = root_uri
        self.groups: list[MetadataEntity] | None = None
        self.properties: PropertyType | None = None
        self.extensions_used: set[str] = set()
        self.extensions_required: set[str] = set()
        self.schema: Schema | None = None

    @classmethod
    def from_dict(cls, tileset_dict: TilesetDictType) -> Self:
        tileset = cls(geometric_error=tileset_dict["geometricError"])

        tileset.asset = Asset.from_dict(tileset_dict["asset"])
        tileset.root_tile = Tile.from_dict(tileset_dict["root"])
        tileset.set_properties_from_dict(tileset_dict)

        if "extensionsUsed" in tileset_dict:
            tileset.extensions_used = set(tileset_dict["extensionsUsed"])
        if "extensionsRequired" in tileset_dict:
            tileset.extensions_required = set(
                tileset_dict["extensionsRequired"]
            )
        if "groups" in tileset_dict:
            tileset.groups = [
                MetadataEntity.from_dict(group)
                for group in tileset_dict["groups"]
            ]

        if "properties" in tileset_dict:
            tileset.properties = tileset_dict["properties"]

        if "schema" in tileset_dict:
            tileset.schema = Schema.from_dict(tileset_dict["schema"])

        return tileset

    @staticmethod
    def from_file(tileset_path: Path) -> TileSet:
        with tileset_path.open() as f:
            tileset_dict = json.load(f)

        tileset: TileSet = TileSet.from_dict(tileset_dict)
        tileset.root_uri = tileset_path.parent

        return tileset

    def get_all_tile_contents(
        self,
    ) -> Generator[TileContent | TileSet, None, None]:
        tiles = [self.root_tile] + self.root_tile.get_all_children()
        for tile in tiles:
            yield tile.get_or_fetch_content(self.root_uri)

    def delete_on_disk(
        self, tileset_path: Path, delete_sub_tileset: bool = False
    ) -> None:
        """
        Deletes all files linked to the tileset. The uri of the tileset should be defined.

        :param tileset_path: The path of the tileset
        :param delete_sub_tileset: If True, all tilesets present as tile content will be removed as well as their content.
        If False, the linked tilesets in tiles won't be removed.
        """
        tileset_path.unlink()
        self.root_tile.delete_on_disk(tileset_path.parent, delete_sub_tileset)

    def write_to_directory(
        self, tileset_path: Path, overwrite: bool = False
    ) -> None:
        """
        Write (or overwrite), to the directory whose name is provided, the
        TileSet that is:
        - the tileset as a json file and
        - all the tiles content of the Tiles used by the Tileset.
        :param tileset_path: the target directory name
        :param overwrite: delete the tileset (and the content) if already exists
        """
        if tileset_path.exists():
            if overwrite:
                tileset = TileSet.from_file(tileset_path)
                tileset.delete_on_disk(tileset_path, delete_sub_tileset=True)
            else:
                raise FileExistsError(
                    f"There is already a file at {tileset_path} and overwrite is False"
                )

        # Proceed with the writing of the TileSet per se:
        self.write_as_json(tileset_path)

        # Prior to writing the TileSet, the future location of the enclosed
        # Tile's content (set as their respective TileContent uri) must be
        # specified:
        all_tiles: list[Tile] = self.root_tile.get_all_children()
        all_tiles.append(self.root_tile)
        for tile in all_tiles:
            if tile.tile_content is not None:
                tile.write_content(tileset_path.parent)

    def write_as_json(self, tileset_path: Path) -> None:
        """
        Write the tileset as a JSON file.
        :param tileset_path: the path where the tileset will be written
        """
        with tileset_path.open("w") as f:
            f.write(self.to_json())

    def to_dict(self) -> TilesetDictType:
        """
        Convert to json string possibly mentioning used schemas
        """
        # Make sure the TileSet is aligned with its children Tiles.
        self.root_tile.sync_bounding_volume_with_children()

        tileset_dict: TilesetDictType = {
            "root": self.root_tile.to_dict(),
            "asset": self.asset.to_dict(),
            "geometricError": self.geometric_error,
        }

        tileset_dict = self.add_root_properties_to_dict(tileset_dict)

        if self.extensions_used:
            tileset_dict["extensionsUsed"] = list(self.extensions_used)
        if self.extensions_required:
            tileset_dict["extensionsRequired"] = list(self.extensions_required)
        if self.groups:
            tileset_dict["groups"] = [group.to_dict() for group in self.groups]
        if self.properties is not None:
            tileset_dict["properties"] = self.properties
        if self.schema is not None:
            tileset_dict["schema"] = self.schema.to_dict()

        return tileset_dict

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))
