import os

from dotenv import load_dotenv

# Load .env from backend dir
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DB_PATH = os.path.join(base_dir, "watchlist.db")
    UPLOAD_FOLDER = os.path.join(base_dir, "uploads")
    PORT = int(os.environ.get("PORT", 5001))
    DEFAULT_PAPER_CASH = 100_000.0
    
    # Agent Settings
    AGENT_ENABLED_DEFAULT = False
    AGENT_CONFIDENCE_FLOOR = float(os.environ.get("AGENT_CONFIDENCE_FLOOR", 0.18))
    
    # API Keys
    OPEN_ROUTER_API_KEY = os.environ.get("OPEN_ROUTER_API_KEY")
    TELEGRAM_HTTP_API_KEY = os.environ.get("TELEGRAM_HTTP_API_KEY")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
    ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")

config = Config()
