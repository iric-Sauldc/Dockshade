import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "dockshade.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name   TEXT NOT NULL,
                command     TEXT NOT NULL,
                ran_at      TEXT NOT NULL,
                container   TEXT NOT NULL DEFAULT 'kali'
            );
            CREATE TABLE IF NOT EXISTS favorites (
                tool_name   TEXT PRIMARY KEY,
                added_at    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notes (
                tool_name   TEXT PRIMARY KEY,
                content     TEXT NOT NULL DEFAULT '',
                updated_at  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tool_status (
                tool_name    TEXT PRIMARY KEY,
                installed    INTEGER NOT NULL DEFAULT 0,
                last_checked TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS progress (
                tool_name  TEXT PRIMARY KEY,
                times_used INTEGER NOT NULL DEFAULT 0,
                last_used  TEXT
            );
        """)

def add_history(tool_name, command, container="kali"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO history (tool_name,command,ran_at,container) VALUES (?,?,?,?)",
            (tool_name, command, datetime.now().isoformat(timespec="seconds"), container)
        )

def get_history(tool_name=None, limit=50):
    with get_conn() as conn:
        if tool_name:
            rows = conn.execute(
                "SELECT * FROM history WHERE tool_name=? ORDER BY ran_at DESC LIMIT ?",
                (tool_name, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM history ORDER BY ran_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]

def clear_history():
    with get_conn() as conn:
        conn.execute("DELETE FROM history")

def toggle_favorite(tool_name):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM favorites WHERE tool_name=?", (tool_name,)
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM favorites WHERE tool_name=?", (tool_name,))
            return False
        conn.execute(
            "INSERT INTO favorites (tool_name,added_at) VALUES (?,?)",
            (tool_name, datetime.now().isoformat(timespec="seconds"))
        )
        return True

def get_favorites():
    with get_conn() as conn:
        rows = conn.execute("SELECT tool_name FROM favorites").fetchall()
    return {r["tool_name"] for r in rows}

def get_note(tool_name):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT content FROM notes WHERE tool_name=?", (tool_name,)
        ).fetchone()
    return row["content"] if row else ""

def save_note(tool_name, content):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO notes (tool_name,content,updated_at) VALUES (?,?,?)
            ON CONFLICT(tool_name) DO UPDATE SET
                content=excluded.content, updated_at=excluded.updated_at
        """, (tool_name, content, datetime.now().isoformat(timespec="seconds")))

def update_tool_status(tool_name, installed):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO tool_status (tool_name,installed,last_checked) VALUES (?,?,?)
            ON CONFLICT(tool_name) DO UPDATE SET
                installed=excluded.installed, last_checked=excluded.last_checked
        """, (tool_name, int(installed), datetime.now().isoformat(timespec="seconds")))

def get_tool_statuses():
    with get_conn() as conn:
        rows = conn.execute("SELECT tool_name,installed FROM tool_status").fetchall()
    return {r["tool_name"]: bool(r["installed"]) for r in rows}

def record_tool_use(tool_name):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO progress (tool_name,times_used,last_used) VALUES (?,1,?)
            ON CONFLICT(tool_name) DO UPDATE SET
                times_used=times_used+1, last_used=excluded.last_used
        """, (tool_name, datetime.now().isoformat(timespec="seconds")))
