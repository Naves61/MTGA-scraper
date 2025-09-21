import cv2
from typing import List


WINDOW_TITLE = "Arena Scraper Preview (green=card, red=title)"


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


def show_overlay(frame, tiles, window: bool):
    if not window:
        return
    annotated = draw_boxes(frame, tiles)
    cv2.imshow(WINDOW_TITLE, annotated)
    cv2.waitKey(1)


def close_overlay():
    try:
        cv2.destroyWindow(WINDOW_TITLE)
    except cv2.error:
        pass
