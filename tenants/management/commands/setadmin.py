from django.core.management import BaseCommand
from django.db import connection, transaction
from django.utils.crypto import get_random_string

from saleor.account.models import User
from saleor.core.permissions import get_permissions

from tenants.emails import send_password_email
from tenants.limits.errors import LimitReachedException


class Command(BaseCommand):
    help = "Set admin account"

    def add_arguments(self, parser):
        parser.add_argument(
            "admin_email", type=str, metavar="ADMIN_EMAIL", help="Admin email address"
        )

    def handle(self, *args, **options):
        email = options["admin_email"]
        with transaction.atomic():
            user = self._get_or_create_user(email)
            self._assign_admin_permissions(user)
            password = self._set_random_password(user)
        send_password_email(user, password)

    @classmethod
    def _get_or_create_user(cls, email):
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            pass

        cls._check_staff_users_limit()
        return User.objects.create(email=email)

    @staticmethod
    def _check_staff_users_limit():
        maximum_count = connection.tenant.max_staff_user_count
        if maximum_count < 0:
            return

        current = User.objects.filter(is_staff=True).count()
        if current >= maximum_count:
            raise LimitReachedException(resource_plural="Staff users", maximum_count=maximum_count, current=current)

    @staticmethod
    def _assign_admin_permissions(user):
        user.is_active = True
        user.is_staff = True
        user.user_permissions.add(*get_permissions())
        user.save()

    @staticmethod
    def _set_random_password(user):
        password = get_random_string()
        user.set_password(password)
        user.save()
        return password
