import sqlite3, time, csv
from pathlib import Path
from typing import Optional, Dict, Iterable, Tuple
from config import DB_PATH, CSV_PATH


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """
    CREATE TABLE IF NOT EXISTS card_map(
      ocr_name TEXT PRIMARY KEY, name TEXT, scryfall_id TEXT, uri TEXT, set_code TEXT, ts INT
    )"""
    )
    conn.execute(
        """
    CREATE TABLE IF NOT EXISTS art_map(
      ahash TEXT PRIMARY KEY, name TEXT, scryfall_id TEXT, uri TEXT, ts INT
    )"""
    )
    conn.execute(
        """
    CREATE TABLE IF NOT EXISTS collection(
      name TEXT PRIMARY KEY, count INT, scryfall_id TEXT, uri TEXT, ts INT
    )"""
    )
    return conn


def cache_card_name(ocr_name: str, info: Dict):
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO card_map(ocr_name,name,scryfall_id,uri,set_code,ts)
                    VALUES(?,?,?,?,?,?)""",
        (
            ocr_name,
            info.get("name"),
            info.get("id"),
            info.get("uri"),
            info.get("set"),
            int(time.time()),
        ),
    )
    conn.commit()


def lookup_card_by_ocr(ocr_name: str) -> Optional[Dict]:
    conn = db()
    cur = conn.execute("SELECT name,scryfall_id,uri FROM card_map WHERE ocr_name=?", (ocr_name,))
    r = cur.fetchone()
    return {"name": r[0], "id": r[1], "uri": r[2]} if r else None


def cache_art(ahash: str, info: Dict):
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO art_map(ahash,name,scryfall_id,uri,ts)
                    VALUES(?,?,?,?,?)""",
        (ahash, info.get("name"), info.get("id"), info.get("uri"), int(time.time())),
    )
    conn.commit()


def iter_art_cache():
    conn = db()
    return conn.execute("SELECT ahash,name,scryfall_id,uri FROM art_map").fetchall()


def upsert_collection(name: str, count: int, info: Optional[Dict]):
    conn = db()
    sid = info.get("id") if info else None
    uri = info.get("uri") if info else None
    conn.execute(
        """INSERT INTO collection(name,count,scryfall_id,uri,ts)
           VALUES(?,?,?,?,?)
           ON CONFLICT(name) DO UPDATE SET
             count=excluded.count,
             scryfall_id=COALESCE(excluded.scryfall_id, collection.scryfall_id),
             uri=COALESCE(excluded.uri, collection.uri),
             ts=excluded.ts""",
        (name, count, sid, uri, int(time.time())),
    )
    conn.commit()


def export_csv():
    conn = db()
    rows = conn.execute(
        "SELECT name,count,scryfall_id,uri FROM collection ORDER BY name COLLATE NOCASE"
    ).fetchall()
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Card Name", "Owned Copies", "Scryfall ID", "Scryfall URI"])
        for r in rows:
            w.writerow(r)
