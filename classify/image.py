"""run image segmentation on a single image"""
import argparse
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import torch
from transformers import (
    AutoImageProcessor,
    Mask2FormerForUniversalSegmentation,
)


class ImageSegmenter:
    """run image segmentation on a single image.

    this image segmentation class uses huggingface's transformers library with
    a pretrained model from Mask2FormerForUniversalSegmentation.


    parameters
    ----------
    image: PIL.Image.Image
        image to run image segmentation on

    attributes
    ----------
    image: PIL.Image.Image
        image to run image segmentation on
    labels: dict[int, str]
        id to label mapping used by the model
    URL: str
        url of the pretrained model
    MODEL: transformers.Mask2FormerForUniversalSegmentation
        pretrained model
    PROCESSOR: transformers.AutoImageProcessor
        pretrained model processor

    examples
    --------
    >>> image = Image.open("image.jpg")
    >>> image_segment = ImageSegmenter(image)
    >>> seg = image_segment.predict_semantic()
    >>> image_segment.visualise(seg)
    >>> image_segment.save_seg(seg, "map.pt")

    """

    URL = "facebook/mask2former-swin-small-cityscapes-semantic"
    """url of the pretrained model"""

    MODEL = Mask2FormerForUniversalSegmentation.from_pretrained(URL)
    """pretrained model"""

    PROCESSOR = AutoImageProcessor.from_pretrained(URL)
    """pretrained model processor"""

    def __init__(self, image: Image.Image) -> None:
        self.image: Image.Image = image
        """image to run image segmentation on"""

        self._labels: dict

    @property
    def labels(self) -> dict[int, str]:
        """the id to label mapping used by the model

        returns
        -------
        dict[int, str]
            id to label mapping used by the model

        """
        if not hasattr(self, "_labels") or self._labels is None:
            self._labels = self.get_labels()
        return self._labels

    @classmethod
    def get_labels(cls) -> dict[int, str]:
        """retrieves the id to label mapping used by the model

        returns
        -------
        dict[int, str]
            id to label mapping used by the model

        """
        if cls.MODEL is None:
            raise RuntimeError("Model not initialised")
        if cls.MODEL.config is None:
            raise RuntimeError("Model config not initialised")
        return cls.MODEL.config.id2label or {}

    @classmethod
    def predict_semantic_image(cls, image: Image.Image) -> np.ndarray:
        """predict semantic segmentation on a single image

        parameters
        ----------
        image: PIL.Image.Image
            image to predict semantic segmentation on

        returns
        -------
        np.ndarray
            semantic segmentation map of the image

        """
        inputs = cls.PROCESSOR(image, return_tensors="pt")
        with torch.no_grad():
            outputs = cls.MODEL(**inputs)
        return cls.PROCESSOR.post_process_semantic_segmentation(
            outputs, target_sizes=[image.size[::-1]]
        )[0]

    def predict_semantic(self) -> np.ndarray:
        """predict semantic segmentation on the image initialised with

        returns
        -------
        np.ndarray
            semantic segmentation map of the image

        """
        return self.predict_semantic_image(self.image)

    def visualise(self, seg: np.ndarray) -> None:
        """visualise the segmentation map on the image initialised with

        parameters
        ----------
        seg: np.ndarray
            semantic segmentation map of the image

        """
        color_seg: np.ndarray = np.zeros(
            (seg.shape[0], seg.shape[1], 3), dtype=np.uint8
        )  # height, width, 3
        color_palette = [
            list(np.random.choice(range(256), size=3))
            for _ in range(len(self.get_labels()))
        ]
        palette = np.array(color_palette)
        for label, color in enumerate(palette):
            color_seg[seg == label, :] = color
        # Convert to BGR
        color_seg = color_seg[..., ::-1]

        # Show image + mask
        img = np.array(self.image) * 0.5 + color_seg * 0.5
        img = img.astype(np.uint8)

        # plt.figure(figsize=(15, 10))
        # plt.imshow(img)
        # plt.axis("off")
        # plt.show()

        # show original image and masked image side by side
        fig, ax = plt.subplots(1, 2)
        ax[0].imshow(self.image)
        ax[0].axis("off")
        ax[1].imshow(img)
        ax[1].axis("off")
        plt.show()

    @staticmethod
    def save_seg(seg: np.ndarray, path: str) -> None:
        """save the segmentation map to a file with the given path

        parameters
        ----------
        seg: np.ndarray
            semantic segmentation map of the image
        path: str
            path to save the segmentation map to

        """
        torch.save(seg, path)


def main(image_path: str, save=False) -> None:
    """main"""
    image: Image.Image = Image.open(image_path)
    image_segment: ImageSegmenter = ImageSegmenter(image)
    seg: np.ndarray = image_segment.predict_semantic()
    if save:
        image_segment.save_seg(seg, "map.pt")
    image_segment.visualise(seg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f", "--file", required=True, type=str, help="path to image file"
    )
    parser.add_argument("-s", "--save", action="store_true")
    args: argparse.Namespace = parser.parse_args()
    main(args.file, args.save)
