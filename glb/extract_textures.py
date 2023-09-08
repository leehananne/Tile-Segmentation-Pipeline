"""extracts textures from a gltf file and saves them as pngs"""
import argparse
import io
import mimetypes
from typing import Optional, Union
from gltflib import Image as GLTF_Image, Buffer, BufferView
from gltflib.gltf import GLTF
from gltflib.gltf_resource import GLBResource, GLTFResource, FileResource
from PIL import Image


def gltf_image_to_pillow(
    gltf: GLTF,
    image: GLTF_Image,
    save: bool = False,
    savepath: str = "",
) -> Image.Image:
    """return a gltf image as a pillow image. optionally save it to a file

    parameters
    ----------
    gltf: gltflib.GLTF
        gltf object which contains the image
    image: gltflib.Image
        gltf image to convert
    save: bool
        whether to save the image to a file. defaults to False
    savepath: str
        path to save the image to. the path should not include the file
        extension. defaults to the current directory

    returns
    -------
    PIL.Image.Image
        pillow image

    """
    data: bytes = get_gltf_image_data(gltf, image)
    img: Image.Image = Image.open(io.BytesIO(data))
    if save:
        img.save(f"{savepath}.{get_image_format(image)}")
    return img


def get_gltf_image_data(gltf: GLTF, image: GLTF_Image) -> bytes:
    """get the bytes data from a gltf image

    parameters
    ----------
    gltf: gltflib.GLTF
        gltf object which contains the image
    image: gltflib.Image
        gltf image to get the data from

    returns
    -------
    bytes
        image data

    """
    if image.uri is None:
        if gltf.model.bufferViews is None:
            raise ValueError("Model has no bufferViews")
        if image.bufferView is None:
            raise ValueError("Image has no bufferView")
        if gltf.model.buffers is None:
            raise ValueError("Model has no buffers")
        buffer_view: BufferView = gltf.model.bufferViews[image.bufferView]
        buffer: Buffer = gltf.model.buffers[buffer_view.buffer]
        data: bytes = get_buffer_data(gltf, buffer)
        start: int = buffer_view.byteOffset or 0
        end: int = start + buffer_view.byteLength
        return data[start:end]
    resource: GLTFResource = gltf.get_resource(image.uri)
    if isinstance(resource, FileResource):
        resource.load()
    return resource.data


def get_buffer_data(gltf: GLTF, buffer: Buffer) -> bytes:
    """get the bytes data from a buffer

    parameters
    ----------
    gltf: gltflib.GLTF
        gltf object which contains the buffer
    buffer: gltflib.Buffer
        buffer to get the data from

    returns
    -------
    bytes
        buffer data

    """
    resource: Union[GLBResource, GLTFResource] = (
        gltf.get_glb_resource()
        if buffer.uri is None
        else gltf.get_resource(buffer.uri)
    )
    if isinstance(resource, FileResource):
        resource.load()
    return resource.data


def get_image_format(image: GLTF_Image) -> str:
    """get the format of a gltf image

    parameters
    ----------
    image: gltflib.Image
        gltf image to get the format of

    returns
    -------
    str
        image format (png or jpg)

    """
    mime_type: Optional[str] = image.mimeType
    if mime_type is None:
        if image.uri is None:
            raise RuntimeError("Image is missing MIME type and has no URI")
        mime_type = mimetypes.guess_type(image.uri)[0]
    if mime_type == "image/png":
        return "png"
    if mime_type == "image/jpeg":
        return "jpg"
    raise RuntimeError(f"Unsupported image MIME type: {mime_type}")


def glb_to_pillow(
    gltf: GLTF, save: bool = False, savepath: str = "."
) -> list[Image.Image]:
    """return a list of pillow images from a gltf file

    parameters
    ----------
    gltf: gltflib.GLTF
        gltf object to get the images from
    save: bool
        whether to save the images to files. defaults to False
    savepath: str
        the directory to save the images to. defaults to the current directory

    returns
    -------
    list[PIL.Image.Image]
        list of pillow images

    """
    images: list[GLTF_Image] = gltf.model.images or []
    return [
        gltf_image_to_pillow(gltf, image, save, f"{savepath}/image_{i}")
        for i, image in enumerate(images)
    ]


def main(file: str, save: bool = False, savepath: str = ".") -> None:
    """extract textures from a gltf file"""
    gltf: GLTF = GLTF.load(file)
    glb_to_pillow(gltf, save, savepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        type=str,
        help="path to gltf file",
    )
    parser.add_argument("-s", "--save", action="store_true")
    parser.add_argument("-p", "--path", type=str, default=".")
    args: argparse.Namespace = parser.parse_args()
    main(args.file, args.save, args.path)
