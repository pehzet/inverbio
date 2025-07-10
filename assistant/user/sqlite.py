# sqlite_backend.py
import sqlite3
from contextlib import closing
from assistant.user.sql_base import UserSQL


class SQLiteUserSQL(UserSQL):
    @property
    def placeholder(self) -> str:         # SQLite benutzt "?"
        return "?"

    @property
    def json_type(self) -> str:           # keine native JSON-Spalte
        return "TEXT"

    @property
    def timestamp_default(self) -> str:   # identisch für SQLite
        return "CURRENT_TIMESTAMP"
    @property
    def short_text_type(self) -> str:    
        return "TEXT"
    @property
    def long_text_type(self) -> str:     
        return "TEXT"

    #   connect
    def _connect(self):
        conn = sqlite3.connect(self.dsn)
        conn.row_factory = sqlite3.Row    # Cursor-Rows als Mapping
        return conn

    #   cursor
    def dict_cursor(self, conn):
        return conn.cursor()              # Row liefert bereits Mapping

    #   executescript (optimiert)
    def executescript(self, sql: str) -> None:
        with closing(self._connect()) as conn:
            conn.executescript(sql)
            conn.commit()
