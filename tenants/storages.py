from urllib.parse import urljoin

from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.utils.encoding import filepath_to_uri
from storages.utils import safe_join
from tenant_schemas.storage import TenantStorageMixin

from saleor.core.storages import S3MediaStorage


class TenantAwareStorage(TenantStorageMixin):
    @property
    def tenant_domain(self):
        return connection.tenant.domain_url

    @property
    def tenant_location(self):
        try:
            return safe_join(self.location, self.tenant_domain)
        except AttributeError:
            return self.location


class TenantS3MediaStorage(TenantAwareStorage, S3MediaStorage):
    def url(self, name, parameters=None, expire=None):
        name = self._normalize_resource_name("media", self._clean_name(name))
        return "%s//%s/%s" % (
            self.url_protocol,
            self.tenant_domain,
            filepath_to_uri(name),
        )

    def _normalize_name(self, name):
        return self._normalize_resource_name(self.tenant_location, name)

    def _normalize_resource_name(self, location, name):
        try:
            return safe_join(location, name)
        except ValueError:
            raise SuspiciousOperation("Attempted access to '%s' denied." % name)


class TenantFileSystemStorage(TenantAwareStorage, FileSystemStorage):
    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        tennant_base_url = "{}/{}/".format(self.base_url, self.tenant_domain)
        url = filepath_to_uri(name)
        if url is not None:
            url = url.lstrip("/")
        return urljoin(tennant_base_url, url)
