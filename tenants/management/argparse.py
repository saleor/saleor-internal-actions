import argparse
import collections
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union

from botocore.exceptions import ParamValidationError
from botocore.handlers import validate_bucket_name
from django.conf import settings
from urllib3.util import Url, parse_url
from urllib3.util.url import SCHEME_RE

LOCATION_TYPE = Union[Path, "S3Options"]


# pylint: disable=too-many-ancestors
@dataclass(repr=False)
class S3Options(collections.UserDict):
    Key: str
    Bucket: str

    # pylint: disable=super-init-not-called
    def __init__(self, **_):
        super().__init__(**_)
        self.full_clean()

    def __str__(self):
        return str(Url(scheme="s3", host=self.Bucket, path=self.Key))

    @property
    def data(self):
        return self.__dict__

    @data.setter
    def data(self, _value):
        ...

    def full_clean(self):
        if not self.Bucket:
            raise argparse.ArgumentTypeError("Bucket name is required.")

        try:
            validate_bucket_name(params=self)
        except ParamValidationError as exc:
            raise argparse.ArgumentTypeError(*exc.args) from exc


# pylint: disable=protected-access
def remove_actions(parser, *dests: str) -> None:
    for action in parser._actions:
        if action.dest in dests:
            parser._remove_action(action)


def parse_s3_url(url: Url) -> S3Options:
    """S3 URL to a bucket file, i.e. s3://[bucket-name]/key"""
    assert url.scheme == "s3"

    bucket_key = (url.path or "").strip("/")  # remove any trailing slash
    bucket_name = url.host or settings.DEFAULT_BACKUP_BUCKET_NAME

    if not bucket_key:
        raise argparse.ArgumentTypeError("Bucket key is required (filename).")

    return S3Options(Key=bucket_key, Bucket=bucket_name)


def location_type(raw_location: str) -> LOCATION_TYPE:
    """Parse a raw input location to a local path or remote URL if RFC 1738 input."""
    url = parse_url(raw_location)

    if url.scheme is None:
        return Path(raw_location)
    if url.scheme == "s3":
        return parse_s3_url(url)

    raise argparse.ArgumentTypeError(f"{url.scheme} is not a supported scheme.")
