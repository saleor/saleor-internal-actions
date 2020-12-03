import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration


__all__ = ["CloudSentry"]


class CloudSentry:
    __slots__ = ["project_version", "_dsn"]

    def __init__(self, project_version: str, dsn: str):
        self.project_version = project_version
        self._dsn = dsn

    def before_send(self, event: dict, _hint: dict) -> dict:
        event["tags"] = {"version": self.project_version}
        return event

    def init(self):
        return sentry_sdk.init(
            self._dsn,
            integrations=[CeleryIntegration(), DjangoIntegration()],
            before_send=self.before_send,
        )
