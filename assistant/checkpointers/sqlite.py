from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os
from typing import Optional

def get_sqlite_checkpoint(db_path: Optional[str] = None) -> SqliteSaver:
    db_path = "state_db/example.db" if db_path is None else db_path
    if not os.path.exists(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    return memory