"""Page image files under `DATA_DIR`.

Each page has a folder `pages/{page_id}/` with `original.{ext}`, `normalized.jpg` and
`thumbnail.jpg`. Uploads are staged under `tmp/` first and moved into place in one rename.

Everything here touches the disk; call it from a thread (`Staging` cleans up on its own).
"""

import asyncio
import shutil
import uuid
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import Self

from kritzellm.api.schemas.pages import ImageVariant

from .images import EXTENSIONS, NormalizedImage


def page_dir(data_dir: Path, page_id: str) -> Path:
    return data_dir / "pages" / page_id


def _file_name(variant: ImageVariant, media_type: str) -> str:
    if variant is ImageVariant.ORIGINAL:
        return f"original.{EXTENSIONS[media_type]}"
    return f"{variant.value}.jpg"


def variant_path(data_dir: Path, page_id: str, variant: ImageVariant, media_type: str) -> Path:
    """Where a page's image variant lives. `media_type` is the original's."""
    return page_dir(data_dir, page_id) / _file_name(variant, media_type)


def delete_page_files(data_dir: Path, page_ids: Iterable[str]) -> None:
    """Removes the pages' folders. Missing ones are fine."""
    for page_id in page_ids:
        shutil.rmtree(page_dir(data_dir, page_id), ignore_errors=True)


class Staging:
    """A scratch folder for one upload, removed on exit with whatever wasn't published."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.root = data_dir / "tmp" / uuid.uuid4().hex

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await asyncio.to_thread(shutil.rmtree, self.root, ignore_errors=True)

    def stage(self, original: bytes, image: NormalizedImage) -> Path:
        """Writes one upload's files into a new folder of the staging area."""
        folder = self.root / uuid.uuid4().hex
        folder.mkdir(parents=True)
        files = {
            ImageVariant.ORIGINAL: original,
            ImageVariant.NORMALIZED: image.normalized,
            ImageVariant.THUMBNAIL: image.thumbnail,
        }
        for variant, data in files.items():
            (folder / _file_name(variant, image.media_type)).write_bytes(data)
        return folder

    def publish(self, staged: Path, page_id: str) -> None:
        """Moves a staged folder into place as the page's image folder."""
        target = page_dir(self.data_dir, page_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        staged.rename(target)
