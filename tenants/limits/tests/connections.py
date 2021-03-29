from contextlib import contextmanager
from unittest import mock


class FakeConnection:
    __slots__ = ("cursor_mock",)

    def __init__(self, cursor_mock: mock.MagicMock):
        self.cursor_mock = cursor_mock

    @contextmanager
    def cursor(self):
        yield self.cursor_mock
