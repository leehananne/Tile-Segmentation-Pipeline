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


class ImageSegment:
    """run image segmentation on a single image"""

    URL = "facebook/mask2former-swin-small-cityscapes-semantic"
    MODEL = Mask2FormerForUniversalSegmentation.from_pretrained(URL)
    PROCESSOR = AutoImageProcessor.from_pretrained(URL)

    @property
    def labels(self) -> dict:
        """returns list of labels"""
        if not hasattr(self, "_labels") or self._labels is None:
            self._labels = self.get_labels()
        return self._labels

    def __init__(self, image: Image.Image) -> None:
        self.image: Image.Image = image

    @classmethod
    def get_labels(cls) -> dict:
        """returns list of labels"""
        if cls.MODEL is None:
            raise RuntimeError("Model not initialised")
        if cls.MODEL.config is None:
            raise RuntimeError("Model config not initialised")
        return cls.MODEL.config.id2label or {}

    @classmethod
    def predict_semantic_image(cls, image: Image.Image) -> np.ndarray:
        """predict semantic segmentation on a single image"""
        inputs = cls.PROCESSOR(image, return_tensors="pt")
        with torch.no_grad():
            outputs = cls.MODEL(**inputs)
        return cls.PROCESSOR.post_process_semantic_segmentation(
            outputs, target_sizes=[image.size[::-1]]
        )[0]

    def predict_semantic(self) -> np.ndarray:
        """predict semantic segmentation on a single image"""
        return self.predict_semantic_image(self.image)

    def visualise(self, seg: np.ndarray) -> None:
        """visualise image segmentation"""
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
    def save_seg(seg: np.ndarray) -> None:
        """save segmentation to a file"""
        torch.save(seg, "map.pt")


def main(image_path: str, save=False) -> None:
    """main"""
    image: Image.Image = Image.open(image_path)
    image_segment: ImageSegment = ImageSegment(image)
    # seg: np.ndarray = image_segment.predict_semantic()
    # if save:
    #     image_segment.save_seg(seg)
    seg = np.load("map.npy")
    image_segment.visualise(seg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f", "--file", required=True, type=str, help="path to image file"
    )
    parser.add_argument("-s", "--save", action="store_true")
    args: argparse.Namespace = parser.parse_args()
    main(args.file, args.save)
