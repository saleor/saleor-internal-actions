import logging
import shutil
import tempfile
from pathlib import Path
from tarfile import TarFile
from typing import IO, Optional, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


class TenantDump:
    DEFAULT_COMPRESSION_LEVEL = 6
    IGNORE_ERRS_RMTREE = True
    MEDIA_DIRNAME = "media"
    SCHEMA_DATA_FILENAME = "schema.json"

    def __init__(self, *, temp_working_directory: Optional[Path] = None):
        self._temp_working_directory: Optional[Path] = temp_working_directory

    @property
    def temp_working_directory(self) -> Path:
        if self._temp_working_directory is None:
            self._temp_working_directory = Path(tempfile.gettempdir(), uuid4().hex)

        return self._temp_working_directory

    def get_archive_path(self):
        archive_path = Path(f"{self._temp_working_directory!s}.tar.gz")
        return archive_path

    @property
    def schema_path(self):
        return self.temp_working_directory / self.SCHEMA_DATA_FILENAME

    @property
    def media_dir(self):
        return self.temp_working_directory / self.MEDIA_DIRNAME

    def start(self):
        self.temp_working_directory.mkdir(mode=0o700)

    def stop(self):
        shutil.rmtree(
            self.temp_working_directory, ignore_errors=self.IGNORE_ERRS_RMTREE
        )

    def compress_all(
        self, archive_path: Optional[str] = None, level: int = DEFAULT_COMPRESSION_LEVEL
    ):
        archive_path = archive_path or self.get_archive_path()
        with TarFile.gzopen(
            name=archive_path, mode="w", compresslevel=level
        ) as archive:
            archive.add(name=self.schema_path, arcname=self.SCHEMA_DATA_FILENAME)
            archive.add(name=self.media_dir, arcname=self.MEDIA_DIRNAME)
        logger.info("Created archive at: %s", archive_path)

    def decompress_all(
        self,
        archive_path: Optional[Path] = None,
        fileobj: Optional[Union[IO, bytes]] = None,
    ):
        work_path = self.temp_working_directory

        if not any([archive_path, fileobj]):
            archive_path = self.get_archive_path()

        with TarFile.gzopen(name=archive_path, fileobj=fileobj, mode="r") as archive:
            for member in archive.getmembers():
                logger.info("Extracting %s to %s", member.name, work_path)
                archive.extract(member, path=work_path)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.stop()
