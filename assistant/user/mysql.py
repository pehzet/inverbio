# mysql_backend.py
import json, pymysql
from contextlib import closing
from assistant.user.sql_base import UserSQL


class MySQLUserSQL(UserSQL):
    # ------------------------------------------------ Platzhalter
    @property
    def placeholder(self) -> str:        
        return "%s"
    @property
    def json_type(self) -> str:          
        return "JSON"
    @property
    def timestamp_default(self) -> str:  
        return "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
    @property
    def short_text_type(self) -> str:    
        return "VARCHAR(255)"
    @property
    def long_text_type(self) -> str:     
        return "TEXT"

    # ------------------------------------------------ Connection / Cursor
    def _connect(self):
        return pymysql.connect(**self.dsn) if isinstance(self.dsn, dict) else pymysql.connect(self.dsn)
    def dict_cursor(self, conn):
        return conn.cursor(pymysql.cursors.DictCursor)

    # ------------------------------------------------ executescript (MySQL-spezifisch)
    def executescript(self, sql: str) -> None:
        stmts = [s.strip() for s in sql.strip().split(";") if s.strip()]
        with closing(self._connect()) as conn, closing(self.dict_cursor(conn)) as cur:
            for stmt in stmts:
                cur.execute(stmt)
            conn.commit()

    # ------------------------------------------------ JSON-Serialisierung
    def _to_db_json(self, obj):
        return None if obj is None else json.dumps(obj, ensure_ascii=False)

    def _escape_identifier(self, identifier: str) -> str:
        return f"`{identifier}`"
