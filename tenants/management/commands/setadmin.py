from django.core.management import BaseCommand
from django.utils.crypto import get_random_string

from saleor.account.models import User
from saleor.core.permissions import get_permissions

from tenants.emails import send_password_email


class Command(BaseCommand):
    help = "Set admin account"

    def add_arguments(self, parser):
        parser.add_argument(
            "admin_email", type=str, metavar="ADMIN_EMAIL", help="Admin email address"
        )

    def handle(self, *args, **options):
        email = options["admin_email"]
        user = self._ger_or_create_user(email)
        self._assign_admin_permissions(user)
        password = self._set_random_password(user)
        send_password_email(user, password)

    @staticmethod
    def _ger_or_create_user(email):
        user, _ = User.objects.get_or_create(email=email)
        return user

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
