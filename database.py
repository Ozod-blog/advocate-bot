import sqlite3
from os import getenv

DB_PATH = getenv("DB_PATH", "advocate.db")

class Database:
    def __init__(self):
        self.db_path = DB_PATH

    def init(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    EXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_entry(self, title, str, content: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO knowledge_base (title,content) VALUES (?,?)",
                (title,content)
            )
            conn.commit()
            return cur.lastrowid

    def get_all_entries(self) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, title, content, created_at FROM knowledge_base ORDER BY created_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_entry(self, entry_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, title, content, created_at FROM knowledge_base WHERE id = ?",
                (entry_id,)
            ).fetchone()
            return dict(row) if row else None

    def delete_entry(self, entry_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM knowledge_base WHERE id = ?", (entry_id,))
            conn.commit()

    def get_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM knowledge_base").fetchone()
            return row["cnt"]
