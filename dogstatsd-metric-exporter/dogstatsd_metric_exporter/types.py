from typing import Union

T_TAGS = tuple[str, ...]
T_NUMBER = Union[int, float]

# - A packet contains a list of strings to join
# - A batch contains a list of packets
T_PACKET = str
T_BATCH = list[T_PACKET]

NUMBER_TYPES = (int, float)
