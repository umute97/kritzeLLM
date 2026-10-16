import io
from collections.abc import Callable

import pytest
from PIL import Image

from kritzellm.core.images import (
    ImageTooLargeError,
    UnsupportedImageError,
    normalize,
)

MakeImage = Callable[..., bytes]


def _open(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


def test_jpeg_is_turned_upright_and_loses_its_metadata(make_image: MakeImage) -> None:
    result = normalize(make_image(size=(300, 200), orientation=6))

    assert result.media_type == "image/jpeg"
    assert (result.width, result.height) == (200, 300)
    normalized = _open(result.normalized)
    assert normalized.format == "JPEG"
    assert normalized.size == (200, 300)
    assert dict(normalized.getexif()) == {}


@pytest.mark.parametrize(
    ("format", "media_type"),
    [("PNG", "image/png"), ("WEBP", "image/webp"), ("HEIF", "image/heic")],
)
def test_other_formats(make_image: MakeImage, format: str, media_type: str) -> None:
    result = normalize(make_image(format, size=(120, 80)))
    assert result.media_type == media_type
    assert (result.width, result.height) == (120, 80)
    assert _open(result.normalized).format == "JPEG"


def test_transparency_becomes_white(make_image: MakeImage) -> None:
    result = normalize(make_image("PNG", size=(20, 20), mode="RGBA", color=(0, 0, 0, 0)))
    normalized = _open(result.normalized)
    assert normalized.mode == "RGB"
    assert all(channel > 250 for channel in normalized.getpixel((10, 10)))  # type: ignore[union-attr]


def test_big_images_shrink_to_2048_and_get_a_400_thumbnail(make_image: MakeImage) -> None:
    result = normalize(make_image(size=(3000, 1500)))
    assert (result.width, result.height) == (2048, 1024)
    assert _open(result.thumbnail).size == (400, 200)


def test_small_images_are_not_upscaled(make_image: MakeImage) -> None:
    result = normalize(make_image(size=(100, 50)))
    assert (result.width, result.height) == (100, 50)
    assert _open(result.thumbnail).size == (100, 50)


@pytest.mark.parametrize("format", ["GIF", "BMP", "TIFF"])
def test_other_image_formats_are_unsupported(make_image: MakeImage, format: str) -> None:
    with pytest.raises(UnsupportedImageError, match="aren't supported"):
        normalize(make_image(format))


@pytest.mark.parametrize("data", [b"", b"not an image", b"\xff\xd8\xff\xe0broken jpeg"])
def test_garbage_is_unsupported(data: bytes) -> None:
    with pytest.raises(UnsupportedImageError):
        normalize(data)


def test_truncated_files_are_unsupported(make_image: MakeImage) -> None:
    with pytest.raises(UnsupportedImageError):
        normalize(make_image(size=(500, 500))[:400])


def test_decompression_bombs_are_too_large(
    make_image: MakeImage, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(ImageTooLargeError):
        normalize(make_image(size=(100, 100)))
