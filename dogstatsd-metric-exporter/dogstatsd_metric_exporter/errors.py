from typing import Type

from opentelemetry.sdk.metrics import Aggregator


class BaseDogStatsDException(BaseException):
    def __init__(self, message: str, *args):
        self.message = message
        super().__init__(message, *args)


class UnsupportedAggregator(BaseDogStatsDException):
    MESSAGE = "Received an unsupported metric aggregation"

    def __init__(self, aggregator_type: Type[Aggregator]):
        super().__init__(self.MESSAGE, aggregator_type)


class UnsupportedValueType(BaseDogStatsDException):
    MESSAGE = "Received an unsupported value type"

    def __init__(self, value: type):
        super().__init__(self.MESSAGE, value)


class TooLongRecord(BaseDogStatsDException):
    MESSAGE = "Record is exceeding the max length that can be safely sent (%d)"

    def __init__(self, record: str, max_length: int):
        super().__init__(self.MESSAGE % max_length, record)
