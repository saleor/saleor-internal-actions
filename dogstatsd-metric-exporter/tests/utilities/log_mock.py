import logging
from collections import defaultdict
from typing import Any, Mapping, Optional, Union


class LoggingHandler(logging.Handler):
    # (x, y, ...) OR {x: a, y: b}
    T_ARGS = Union[tuple[Any, ...], Mapping[str, Any]]

    # (msg, args)
    T_MESSAGE = logging.LogRecord

    # {LEVEL: [(msg, args), ...]}
    T_MESSAGES = dict[str, list[T_MESSAGE]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._messages: LoggingHandler.T_MESSAGES = defaultdict(list)

    @property
    def messages(self) -> T_MESSAGES:
        """
        Contains the list of messages + arguments
        """
        return self._messages

    def reset(self) -> "LoggingHandler":
        self.acquire()
        try:
            self._messages.clear()
        finally:
            self.release()
        return self

    def emit(self, record: logging.LogRecord):
        self._messages[record.levelname.upper()].append(record)


class LoggingPatcher:
    __slots__ = "_logger", "_handler_cls", "_handler_instance", "_is_active"

    def __init__(self):
        self._logger: Optional[logging.Logger] = None
        self._handler_instance: LoggingHandler = LoggingHandler()
        self._is_active: bool = False

    @property
    def handler(self) -> LoggingHandler:
        return self._handler_instance

    @property
    def is_active(self) -> bool:
        return self._is_active

    def init(self, logger: logging.Logger) -> "LoggingPatcher":
        self._logger = logger
        return self

    def start(self) -> LoggingHandler.T_MESSAGES:
        if self._logger is None:
            raise RuntimeError("Logger was not configured")

        handler = self._handler_instance
        self._logger.addHandler(handler)
        self._is_active = True
        return self._handler_instance.messages

    def reset(self) -> None:
        self._handler_instance.reset()

    def stop(self) -> None:
        self._logger.removeHandler(self._handler_instance)
        self._is_active = False

    def __enter__(self) -> LoggingHandler.T_MESSAGES:
        return self.start()

    def __exit__(self, *_args) -> None:
        return self.stop()
