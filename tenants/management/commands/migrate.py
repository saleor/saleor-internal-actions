import sys

from django.core.management import CommandError, call_command
from django.core.management.commands.migrate import Command as BaseMigrateCommand
from tenant_schemas.utils import get_public_schema_name


class Command(BaseMigrateCommand):
    @staticmethod
    def is_called_from_tests() -> bool:
        return getattr(sys, "_called_from_test", False)

    def handle(self, *args, **options):
        """Migrate the schemas if ran under pytest. Does nothing otherwise.

        This command is only used for running the Saleor tests effectively to
        wrap the whole django logic.
        """
        if not self.is_called_from_tests():
            raise CommandError(
                "Command 'migrate' is disabled. Use migrate_schemas instead."
            )

        call_command("migrate_schemas", schema_name=get_public_schema_name(), **options)
