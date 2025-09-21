import json, cv2, numpy as np
from dataclasses import dataclass
from typing import List
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


def calibrate(frame) -> List[Tile]:
    kept = _boxes_from_edges(frame)
    if len(kept) < 10:
        raise RuntimeError("Calibration failed: not enough card rectangles.")
    kept = sorted(kept, key=lambda r: (r[1], r[0]))
    ys = [y for _, y, _, _ in kept]
    split = np.median(ys)
    row1 = sorted([b for b in kept if b[1] < split], key=lambda r: r[0])[:6]
    row2 = sorted([b for b in kept if b[1] >= split], key=lambda r: r[0])[:6]
    boxes = row1 + row2
    tiles = []
    for (x, y, w, h) in boxes:
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
        tiles.append(Tile(rect, title, dots))
    return tiles


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
