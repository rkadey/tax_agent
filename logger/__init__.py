import logging
import os
from from_root import from_root
from datetime import datetime

LOG_FILE = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"

log_dir = "logs"

logs_path = os.path.join(from_root(), log_dir, LOG_FILE)

os.makedirs(log_dir, exist_ok=True)


logger = logging.getLogger("custom_logger")
logger.setLevel(logging.INFO)

logger.propagate = False

# File handler
file_handler = logging.FileHandler(logs_path)
file_handler.setFormatter(logging.Formatter(
    "[ %(asctime)s ] %(name)s - %(levelname)s - %(message)s"
))

logger.addHandler(file_handler)