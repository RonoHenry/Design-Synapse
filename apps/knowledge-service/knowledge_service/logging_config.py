"""Logging configuration for knowledge service."""

import logging
import logging.config
from typing import Any, Dict


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""

    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "knowledge_service.log",
                "mode": "a",
            },
        },
        "loggers": {
            "knowledge_service": {
                "level": "DEBUG",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "httpx": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "sentence_transformers": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {"level": log_level, "handlers": ["console"]},
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"knowledge_service.{name}")
