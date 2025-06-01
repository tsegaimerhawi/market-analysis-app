import logging
from pathlib import Path

# Logs directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
print(log_dir / "app.log")
log_file = log_dir / "app.log"

# Formatter string
log_format = (
    "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)

# Configure logger
logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)

logger = logging.getLogger("my_project")
