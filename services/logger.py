import logging
from logging.handlers import RotatingFileHandler
import os
from colorama import Fore, Style, init

init(autoreset=True)

class Logger:
    _logger = None

    @staticmethod
    def get_logger(name: str = "AI Log", log_file: str = "app.log") -> logging.Logger:
        if Logger._logger is None:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)

            # Custom color formatter for console
            class ColorFormatter(logging.Formatter):
                COLORS = {
                    logging.DEBUG: Fore.WHITE,
                    logging.INFO: Fore.GREEN,
                    logging.WARNING: Fore.YELLOW,
                    logging.ERROR: Fore.RED,
                    logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
                }

                def format(self, record):
                    color = self.COLORS.get(record.levelno, "")
                    message = super().format(record)
                    return color + message + Style.RESET_ALL

            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(ColorFormatter(
                '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))

            file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
            file_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
            logger.propagate = False

            Logger._logger = logger

        return Logger._logger
