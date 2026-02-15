"""
Logging utilities: colored console output when running in a TTY.
"""

import logging
import sys

# ANSI codes (safe to use; reset is always appended)
_RESET = "\033[0m"
_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",    # cyan
    logging.INFO: "\033[32m",     # green
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",    # red
}


class ColoredFormatter(logging.Formatter):
    """
    Formatter that adds ANSI colors to the level name when the output stream is a TTY.
    File handlers should use a plain Formatter (no color).
    """

    def __init__(self, fmt=None, datefmt=None, use_color=None):
        super().__init__(fmt, datefmt)
        if use_color is None:
            use_color = self._stderr_is_tty()
        self.use_color = use_color

    @staticmethod
    def _stderr_is_tty():
        try:
            return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()
        except Exception:
            return False

    def format(self, record):
        message = super().format(record)
        if self.use_color and record.levelno in _LEVEL_COLORS:
            return _LEVEL_COLORS[record.levelno] + message + _RESET
        return message


def setup_script_logging(
    log_format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_file=None,
):
    """
    Configure the root logger for scripts: colored console (when TTY) and optional file.
    If COLLIBRA_LOG_FILE env var is set, it overrides the log_file argument.
    """
    import os

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Remove existing handlers so we control console + file
    for h in root.handlers[:]:
        root.removeHandler(h)

    # Console: colored when TTY
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(ColoredFormatter(log_format, datefmt=datefmt))
    root.addHandler(console)

    # Optional file: no color
    path = log_file or os.environ.get("COLLIBRA_LOG_FILE")
    if path:
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format, datefmt=datefmt))
        root.addHandler(fh)
