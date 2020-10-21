import tempfile
import logging
from django.core.management import CommandError
from django.db import connection

from .restore_tenant import Command as RestoreCommand
from .backup_tenant import run_dump_data

logger = logging.getLogger(__name__)


class Command(RestoreCommand):
    @staticmethod
    def _create_recovery_dump(schema_name):
        recovery_dump_filename = tempfile.NamedTemporaryFile(delete=False, mode="w+t").name
        run_dump_data(schema_name, recovery_dump_filename)
        return recovery_dump_filename

    def rollback_tenant(self):
        schema_name = connection.tenant.schema_name
        backup_sql_dump_filename = self._manager.schema_path
        recovery_dump_filename = self._create_recovery_dump(schema_name)

        try:
            self._drop_schema(schema_name)
            self._execute_sql_dump(backup_sql_dump_filename)
        except Exception as exc:
            logging.exception("Database rollback failed!, trying to recover...")
            self._drop_schema(schema_name)
            self._execute_sql_dump(recovery_dump_filename)
            raise CommandError(repr(exc))

        self._run_media_restore()

    def handle(self, *_, **options):
        self.prepare_for_restore(**options)
        self.rollback_tenant()
