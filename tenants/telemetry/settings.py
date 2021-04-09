import os


def configure_metric_exporter_logging(loggers):
    cfg = {
        "handlers": ["default"],
        "level": os.environ.get("OPTL_LOG_LEVEL", "INFO"),
        "propagate": False,
    }
    loggers["dogstatsd_metric_exporter.queue"] = cfg
    loggers["dogstatsd_metric_exporter.exporter"] = cfg
