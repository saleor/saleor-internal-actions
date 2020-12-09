from tenant_schemas.middleware import TenantMiddleware


class SaleorTenantMiddleware(TenantMiddleware):
    EXCLUDED_PATHS = ()

    def process_request(self, request):
        if request.path in SaleorTenantMiddleware.EXCLUDED_PATHS:
            return
        return super().process_request(request)
