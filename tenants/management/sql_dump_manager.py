from django.db import connection

from tenants.management.gzip_dump_manager import TenantDump


class SqlManager:
    def __init__(self, sql_dump_filename: str):
        with open(sql_dump_filename, encoding="utf-8") as dump_fh:
            self.sql_dump = dump_fh.read()
        self.sql_dump_filename = sql_dump_filename

    @staticmethod
    def _replace_dump_schema(dump: str, source_schema: str, target_schema: str):
        replaceable = [
            'CREATE SCHEMA "{schema_name}"',
            'ALTER SCHEMA "{schema_name}"',
            'CREATE TABLE "{schema_name}".',
            'OWNED BY "{schema_name}".',
            'SET DEFAULT "nextval"(\'"{schema_name}".',
            'COPY "{schema_name}".',
            'pg_catalog.setval(\'"{schema_name}".',
            'ON "{schema_name}".',
            'CREATE SEQUENCE "{schema_name}".',
            'ALTER SEQUENCE "{schema_name}".',
            'ALTER TABLE "{schema_name}".',
            'ALTER TABLE ONLY "{schema_name}".',
            'REFERENCES "{schema_name}".',
        ]
        for r in replaceable:
            dump = dump.replace(
                r.format(schema_name=source_schema), r.format(schema_name=target_schema)
            )
        return dump

    def update(self, source_schema: str, target_schema: str):
        dump = self._replace_dump_schema(self.sql_dump, source_schema, target_schema)
        with open(self.sql_dump_filename, "wt", encoding="utf-8") as f:
            f.write(dump)
