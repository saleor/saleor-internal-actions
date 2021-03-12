from unittest import mock

import pytest
from django.db import connection 
from django.core.management import call_command

from saleor.account.models import User
from saleor.core.permissions import get_permissions

from tenants.management.commands import setadmin
from tenants.limits.errors import LimitReachedException

CMD = "setadmin"
ADMIN_EMAIL = "admin@example.com"

@pytest.fixture
def mocked_send_email():
    with mock.patch.object(setadmin, "send_password_email") as patched:
        yield patched

def test_create_new_admin_user(mocked_send_email):
    assert User.objects.count() == 0
    call_command(CMD, ADMIN_EMAIL)
    user = User.objects.get(email=ADMIN_EMAIL)
    assert_is_admin(user)
    mocked_send_email.assert_called_once()

def test_assign_admin_permissions_to_exisiting_user(mocked_send_email):
    user = User.objects.create(email=ADMIN_EMAIL)
    call_command(CMD, ADMIN_EMAIL)
    user.refresh_from_db()
    assert_is_admin(user)
    mocked_send_email.assert_called_once()


def test_fail_to_create_when_out_of_staff_user_limit(tenant_connection_keeper, mocked_send_email):
    connection.tenant.max_staff_user_count = 0
    connection.tenant.save()
    with pytest.raises(LimitReachedException):
        call_command(CMD, ADMIN_EMAIL)
    mocked_send_email.assert_not_called()


def test_skip_staff_user_limit_if_account_exists(tenant_connection_keeper, mocked_send_email):
    user = User.objects.create(email=ADMIN_EMAIL, is_staff=True)
    connection.tenant.max_staff_user_count = 1
    connection.tenant.save()

    call_command(CMD, ADMIN_EMAIL)
    user.refresh_from_db()
    assert_is_admin(user)
    mocked_send_email.assert_called_once()

def assert_is_admin(user):
    assert user.is_active
    assert user.is_staff
    assert user.password

    user_permissions = user.user_permissions.all()
    for permission in get_permissions():
        assert permission in user_permissions
