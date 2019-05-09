from tenant_schemas.test.client import TenantClient as BaseTenantClient


class TenantClient(BaseTenantClient):
    def options(self, path, data="", **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = self.tenant.domain_url

        return super(TenantClient, self).options(path, data, **extra)
