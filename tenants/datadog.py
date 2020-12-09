import os
import logging


class DatadogInstaller:
    """
    Datadog APM agent for distributed tracing
    Note we cannot import anything from ddtrace otherwise it will be initialized
    It needs to be called as soon as possible due to monkey-patching starting
    as soon as imported.

    Configuration keys for the global tracer (a base datadog tracer that is used inside
    the Datadog opentracing tracer):
      https://docs.datadoghq.com/tracing/setup_overview/setup/python#configuration

    For Django support configuration:
      https://ddtrace.readthedocs.io/en/stable/integrations.html#django
    """

    SERVICE_NAME = "core"

    def __init__(
        self,
        *,
        agent_host: str,
        agent_port: int,
        project_version: str,
        variables: dict,
        logging_level: str,
        debug: bool
    ):
        self.agent_host = agent_host
        self.agent_port = agent_port

        self.project_version = project_version
        self.variables = variables

        self.logging_level = logging_level
        self.debug = debug

        self.logging_configuration: dict = variables["LOGGING"]
        self.installed_apps = variables["INSTALLED_APPS"]
        self.enabled_loggers = ("ddtrace.monkey", "ddtrace.api")

    def get_tracer_configuration(self) -> dict:
        cfg = {
            "agent_hostname": self.agent_host,
            "agent_port": self.agent_port,
            "debug": self.debug,
            "enabled": True,
        }
        return cfg

    def _patch_django_logging_configuration(self):
        # Force default logging until django configures it
        logging.basicConfig(level=self.logging_level)

        # Add datadog loggers onto Django configuration
        loggers_cfg = self.logging_configuration["loggers"]
        for logger_name in self.enabled_loggers:
            loggers_cfg[logger_name] = {
                "handlers": ["default"],
                "level": self.logging_level,
                "propagate": False,
            }

    def _patch_django_installed_apps(self):
        self.installed_apps.append("ddtrace.contrib.django")

    def _patch_environment_variable(self):
        # Set project version before importing DataDog tracer
        # as it will try to find this key during import
        os.environ["DD_VERSION"] = self.project_version

    def _initialize_datadog_opentracer(self):
        """
        For configuration details, refer to
        https://ddtrace.readthedocs.io/en/stable/advanced_usage.html#opentracing
        """
        import ddtrace.opentracer as dd_ot
        from ddtrace import patch_all

        # Patch available packages as integrations
        patch_all()

        # Set-up the opentracing tracer
        cfg = self.get_tracer_configuration()
        tracer = dd_ot.Tracer(self.SERVICE_NAME, config=cfg)
        dd_ot.set_global_tracer(tracer)
        return tracer

    def init(self):
        self._patch_django_logging_configuration()
        self._patch_django_installed_apps()
        self._patch_environment_variable()
        tracer = self._initialize_datadog_opentracer()
        return tracer
