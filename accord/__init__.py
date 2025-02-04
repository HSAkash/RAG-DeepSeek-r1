import os
import sys
from loguru import logger

# Define log directory and file
log_dir = "logs"
log_filepath = os.path.join(log_dir, "accord_logs.log")
os.makedirs(log_dir, exist_ok=True)

# Remove default handler to avoid duplicate logs
logger.remove()

# Add log handlers
logger.add(
    log_filepath,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

logger.info("welcome to accord!")
