from grant_license_checker.renderers.base import BaseRenderer
from grant_license_checker.renderers.html import HTMLRenderer
from grant_license_checker.renderers.tsv import TSVRenderer
from grant_license_checker.renderers.tty import TTYRenderer

RENDERERS: dict[str, type[BaseRenderer]] = {
    "html": HTMLRenderer,
    "tty": TTYRenderer,
    "tsv": TSVRenderer,
}
