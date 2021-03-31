from django.conf import settings
from django.core.management import BaseCommand
from django.db import connection, transaction

from saleor.account.models import User
from saleor.account.notifications import send_set_password_notification
from saleor.core.permissions import get_permissions
from saleor.plugins.manager import get_plugins_manager

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

        protocol = "https" if settings.ENABLE_SSL else "http"
        domain = connection.tenant.domain_url
        redirect_url = f"{protocol}://{domain}/dashboard/new-password/"
        send_set_password_notification(
            redirect_url, user, manager=get_plugins_manager(), staff=True
        )

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
