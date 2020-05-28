from tests.settings import *  # noqa
from tenants.postgresql_backend.creation import TEST_DOMAIN

TENANT_APPS.append("tests.api.pagination")  # noqa: F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1", TEST_DOMAIN]

PATTERNS_IGNORED_IN_QUERY_CAPTURES: List[Union[Pattern, SimpleLazyObject]] = [
    lazy_re_compile(r"^SET\s+"),
    lazy_re_compile(r"^SELECT \"tenants_tenant\".\"id\",.+ FROM \"tenants_tenant\"\s+"),
]

DEFAULT_BACKUP_BUCKET_NAME = "testbackups"
