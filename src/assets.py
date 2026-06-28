"""Asset loading utilities for MBM Mod Loader."""

from pathlib import Path

from PIL import Image, ImageTk
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

from config import _bundle_dir

ASSETS_DIR = _bundle_dir() / "assets"


def load_svg_as_photo(name: str, height: int) -> ImageTk.PhotoImage:
    """Rasterize an SVG from the assets folder and return a tkinter PhotoImage.

    The image is scaled so it fits within ``height`` pixels, preserving the
    aspect ratio. The caller must keep a reference to the returned object so
    tkinter does not garbage-collect it.
    """
    path = ASSETS_DIR / name
    drawing = svg2rlg(str(path))
    scale = height / drawing.height
    drawing.width = drawing.width * scale
    drawing.height = height
    drawing.transform = (scale, 0, 0, scale, 0, 0)
    pil_img = renderPM.drawToPIL(drawing)
    return ImageTk.PhotoImage(pil_img)
