import time, hashlib, cv2
from typing import List
from config import DATA_DIR, LOG_PATH, CALIB_PATH, PAGE_SETTLE_SEC, CSV_PATH
from capture import bring_front, screenshot, mouse_safe
from calibrate import (
    calibrate,
    save_calibration,
    load_calibration,
    Tile,
    layout_matches,
)
from recognize import resolve_name, count_black_dots
from store import upsert_collection, export_csv
from overlay import show_overlay, close_overlay


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


def prompt_to_resume() -> bool:
    import tkinter as tk

    root = tk.Tk()
    root.title("Arena Tracker – Attention")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    message = (
        "The expected 2x6 card layout is obstructed.\n"
        "Clear the view, then press Retry to scan again or Abort to stop."
    )
    tk.Label(root, text=message, padx=20, pady=15, justify="center").pack()

    result = {"choice": "abort"}

    def choose(value: str):
        result["choice"] = value
        root.destroy()

    button_frame = tk.Frame(root, pady=10)
    button_frame.pack()
    tk.Button(button_frame, text="Retry", width=12, command=lambda: choose("retry")).pack(
        side=tk.LEFT, padx=6
    )
    tk.Button(
        button_frame,
        text="Abort",
        width=12,
        command=lambda: choose("abort"),
        bg="#c0392b",
        fg="white",
        activebackground="#922b21",
        activeforeground="white",
    ).pack(side=tk.LEFT, padx=6)

    root.protocol("WM_DELETE_WINDOW", lambda: choose("abort"))
    root.mainloop()
    return result["choice"] == "retry"


def ensure_layout(frame, tiles: List[Tile], preview: bool):
    if layout_matches(frame, tiles):
        return frame

    log("Card grid obstructed. Waiting for user intervention…")
    show_overlay(frame, tiles, preview)

    while True:
        if not prompt_to_resume():
            return None
        bring_front()
        time.sleep(0.5)
        mouse_safe()
        time.sleep(0.15)
        frame = screenshot()
        show_overlay(frame, tiles, preview)
        if layout_matches(frame, tiles):
            log("Card grid restored. Resuming.")
            return frame


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
    try:
        while True:
            mouse_safe()
            time.sleep(0.15)
            frame = screenshot()
            frame = ensure_layout(frame, tiles, preview)
            if frame is None:
                log("User aborted after obstruction. Stopping.")
                break
            sig = page_sig(frame, tiles)
            if first is None:
                first = sig
            if sig in seen and sig == first and page_idx > 0:
                log("Detected loop to first page. Stopping.")
                break
            seen.add(sig)

            show_overlay(frame, tiles, preview)

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
    finally:
        if preview:
            close_overlay()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--recalibrate", action="store_true")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--hover-ocr", action="store_true")
    args = p.parse_args()
    run(recalibrate=args.recalibrate, preview=args.preview, hover_ocr=args.hover_ocr)
