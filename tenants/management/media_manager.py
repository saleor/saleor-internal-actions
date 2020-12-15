import logging
from pathlib import Path

from django.core.files.storage import get_storage_class

from tenants.storages import TenantAwareStorage

logger = logging.getLogger(__name__)


class MediaManager:
    MEDIA_SKIP_DIRS = []

    def __init__(self, media_dir: Path):
        self.media_dir = media_dir
        self.storage: TenantAwareStorage = get_storage_class()()

    def download(self):
        self.storage.download_dir(self.media_dir, excludes=self.MEDIA_SKIP_DIRS)

    def upload(self):
        self.storage.upload_dir(self.media_dir, excludes=self.MEDIA_SKIP_DIRS)
