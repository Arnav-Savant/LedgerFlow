import os
import sys
import traceback
from datetime import datetime
from typing import Optional


_LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}


class AppLogger:
    _instance: Optional["AppLogger"] = None

    def __new__(cls) -> "AppLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._min_level = _LOG_LEVELS.get(
                os.getenv("APP_LOG_LEVEL", "INFO").upper(), 20
            )
        return cls._instance

    def _emit(self, level: str, message: str, **kwargs) -> None:
        if _LOG_LEVELS.get(level, 0) < self._min_level:
            return
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        line = f"{now} | {level:<8} | payment-service | {message}"
        if kwargs:
            line += " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
        print(line, file=sys.stderr, flush=True)

    def debug(self, message: str, **kwargs) -> None:
        self._emit("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self._emit("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._emit("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._emit("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self._emit("CRITICAL", message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        self._emit("ERROR", message, **kwargs)
        print(traceback.format_exc(), file=sys.stderr, flush=True)


logger = AppLogger()
