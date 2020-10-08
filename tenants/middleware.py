from tenant_schemas.middleware import BaseTenantMiddleware


class SaleorTenantMiddleware(BaseTenantMiddleware):
    EXCLUDED_PATHS = [
        "/prometheus/metrics"
    ]

    def process_request(self, request):
        if request.path in SaleorTenantMiddleware.EXCLUDED_PATHS:
            return
        return super().process_request(request)

    def get_tenant(self, model, hostname, request):
        return model.objects.get(domain_url=self.get_base_domain_url(hostname))

    def get_base_domain_url(self, hostname):
        domain_parts = hostname.split(".")
        tenant_label_parts = domain_parts[0].split("-")
        if len(tenant_label_parts) > 1:
            domain_parts[0] = tenant_label_parts[-1]
        return ".".join(domain_parts)
