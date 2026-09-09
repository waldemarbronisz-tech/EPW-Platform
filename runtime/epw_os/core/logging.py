import logging
import sys

def get_logger(name: str = "EPW_OS") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(levelname)s     %(name)s:%(filename)s:%(lineno)d %(message)s'
        )
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

log = get_logger()
