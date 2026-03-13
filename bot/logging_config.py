"""
Structured logging configuration for the trading bot.
Outputs to both console (colored) and rotating log file.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

# ANSI color codes for terminal output
COLORS = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[35m",  # Magenta
    "RESET": "\033[0m",
}


class ColoredFormatter(logging.Formatter):
    """Formatter that adds ANSI colors to log level names in terminal output."""

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = COLORS.get(levelname, COLORS["RESET"])
        record.levelname = f"{color}{levelname:<8}{COLORS['RESET']}"
        return super().format(record)


class PlainFormatter(logging.Formatter):
    """Plain formatter for file output (no ANSI codes)."""
    pass


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure and return the root logger for the trading bot.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).

    Returns:
        Configured logger instance.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("trading_bot")
    logger.setLevel(numeric_level)


    if logger.handlers:
        return logger
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_fmt = ColoredFormatter(
        fmt="%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)

    
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG to file
    file_fmt = PlainFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger