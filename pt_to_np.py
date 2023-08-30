"""convert pytorch .pt file to numpy .npy file"""
import argparse
import numpy as np
import torch


def convert(path: str) -> None:
    """convert pytorch .pt file to numpy .npy file"""
    data = torch.load(path)
    np.save(path.replace(".pt", ".npy"), data.detach().cpu().numpy())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", required=True, help="path to .pt file")
    args: argparse.Namespace = parser.parse_args()
    convert(args.path)
