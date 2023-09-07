import datetime
import json
import logging
import os
from typing import Union

from django.conf import settings
from django.utils.encoding import force_str


def get_logging_config_dict(log_level: str, log_dir: str) -> dict:
    """
    Get Logging Config
    """

    log_class = "logging.handlers.RotatingFileHandler"
    if settings.DEBUG:
        logging_format = {
            "format": ("%(levelname)s [%(asctime)s] %(pathname)s " "%(lineno)d %(funcName)s " "\n \t %(message)s \n"),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    else:
        logging_format = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": (
                "%(levelname)s %(asctime)s %(pathname)s %(lineno)d " "%(funcName)s %(process)d %(thread)d %(message)s"
            ),
        }
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": logging_format,
            "simple": {"format": "%(levelname)s %(message)s"},
        },
        "handlers": {
            "null": {"level": "DEBUG", "class": "logging.NullHandler"},
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "simple",
            },
            "app": {
                "class": log_class,
                "formatter": "verbose",
                "filename": os.path.join(log_dir, "django.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 5,
                "encoding": "utf8",
            },
            "mysql": {
                "class": log_class,
                "formatter": "verbose",
                "filename": os.path.join(log_dir, "mysql.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 5,
                "encoding": "utf8",
            },
            "cel": {
                "class": log_class,
                "formatter": "verbose",
                "filename": os.path.join(log_dir, "celery.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "django": {"handlers": ["null"], "level": "INFO", "propagate": True},
            "django.server": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": True,
            },
            "django.request": {
                "handlers": ["app"],
                "level": "ERROR",
                "propagate": True,
            },
            "django.db.backends": {
                "handlers": ["mysql"],
                "level": log_level,
                "propagate": True,
            },
            "root": {"handlers": ["console"], "level": log_level, "propagate": True},
            "app": {"handlers": ["app"], "level": log_level, "propagate": True},
            "mysql": {"handlers": ["mysql"], "level": log_level, "propagate": True},
            "cel": {"handlers": ["cel"], "level": log_level, "propagate": True},
        },
    }


class DumpLog:
    """
    Dump Log to Str
    """

    def __init__(self, *args):
        self._args = args

    @property
    def args(self) -> tuple:
        new_args = list()
        for _arg in self._args:
            try:
                if isinstance(_arg, bytes):
                    new_args.append(_arg.decode())
                elif isinstance(_arg, Union[str, int]):
                    new_args.append(_arg)
                elif isinstance(_arg, Union[datetime.datetime, datetime.date]):
                    new_args.append(str(_arg))
                else:
                    new_args.append(json.dumps(_arg, ensure_ascii=False))
            except Exception:
                new_args.append(force_str(_arg))
        return tuple(new_args)


class LogLevelHandler:
    """
    Handler Log Level
    """

    def __init__(self, log, level: str):
        self.log = log
        self.level = level

    def __call__(self, msg, *args):
        args = DumpLog(*args).args
        func = getattr(self.log.logger, self.level)
        func(msg, *args)


class Log:
    """
    Log
    """

    def __init__(self, name):
        self.logger = logging.getLogger(name)

    def __getattr__(self, level: str):
        return LogLevelHandler(self, level)


logger = Log("app")
celery_logger = Log("cel")
mysql_logger = Log("mysql")
