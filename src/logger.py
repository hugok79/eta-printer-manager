import logging
import os
from pathlib import Path


def setup_logger():
    # Saves the log file to the user's cache directory
    log_dir = Path.home() / ".cache" / "eta-printer-manager"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
    except Exception:
        log_file = "/tmp/eta-printer-manager.log"

    log = logging.getLogger("eta_printer_manager")
    log.setLevel(logging.DEBUG)

    if not log.handlers:
        # Log Format: [Date Time] [LEVEL] [File:Line] - Message
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 1. File Handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)

        # 2. Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        log.addHandler(console_handler)

    return log


# Defines 'logger' variable at the module level
logger = setup_logger()