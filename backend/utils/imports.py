# Standard Libraries
import os
import sys
import json
import time
import datetime

# Third-party Libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


UPLOAD_FOLDER = "uploads"
def ensure_uploads_dir():
    """Create the uploads directory when needed (avoid side-effects at import)."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
