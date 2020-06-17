import logging
from pathlib import Path
from typing import Tuple, List

from django.core.files.storage import get_storage_class

logger = logging.getLogger(__name__)


class MediaManager:
    MEDIA_SKIP_DIRS = ["__sized__"]

    def __init__(self, media_dir: Path):
        self.media_dir = media_dir
        self.storage = get_storage_class()()

    def download(self):
        root = Path("")
        dirs = [root]
        while dirs:
            current_dir = dirs.pop()
            local_path = self.media_dir / current_dir
            local_path.mkdir(mode=0o700)

            subdirs, files = self._list_storage_dir(current_dir)
            for filename in files:
                self._download_file(current_dir / filename)

            dirs.extend(
                [
                    current_dir / subdir
                    for subdir in subdirs
                    if subdir not in self.MEDIA_SKIP_DIRS
                ]
            )

    def _download_file(self, path: Path):
        logger.info("Downloading %s to %s", path, self.media_dir)
        content = self.storage.open(path).read()
        local_path = self.media_dir / path
        with open(local_path, "wb") as f:
            f.write(content)

    def upload(self):
        dirs = [self.media_dir]
        while dirs:
            current_dir = dirs.pop()
            for path in current_dir.iterdir():
                if path.is_dir():
                    dirs.append(path)
                else:
                    self._upload_file(path)

    def _upload_file(self, path: Path):
        storage_path = path.relative_to(self.media_dir)
        logger.info("Uploading %s", storage_path)
        with open(path, "rb") as f:
            self.storage.save(str(storage_path), f)

    def _list_storage_dir(self, path) -> Tuple[List[str], List[str]]:
        try:
            return self.storage.listdir(path)
        except FileNotFoundError:
            return [], []
