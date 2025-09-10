from loguru import logger
import sys
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[2] / "bot.log"

logger.remove()
logger.add(sys.stderr, format="<green>{time}</green> | <level>{level}</level> | {message}")
logger.add(LOG_PATH, rotation="1 MB", retention=10, enqueue=True,
           format="{time} | {level} | {message}")

def get_logger():
    return logger
