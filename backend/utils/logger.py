import logging
from pathlib import Path

# Logs directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "app.log"

# Formatter string
log_format = (
    "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)

# Configure logger: INFO for console/file so third-party libs (e.g. yfinance) don't flood DEBUG
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)

logger = logging.getLogger("my_project")
logger.setLevel(logging.DEBUG)

# Silence noisy third-party DEBUG logs (yfinance, urllib3, etc.)
logging.getLogger("yfinance").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
