import cv2
from pathlib import Path
from typing import List, Tuple
from config import FRAMES_DIR


def draw_boxes(frame, tiles, color_card=(0, 255, 0), color_title=(0, 0, 255)):
    canvas = frame.copy()
    for t in tiles:
        cv2.rectangle(
            canvas,
            (t.rect.x, t.rect.y),
            (t.rect.x + t.rect.w, t.rect.y + t.rect.h),
            color_card,
            2,
        )
        cv2.rectangle(
            canvas,
            (t.title.x, t.title.y),
            (t.title.x + t.title.w, t.title.y + t.title.h),
            color_title,
            2,
        )
    return canvas


def show_and_save(frame, tiles, page_idx: int, window: bool):
    annotated = draw_boxes(frame, tiles)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(FRAMES_DIR / f"page_{page_idx:04d}.png"), annotated)
    if window:
        cv2.imshow("Arena Scraper Preview (green=card, red=title)", annotated)
        cv2.waitKey(1)
