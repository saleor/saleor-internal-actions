from django.http import HttpResponseNotFound
from saleor.core.views import handle_404 as tenant_handle_404


def handle_404(request, exception=None):
    tenant = getattr(request, "tenant", None)
    if tenant is None:
        response = HttpResponseNotFound("No such tenant.", content_type="text/plain")
        response["Content-Length"] = len(response.content)
        return response
    return tenant_handle_404(request, exception=exception)
