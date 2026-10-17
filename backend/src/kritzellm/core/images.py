"""Page images: sniff the uploaded file, rotate it upright and make the JPEGs everything else uses.

The functions here are CPU-bound; call them from a thread.
"""

import io
import warnings
from dataclasses import dataclass

import pillow_heif
from PIL import Image, ImageOps, UnidentifiedImageError

pillow_heif.register_heif_opener()

NORMALIZED_LONG_EDGE = 2048
"""The normalized image is at most this big on its long edge; it's what gets transcribed."""
THUMBNAIL_LONG_EDGE = 400

_HEIC_BRANDS = {b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx"}

EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/heif": "heif",
    "image/webp": "webp",
}
"""File extension for each media type an original can have."""


class UnsupportedImageError(ValueError):
    """The file isn't a JPEG, PNG, HEIC/HEIF or WebP image (or is broken)."""


class ImageTooLargeError(ValueError):
    """The image has so many pixels it could be a decompression bomb."""


@dataclass(frozen=True, slots=True)
class NormalizedImage:
    media_type: str
    """Media type of the original file, from its content (not from what the client claimed)."""
    normalized: bytes
    """Upright JPEG, at most `NORMALIZED_LONG_EDGE` pixels on its long edge, without metadata."""
    thumbnail: bytes
    """Upright JPEG preview, at most `THUMBNAIL_LONG_EDGE` pixels on its long edge."""
    width: int
    """Width of `normalized`."""
    height: int
    """Height of `normalized`."""


def _media_type(image: Image.Image, data: bytes) -> str:
    match image.format:
        case "JPEG":
            return "image/jpeg"
        case "PNG":
            return "image/png"
        case "WEBP":
            return "image/webp"
        case "HEIF":
            return "image/heic" if data[8:12] in _HEIC_BRANDS else "image/heif"
        case _:
            raise UnsupportedImageError(f"{image.format or 'This'} images aren't supported.")


def _open(data: bytes) -> tuple[Image.Image, str]:
    """The decoded image and its media type."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            image = Image.open(io.BytesIO(data))
            media_type = _media_type(image, data)
            image.load()
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ImageTooLargeError("The image has too many pixels.") from exc
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise UnsupportedImageError("The file isn't a readable image.") from exc
    return image, media_type


def _flatten(image: Image.Image) -> Image.Image:
    """An RGB copy; transparent parts become white, like paper."""
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        background.info = image.info
        return background
    return image.convert("RGB")


def _jpeg(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    # Only the colour profile is kept: EXIF (with GPS), XMP and comments are dropped.
    icc_profile = image.info.get("icc_profile")
    image.save(buffer, "JPEG", quality=quality, optimize=True, icc_profile=icc_profile)
    return buffer.getvalue()


def normalize(data: bytes) -> NormalizedImage:
    """Checks an uploaded file and makes its normalized image and thumbnail.

    Raises `UnsupportedImageError` or `ImageTooLargeError`.
    """
    image, media_type = _open(data)
    upright = _flatten(ImageOps.exif_transpose(image))
    upright.thumbnail((NORMALIZED_LONG_EDGE, NORMALIZED_LONG_EDGE), Image.Resampling.LANCZOS)
    thumbnail = upright.copy()
    thumbnail.thumbnail((THUMBNAIL_LONG_EDGE, THUMBNAIL_LONG_EDGE), Image.Resampling.LANCZOS)
    return NormalizedImage(
        media_type=media_type,
        normalized=_jpeg(upright, quality=90),
        thumbnail=_jpeg(thumbnail, quality=80),
        width=upright.width,
        height=upright.height,
    )
