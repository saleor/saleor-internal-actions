from typing import List

from saleor.account.models import User
from saleor.channel.models import Channel
from saleor.order.models import Order


def create_orders(how_many: int, channel: Channel = None) -> List[Order]:
    if channel is None:
        channel = Channel.objects.create(name="PLN", slug="pln", currency_code="pln")
    return Order.objects.bulk_create(
        [Order(channel=channel, token=str(i)) for i in range(how_many)]
    )


def create_users(how_many, **defaults):
    defaults.setdefault("first_name", "first")
    defaults.setdefault("last_name", "first")

    # Set invalid default password hash, will always refuse login by default
    defaults.setdefault("password", "!invalid")

    return User.objects.bulk_create(
        [User(email=f"dummy+{i}@test", **defaults) for i in range(how_many)]
    )
