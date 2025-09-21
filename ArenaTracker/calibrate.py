import json, cv2, numpy as np
from dataclasses import dataclass
from typing import List

import textwrap

from overlay import show_overlay
from config import CALIB_PATH


@dataclass
class ROI:
    x: int
    y: int
    w: int
    h: int

    def crop(self, im):
        return im[self.y : self.y + self.h, self.x : self.x + self.w]


@dataclass
class Tile:
    rect: ROI
    title: ROI
    dots: ROI


def _boxes_from_edges(frame):
    H, W = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 70, 170)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), 1)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        ar = w / (h + 1e-9)
        if area < 40000 or area > 300000:
            continue
        if 0.6 < ar < 0.9 and H * 0.12 < y < H * 0.92:
            boxes.append((x, y, w, h))
    # NMS
    boxes = sorted(boxes, key=lambda r: r[2] * r[3], reverse=True)
    kept = []

    def iou(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        x1 = max(ax, bx)
        y1 = max(ay, by)
        x2 = min(ax + aw, bx + bw)
        y2 = min(ay + ah, by + bh)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        union = aw * ah + bw * bh - inter
        return inter / union

    for b in boxes:
        if all(iou(b, k) < 0.2 for k in kept):
            kept.append(b)
        if len(kept) >= 12:
            break
    return kept


def detect_card_boxes(frame):
    """Detect potential card rectangles in the current frame."""
    return _boxes_from_edges(frame)


def _tile_from_box(box) -> Tile:
    x, y, w, h = box
    rect = ROI(x, y, w, h)
    t_h = int(h * 0.16)
    title = ROI(
        x + int(w * 0.06),
        y + h - t_h + int(t_h * 0.1),
        w - int(w * 0.12),
        t_h - int(t_h * 0.2),
    )
    d_h = max(12, int(h * 0.06))
    dots = ROI(x + int(w * 0.25), y + h - t_h - d_h - 2, int(w * 0.5), d_h)
    return Tile(rect, title, dots)


def calibrate(frame, preview: bool = False) -> List[Tile]:
    kept = _boxes_from_edges(frame)
    kept = sorted(kept, key=lambda r: (r[1], r[0]))
    if len(kept) >= 10:
        ys = [y for _, y, _, _ in kept]
        split = np.median(ys)
        row1 = sorted([b for b in kept if b[1] < split], key=lambda r: r[0])[:6]
        row2 = sorted([b for b in kept if b[1] >= split], key=lambda r: r[0])[:6]
        boxes = row1 + row2
        return [_tile_from_box(box) for box in boxes]

    if preview and kept:
        preview_tiles = [_tile_from_box(b) for b in kept]
        show_overlay(
            frame,
            preview_tiles,
            True,
            message=f"Calibration detected {len(preview_tiles)} boxes",
            hold_ms=900,
        )

    return _manual_calibration(frame, preview, detected_count=len(kept))


def _manual_calibration(frame, preview: bool, detected_count: int) -> List[Tile]:
    if detected_count >= 1:
        default_cards = min(12, max(6, detected_count))
    else:
        default_cards = 6

    print("Automatic calibration failed: not enough card rectangles detected.")

    prompt = (
        "Enter the number of cards visible (press Enter for "
        f"{default_cards}): "
    )
    try:
        raw = input(prompt)
    except EOFError:
        raw = ""
    raw = raw.strip()
    card_count = default_cards
    if raw:
        try:
            value = int(raw)
            if value >= 1:
                card_count = value
        except ValueError:
            pass

    message = textwrap.dedent(
        """
        Manual calibration controls:
          • Click the TOP-RIGHT corner, then the BOTTOM-LEFT corner for each card.
          • Proceed card by card, left-to-right, top-to-bottom.
          • Press 'u' to undo the last point, 'r' to reset, 'q' to abort.
          • After marking all cards, press Enter to confirm.
        """
    ).strip()
    print(message)

    boxes = _collect_card_boxes(frame, card_count)
    tiles = [_tile_from_box(box) for box in boxes]

    if preview:
        show_overlay(
            frame,
            tiles,
            True,
            message="Manual calibration complete",
            hold_ms=1100,
        )

    return tiles


def _collect_card_boxes(frame, card_count: int):
    window = "ArenaTracker – Manual calibration"
    base = frame.copy()
    points: List[tuple[int, int]] = []
    confirmed = False

    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    def draw(show_confirm: bool = False) -> None:
        display = base.copy()
        next_idx = len(points)
        card_idx = min(card_count, next_idx // 2 + 1)
        instruction = (
            f"Card {card_idx}/{card_count}: click top-right"
            if next_idx % 2 == 0 and next_idx < card_count * 2
            else f"Card {card_idx}/{card_count}: click bottom-left"
        )
        if next_idx >= card_count * 2:
            instruction = "All cards marked. Press Enter to confirm."
        status_lines = [
            instruction,
            "Press Enter to finish once all cards are marked.",
            "Keys: u=undo, r=reset, q=abort",
        ]
        y = 28
        for line in status_lines:
            cv2.putText(
                display,
                line,
                (18, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
                lineType=cv2.LINE_AA,
            )
            y += 30

        for idx, (px, py) in enumerate(points):
            label = "TR" if idx % 2 == 0 else "BL"
            cv2.circle(display, (px, py), 7, (57, 255, 20), -1)
            cv2.putText(
                display,
                f"{idx // 2 + 1}{label}",
                (px + 8, py - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (57, 255, 20),
                2,
                lineType=cv2.LINE_AA,
            )

        if show_confirm:
            cv2.putText(
                display,
                "Ready to save – press Enter",
                (18, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 220, 255),
                2,
                lineType=cv2.LINE_AA,
            )

        cv2.imshow(window, display)

    def on_mouse(event, x, y, *_args):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < card_count * 2:
            points.append((int(x), int(y)))
            draw(len(points) >= card_count * 2)

    cv2.setMouseCallback(window, on_mouse)
    draw()

    try:
        while True:
            key = cv2.waitKey(50) & 0xFF
            if key == ord("u"):
                if points:
                    points.pop()
                    draw(len(points) >= card_count * 2)
            elif key == ord("r"):
                if points:
                    points.clear()
                    draw()
            elif key == ord("q") or key == 27:
                raise RuntimeError("Manual calibration aborted by user.")
            elif key in (13, ord(" ")):
                if len(points) >= card_count * 2:
                    confirmed = True
                    break
            if len(points) >= card_count * 2:
                draw(True)
    finally:
        cv2.destroyWindow(window)

    if not confirmed or len(points) < card_count * 2:
        raise RuntimeError("Manual calibration incomplete.")

    boxes = []
    for idx in range(card_count):
        p_tr = points[idx * 2]
        p_bl = points[idx * 2 + 1]
        x1 = min(p_tr[0], p_bl[0])
        x2 = max(p_tr[0], p_bl[0])
        y1 = min(p_tr[1], p_bl[1])
        y2 = max(p_tr[1], p_bl[1])
        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            raise RuntimeError("Invalid card region selected; please retry calibration.")
        boxes.append((x1, y1, w, h))

    boxes.sort(key=lambda r: (r[1], r[0]))
    return boxes


def save_calibration(tiles: List[Tile]):
    data = {
        "tiles": [
            {"rect": vars(t.rect), "title": vars(t.title), "dots": vars(t.dots)}
            for t in tiles
        ]
    }
    CALIB_PATH.write_text(json.dumps(data))


def load_calibration() -> List[Tile]:
    d = json.loads(CALIB_PATH.read_text())
    toROI = lambda r: ROI(r["x"], r["y"], r["w"], r["h"])
    return [
        Tile(toROI(t["rect"]), toROI(t["title"]), toROI(t["dots"])) for t in d["tiles"]
    ]


def layout_matches(frame, tiles: List[Tile], min_matches: int = 10, iou_threshold: float = 0.55) -> bool:
    """Check whether the expected 2x6 grid of cards is visible."""

    boxes = detect_card_boxes(frame)
    if not boxes:
        return False

    def rect_iou(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        x1 = max(ax, bx)
        y1 = max(ay, by)
        x2 = min(ax + aw, bx + bw)
        y2 = min(ay + ah, by + bh)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        union = aw * ah + bw * bh - inter
        if union <= 0:
            return 0.0
        return inter / union

    matches = 0
    for tile in tiles:
        expected = (tile.rect.x, tile.rect.y, tile.rect.w, tile.rect.h)
        if any(rect_iou(expected, b) >= iou_threshold for b in boxes):
            matches += 1
    needed = min(len(tiles), max(0, min_matches))
    return matches >= needed
