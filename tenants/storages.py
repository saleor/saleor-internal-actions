import logging
import subprocess
from pathlib import Path
from typing import Tuple, List
from urllib.parse import urljoin
from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.utils.encoding import filepath_to_uri
from storages.utils import safe_join
from tenant_schemas.storage import TenantStorageMixin
from saleor.core.storages import S3MediaStorage

logger = logging.getLogger(__name__)


class TenantAwareStorage(TenantStorageMixin):
    @property
    def tenant_domain(self):
        return connection.tenant.domain_url

    @property
    def tenant_location(self):
        try:
            return safe_join(self.location, self.tenant_domain)
        except AttributeError:
            return self.location

    def upload_dir(self, dir_path, excludes=None):
        dirs = [dir_path]
        while dirs:
            current_dir = dirs.pop()
            for path in current_dir.iterdir():
                if path.is_dir():
                    dirs.append(path)
                else:
                    self._upload_file(dir_path, path)

    def _upload_file(self, dir_path: Path, file_path: Path):
        storage_path = file_path.relative_to(dir_path)
        logger.info("Uploading %s", storage_path)
        with open(file_path, "rb") as f:
            self.save(str(storage_path), f)

    def download_dir(self, dir_path, excludes=None):
        root = Path("")
        dirs = [root]
        while dirs:
            current_dir = dirs.pop()
            local_path = dir_path / current_dir
            local_path.mkdir(mode=0o700)

            subdirs, files = self._list_storage_dir(current_dir)
            for filename in files:
                self._download_file(dir_path, current_dir / filename)

            dirs.extend(
                [current_dir / subdir for subdir in subdirs if subdir not in excludes]
            )

    def _list_storage_dir(self, path: Path) -> Tuple[List[str], List[str]]:
        try:
            return self.listdir(str(path))
        except FileNotFoundError:
            return [], []

    def _download_file(self, dir_path: Path, file_path: Path):
        logger.info("Downloading %s to %s", file_path, dir_path)
        content = self.open(str(file_path)).read()
        local_path = dir_path / file_path
        with open(local_path, "wb") as f:
            f.write(content)


class TenantS3MediaStorage(TenantAwareStorage, S3MediaStorage):
    def url(self, name, parameters=None, expire=None):
        name = self._normalize_resource_name("media", self._clean_name(name))
        return "%s//%s/%s" % (
            self.url_protocol,
            self.tenant_domain,
            filepath_to_uri(name),
        )

    def _normalize_name(self, name):
        return self._normalize_resource_name(self.tenant_location, name)

    def _normalize_resource_name(self, location, name):
        try:
            return safe_join(location, name)
        except ValueError:
            raise SuspiciousOperation("Attempted access to '%s' denied." % name)

    def upload_dir(self, dir_path, excludes=None):
        bucket_url = f"s3://{self.bucket.name}/{self.tenant_location}"
        cmd = ["aws", "s3", "sync", str(dir_path), bucket_url]
        if excludes:
            for exclude in excludes:
                cmd += ["--exclude", exclude]
        subprocess.check_call(cmd)

    def download_dir(self, dir_path, excludes=None):
        bucket_url = f"s3://{self.bucket.name}/{self.tenant_location}"
        cmd = ["aws", "s3", "sync", bucket_url, str(dir_path)]
        if excludes:
            for exclude in excludes:
                cmd += ["--exclude", exclude]
        subprocess.check_call(cmd)


class TenantFileSystemStorage(TenantAwareStorage, FileSystemStorage):
    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        tennant_base_url = "{}/{}/".format(self.base_url, self.tenant_domain)
        url = filepath_to_uri(name)
        if url is not None:
            url = url.lstrip("/")
        return urljoin(tennant_base_url, url)
