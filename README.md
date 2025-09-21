# ArenaTracker

Toolkit for extracting a player's MTG Arena collection using screen captures, OCR, and Scryfall lookups.

## Project Layout

```
ArenaTracker/
  requirements.txt
  main.py
  config.py
  capture.py
  calibrate.py
  recognize.py
  scryfall.py
  store.py
  overlay.py
```

## Installation

```bash
cd ~/Desktop
python3 -m venv venv && source venv/bin/activate
# macOS: install Tesseract once
brew install tesseract
# If you see LibreSSL warnings, pin urllib3<2
pip install -r ArenaTracker/requirements.txt
```

## Usage

```bash
source ~/Desktop/venv/bin/activate   # if not already
python ~/Desktop/ArenaTracker/main.py --recalibrate --preview --hover-ocr
```

* Mouse is parked to avoid the hover overlay during captures; if `--hover-ocr` is set, the script briefly hovers a tile only when needed, then parks again.
* Green/red boxes are shown in the preview window and saved to `~/Desktop/ArenaTracker/data/frames/`.
* Output CSV: `~/Desktop/ArenaTracker/data/collection.csv`.
* Logs: `~/Desktop/ArenaTracker/data/run.log`.
* Cache DB: `~/Desktop/ArenaTracker/data/cache.sqlite3`.
* Calibration is stored and reused until you pass `--recalibrate`.
