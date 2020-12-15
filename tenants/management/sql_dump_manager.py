import os

from django.db import connection

from tenants.management.gzip_dump_manager import TenantDump


class SqlManager:
    def __init__(self, sql_dump_filename: str, source_schema: str, target_schema: str):
        self.sql_dump_filename = sql_dump_filename
        replace_template = [
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
        self.replace_from = list(map(lambda s: s.format(schema_name=source_schema), replace_template))
        self.replace_to = list(map(lambda s: s.format(schema_name=target_schema), replace_template))

    def _replace(self, line: str):
        if line == "\n" or line == "" or line.startswith("--"):
            return line
        for i, s in enumerate(self.replace_from):
            if s in line:
                line = line.replace(s, self.replace_to[i])
        return line

    def update(self):
        temp_out_filename = f"{self.sql_dump_filename}_tmp"
        with open(temp_out_filename, "wt", encoding="utf-8") as out_fh:
            for line in open(self.sql_dump_filename, encoding="utf-8"):
                replaced = self._replace(line)
                out_fh.write(replaced)
        os.remove(self.sql_dump_filename)
        os.rename(temp_out_filename, self.sql_dump_filename)
