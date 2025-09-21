from pathlib import Path

# All outputs in a visible folder on Desktop
BASE_DIR = Path.home() / "Desktop" / "ArenaTracker"
DATA_DIR = BASE_DIR / "data"
FRAMES_DIR = DATA_DIR / "frames"
LOG_PATH = DATA_DIR / "run.log"
CSV_PATH = DATA_DIR / "collection.csv"
DB_PATH = DATA_DIR / "cache.sqlite3"
CALIB_PATH = DATA_DIR / "calibration.json"

# Tunables
FUZZY_NAME_CUTOFF = 80
MAX_DOTS = 4
PAGE_SETTLE_SEC = 0.40
HOVER_DELAY_SEC = 0.25
