# Standard Libraries
import os

# Third-party Libraries

UPLOAD_FOLDER = "uploads"


def ensure_uploads_dir():
    """Create the uploads directory when needed (avoid side-effects at import)."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
