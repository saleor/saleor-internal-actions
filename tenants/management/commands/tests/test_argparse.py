from argparse import ArgumentTypeError
from pathlib import Path

import pytest
from tenants.management.argparse import location_type, S3Options


@pytest.mark.parametrize("path", ["/usr/bin", "./", "./abc/d", "abc"])
def test_parse_location_local_path(path):
    result = location_type(path)
    assert result == Path(path)


@pytest.mark.parametrize(
    "url, expected",
    [
        ("s3:///some/key/", S3Options(Bucket="Dummy", Key="some/key")),
        ("s3://myBucket/key", S3Options(Bucket="myBucket", Key="key")),
    ],
)
def test_parse_location_s3_url(url, expected, settings):
    settings.DEFAULT_BACKUP_BUCKET_NAME = "Dummy"
    result = location_type(url)
    assert result == expected


@pytest.mark.parametrize("default_bucket_name", ["", None])
def test_parse_location_s3_url_no_bucket_name_raises_an_error(
    settings, default_bucket_name
):
    settings.DEFAULT_BACKUP_BUCKET_NAME = default_bucket_name

    with pytest.raises(ArgumentTypeError) as exc:
        location_type("s3:///key")

    assert exc.value.args == ("Bucket name is required.",)


def test_parse_location_s3_url_no_key_raises_an_error(settings):

    with pytest.raises(ArgumentTypeError) as exc:
        location_type("s3://bucket")

    assert exc.value.args == ("Bucket key is required (filename).",)


def test_parse_location_s3_url_invalid_bucket_name():
    with pytest.raises(ArgumentTypeError) as exc:
        S3Options(Bucket="MyBucket%", Key="abc")

    assert 'Invalid bucket name "MyBucket%"' in exc.value.args[0]


def test_parse_location_non_supported_schema():
    with pytest.raises(ArgumentTypeError) as exc:
        location_type("ftp://hello/world")

    assert exc.value.args == ("ftp is not a supported scheme.",)
