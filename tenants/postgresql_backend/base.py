from tenant_schemas.postgresql_backend.base import (
    DatabaseWrapper as BaseDatabaseWrapper,
)

from .creation import DatabaseCreation


class DatabaseWrapper(BaseDatabaseWrapper):
    """Wrap the third party's wrap of the postgres backend for psycopg2.

    Add additional logic for creating test databases.
    """

    creation_class = DatabaseCreation
