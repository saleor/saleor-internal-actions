#!/usr/bin/env python

from os.path import isfile

from setuptools import setup


def _read_file(path):
    with open(path) as fp:
        return fp.read().strip()


INSTALL_REQUIREMENTS = ["datadog", "opentelemetry-sdk", "opentelemetry-api"]
LINTING_REQUIREMENTS = [
    "black==19.10b0",
    "isort>=5.0.0",
]
TEST_REQUIREMENTS = [
    "mypy>=0.800,<0.900",
    "pytest",
    "pytest-benchmark>=3.2,<3.3",
    "pytest-cov>=2.11,<3.0.0",
]

DEV_REQUIREMENTS = LINTING_REQUIREMENTS + TEST_REQUIREMENTS


if isfile("README.md"):
    long_description = _read_file("README.md")
else:
    long_description = ""

setup(
    name="dogstatsd-metric-exporter",
    packages=["dogstatsd_metric_exporter"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    install_requires=INSTALL_REQUIREMENTS,
    extras_require={
        "dev": DEV_REQUIREMENTS,
        "tests": TEST_REQUIREMENTS,
        "linters": LINTING_REQUIREMENTS,
        "build": ["setuptools", "wheel"],
    },
    zip_safe=False,
)
