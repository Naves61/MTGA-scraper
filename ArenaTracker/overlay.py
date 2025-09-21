import cv2
from typing import List, Optional


WINDOW_TITLE = "Arena Scraper Preview (green=card, red=title)"


def draw_boxes(
    frame,
    tiles,
    color_card=(0, 255, 0),
    color_title=(0, 0, 255),
    highlight_idx: Optional[int] = None,
    message: Optional[str] = None,
):
    canvas = frame.copy()
    for idx, t in enumerate(tiles):
        cur_color_card = color_card
        cur_color_title = color_title
        thickness = 2
        if highlight_idx is not None and idx == highlight_idx:
            cur_color_card = (0, 215, 255)
            cur_color_title = (0, 165, 255)
            thickness = 3
        cv2.rectangle(
            canvas,
            (t.rect.x, t.rect.y),
            (t.rect.x + t.rect.w, t.rect.y + t.rect.h),
            cur_color_card,
            thickness,
        )
        cv2.rectangle(
            canvas,
            (t.title.x, t.title.y),
            (t.title.x + t.title.w, t.title.y + t.title.h),
            cur_color_title,
            thickness,
        )
    if message:
        text = message.strip()
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        pad_x = 16
        pad_y = 10
        x1, y1 = 16, 16
        x2 = x1 + text_w + pad_x
        y2 = y1 + text_h + baseline + pad_y
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 0, 0), -1)
        cv2.putText(
            canvas,
            text,
            (x1 + pad_x // 2, y2 - baseline - pad_y // 2),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )
    return canvas


def show_overlay(
    frame,
    tiles,
    window: bool,
    *,
    highlight_idx: Optional[int] = None,
    message: Optional[str] = None,
    hold_ms: int = 1,
):
    if not window:
        return
    annotated = draw_boxes(
        frame,
        tiles,
        highlight_idx=highlight_idx,
        message=message,
    )
    cv2.imshow(WINDOW_TITLE, annotated)
    cv2.waitKey(max(1, hold_ms))


def close_overlay():
    try:
        cv2.destroyWindow(WINDOW_TITLE)
    except cv2.error:
        pass
