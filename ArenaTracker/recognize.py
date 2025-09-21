import cv2, numpy as np
from typing import Optional, Dict
from config import MAX_DOTS
from store import lookup_card_by_ocr, cache_card_name, iter_art_cache, cache_art
from capture import hover_screenshot


def clean_text(s: str) -> str:
    s = s.strip().replace("\n", " ")
    for a, b in {"’": "'", "‘": "'", "“": '"', "”": '"', "—": "-", "–": "-"}.items():
        s = s.replace(a, b)
    return " ".join(s.split())


def ocr_title(img) -> str:
    import pytesseract

    txt = pytesseract.image_to_string(img, config="--psm 7 -l eng")
    return clean_text(txt)


def count_black_dots(dot_img) -> int:
    g = cv2.cvtColor(dot_img, cv2.COLOR_BGR2GRAY)
    g = cv2.medianBlur(g, 3)
    th = cv2.threshold(g, 60, 255, cv2.THRESH_BINARY_INV)[1]
    th = cv2.morphologyEx(
        th, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), 1
    )
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    owned = 0
    for c in cnts:
        area = cv2.contourArea(c)
        if 10 <= area <= 300:
            x, y, w, h = cv2.boundingRect(c)
            r = w / float(h + 1e-9)
            if 0.6 < r < 1.6:
                owned += 1
    return min(owned, MAX_DOTS)


def ahash(img) -> str:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, (8, 8), interpolation=cv2.INTER_AREA)
    m = g.mean()
    bits = (g > m).astype(np.uint8).flatten()
    val = 0
    for b in bits:
        val = (val << 1) | int(b)
    return f"{val:016x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def art_lookup(tile_img) -> Optional[Dict]:
    target = ahash(tile_img)
    best = None
    best_d = 999
    for ah, name, sid, uri in iter_art_cache():
        d = hamming(target, ah)
        if d < best_d:
            best_d = d
            best = {"name": name, "id": sid, "uri": uri}
    return best if best and best_d <= 5 else None


def resolve_name(frame, tile, use_hover: bool) -> Optional[Dict]:
    # 1) OCR on title band
    raw = ocr_title(tile.title.crop(frame)).strip()
    if raw:
        from scryfall import lookup_fuzzy

        info = lookup_fuzzy(raw)
        if info:
            cache_card_name(raw, info)
            return info
    # 2) Hover OCR (big preview)
    if use_hover:
        cx = tile.rect.x + tile.rect.w // 2
        cy = tile.rect.y + tile.rect.h // 2
        pop = hover_screenshot(cx, cy)
        raw2 = ocr_title(pop).strip()
        if raw2:
            from scryfall import lookup_fuzzy

            info2 = lookup_fuzzy(raw2)
            if info2:
                cache_card_name(raw2, info2)
                return info2
    # 3) Local art hash
    img = tile.rect.crop(frame)
    info3 = art_lookup(img)
    if info3:
        cache_art(ahash(img), info3)
        return info3
    return None
