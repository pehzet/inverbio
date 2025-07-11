# usersql.py
import json
from abc import ABC, abstractmethod
from contextlib import closing
from typing import Any, Dict, List, Union


class UserSQL(ABC):
    """
    Generische Basisklasse für SQLite / MySQL / PostgreSQL-Backends.
    Subklassen müssen _connect(), dict_cursor() und ggf. _escape_identifier()
    überschreiben; executescript() kann bei Bedarf optimiert werden.
    """

    def __init__(self, data_source_name: Union[str, Dict[str, Any]]):
        """
        :param data_source_name: Datenquelle als URI (z. B. "mysql://user:password@localhost:3306/test") oder
                                    als Dict mit Verbindungsparametern (z. B. {"host": "localhost",
                                    "user": "root", "password": "password", "database": "test"})

        """
        self.dsn = data_source_name
    # DB specific methods
    @abstractmethod
    def _connect(self):
        """Stellt eine DB-Verbindung her und gibt ein Connection-Objekt zurück."""
        raise NotImplementedError

    @property
    @abstractmethod
    def placeholder(self) -> str:
        """Platzhalter-Symbol der jeweiligen DB-API („?“, „%s“ …)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def json_type(self) -> str:
        """SQL-Typ für JSON-Spalten (z. B. TEXT, JSON, JSONB)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def timestamp_default(self) -> str:
        """SQL-Fragment für automatische Timestamp-Spalten."""
        raise NotImplementedError

    @abstractmethod
    def dict_cursor(self, conn):
        """Liefert einen Cursor, der Mapping-Objekte (dict-ähnlich) zurückgibt."""
        raise NotImplementedError

    @property
    @abstractmethod
    def short_text_type(self) -> str:
        """Typ für String-Spalten mit DEFAULT (z. B. VARCHAR)."""
        raise NotImplementedError

    @property 
    @abstractmethod
    def long_text_type(self) -> str:
        """Typ für lange Texte ohne DEFAULT (z. B. TEXT)."""
        raise NotImplementedError

    # kein Plan, hat ChatGPT vorgeschlagen, ich lasse es mal drin /PZm 9.7.25
    def _escape_identifier(self, identifier: str) -> str:
        """Sicheres Escaping von Spalten-/Tabellennamen."""
        return identifier  # SQLite & einfache Fälle

    #   Helper
    def _to_db_json(self, obj: Any):
        """Gibt JSON-geeigneten Wert zurück (dict oder serialisierter String)."""
        if obj is None:
            return None
        return obj if self.json_type.lower().startswith("json") else json.dumps(obj, ensure_ascii=False)

    def executescript(self, sql: str) -> None:
        """
        Fallback-Implementierung für mehrere Statements.
        Subklassen können das überschreiben (SQLite.executescript, PyMySQL multi=True …)
        """
        statements = [s.strip() for s in sql.strip().split(";") if s.strip()]
        with closing(self._connect()) as conn, closing(self.dict_cursor(conn)) as cur:
            for stmt in statements:
                cur.execute(stmt)
            conn.commit()

    #   Table-Creation
    def create_tables(self) -> bool:
        ddl = f"""
        CREATE TABLE IF NOT EXISTS users (
            user_id      {self.short_text_type} PRIMARY KEY,
            created_at   TIMESTAMP DEFAULT {self.timestamp_default},
            updated_at   TIMESTAMP DEFAULT {self.timestamp_default},
            status       {self.short_text_type} DEFAULT 'active',
            preferences  {self.json_type}
        );
        CREATE TABLE IF NOT EXISTS threads (
            thread_id    {self.short_text_type} PRIMARY KEY,
            title        {self.short_text_type} DEFAULT 'New Thread',
            description  {self.long_text_type},
            user_id      {self.short_text_type},
            created_at   TIMESTAMP DEFAULT {self.timestamp_default},
            updated_at   TIMESTAMP DEFAULT {self.timestamp_default},
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """
        try:
            self.executescript(ddl)
            return True
        except Exception as e:
            print("Error creating tables:", e)
            return False

    #   User-CRUD
    def _create_anonymous_user(self) -> bool:
        return self.add_user("anonymous", {"preferences": {}})
    def add_user(self, user_id: str, preferences: Dict | None = None) -> bool:
        sql = f"""INSERT INTO users (user_id, preferences)
                  VALUES ({self.placeholder}, {self.placeholder})"""
        prefs = self._to_db_json(preferences or {})
        try:
            with closing(self._connect()) as conn, closing(self.dict_cursor(conn)) as cur:
                cur.execute(sql, (user_id, prefs))
                conn.commit()
            return True
        except Exception as e:
            print("Error adding user:", e)
            return False

    def get_user(self, user_id: str) -> Dict[str, Any]:
        if user_id in (None, "anonymous"):
            return {"user_id": "anonymous", "preferences": {}}

        sql = f"SELECT * FROM users WHERE user_id = {self.placeholder}"
        with closing(self._connect()) as conn, closing(self.dict_cursor(conn)) as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()

        return self._format_nested_dict(row) if row else {}

    #  Thread-CRUD
    def add_thread(self, thread_id: str, user_id: str) -> bool:
        sql = f"""INSERT INTO threads (thread_id, user_id)
                  VALUES ({self.placeholder}, {self.placeholder})"""
        try:
            with closing(self._connect()) as conn, closing(self.dict_cursor(conn)) as cur:
                cur.execute(sql, (thread_id, user_id))
                conn.commit()
            return True
        except Exception as e:
            print("Error adding thread:", e)
            return False

    def update_thread(self, thread_id: str, field: str, value: Any) -> bool:
        allowed = {"user_id", "title", "description"}
        if field not in allowed:
            raise ValueError("Ungültiger Feldname!")

        identifier = self._escape_identifier(field)
        sql = (
            f"UPDATE threads "
            f"SET {identifier} = {self.placeholder}, "
            f"updated_at = {self.timestamp_default} "
            f"WHERE thread_id = {self.placeholder}"
        )
        try:
            with closing(self._connect()) as conn, closing(self.dict_cursor(conn)) as cur:
                cur.execute(sql, (value, thread_id))
                conn.commit()
            return True
        except Exception as e:
            print("Error updating thread:", e)
            return False

    def get_threads_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM threads WHERE user_id = {self.placeholder}"
        with closing(self._connect()) as conn, closing(self.dict_cursor(conn)) as cur:
            cur.execute(sql, (user_id,))
            rows = cur.fetchall()
        return rows or []

    def get_thread_ids_by_user(self, user_id: str) -> List[str]:
        return [t["thread_id"] for t in self.get_threads_by_user(user_id)]

    #   Utility
    @staticmethod
    def _format_nested_dict(d: Any) -> Any:
        """Wandelt JSON-Strings rekursiv wieder in dict/list-Objekte um."""
        def recurse(x):
            if isinstance(x, str):
                try:
                    return recurse(json.loads(x))
                except Exception:
                    return x
            if isinstance(x, dict):
                return {k: recurse(v) for k, v in x.items()}
            if isinstance(x, list):
                return [recurse(i) for i in x]
            return x
        return recurse(d)
