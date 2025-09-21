import time, hashlib, cv2
from pathlib import Path
from typing import List, Tuple
from config import DATA_DIR, LOG_PATH, CALIB_PATH, PAGE_SETTLE_SEC, CSV_PATH
from capture import bring_front, screenshot, mouse_safe
from calibrate import calibrate, save_calibration, load_calibration, Tile
from recognize import resolve_name, count_black_dots
from store import upsert_collection, export_csv
from overlay import show_and_save


def log(msg: str):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def page_sig(frame, tiles: List[Tile]) -> str:
    roi = tiles[0].title.crop(frame)
    roi = cv2.resize(roi, (64, 16), interpolation=cv2.INTER_AREA)
    return hashlib.sha1(roi.tobytes()).hexdigest()[:16]


def next_page():
    import pyautogui

    pyautogui.press("right")


def run(recalibrate: bool = False, preview: bool = False, hover_ocr: bool = False):
    bring_front()
    time.sleep(0.5)
    frame = screenshot()

    if recalibrate or not CALIB_PATH.exists():
        log("Calibrating (edge-based)…")
        tiles = calibrate(frame)
        save_calibration(tiles)
        log(f"Saved calibration to {CALIB_PATH}")
    else:
        tiles = load_calibration()

    seen = set()
    first = None
    page_idx = 0
    looped = False

    while True:
        mouse_safe()
        time.sleep(0.15)
        frame = screenshot()
        sig = page_sig(frame, tiles)
        if first is None:
            first = sig
        if sig in seen and sig == first and page_idx > 0:
            log("Detected loop to first page. Stopping.")
            break
        seen.add(sig)

        show_and_save(frame, tiles, page_idx, window=preview)

        # Process
        for t in tiles:
            info = resolve_name(frame, t, use_hover=hover_ocr)
            name = info["name"] if info else ""
            owned = count_black_dots(t.dots.crop(frame))
            if name:
                upsert_collection(name, owned, info)
        export_csv()
        log(f"Processed page {page_idx}. CSV at {CSV_PATH}")

        next_page()
        time.sleep(PAGE_SETTLE_SEC)
        page_idx += 1


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--recalibrate", action="store_true")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--hover-ocr", action="store_true")
    args = p.parse_args()
    run(recalibrate=args.recalibrate, preview=args.preview, hover_ocr=args.hover_ocr)
