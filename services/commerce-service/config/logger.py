import logging
import os
import sys
from typing import Optional


class AppLogger:
    _instance: Optional["AppLogger"] = None
    _logger: logging.Logger

    def __new__(cls) -> "AppLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self) -> None:
        log_level_str = os.getenv("APP_LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

        self._logger = logging.getLogger("commerce-service")
        self._logger.setLevel(log_level)

        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(log_level)
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    def _format(self, message: str, **kwargs) -> str:
        if kwargs:
            context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            return f"{message} | {context}"
        return message

    def info(self, message: str, **kwargs) -> None:
        self._logger.info(self._format(message, **kwargs))

    def debug(self, message: str, **kwargs) -> None:
        self._logger.debug(self._format(message, **kwargs))

    def warning(self, message: str, **kwargs) -> None:
        self._logger.warning(self._format(message, **kwargs))

    def error(self, message: str, **kwargs) -> None:
        self._logger.error(self._format(message, **kwargs))

    def critical(self, message: str, **kwargs) -> None:
        self._logger.critical(self._format(message, **kwargs))

    def exception(self, message: str, **kwargs) -> None:
        self._logger.exception(self._format(message, **kwargs))


logger = AppLogger()
