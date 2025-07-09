# pg_backend.py  –  psycopg 3-Variante
import psycopg                             # neues Paket
from psycopg.rows import dict_row          # Row-Factory für Mapping-Objekte
from contextlib import closing
from assistant.user.sql_base import UserSQL
import json

class PostgresUserSQL(UserSQL):
    #   DB-Spezifisches
    @property
    def placeholder(self) -> str:         
        return "%s"

    @property
    def json_type(self) -> str:
        return "JSONB"

    @property
    def timestamp_default(self) -> str:
        return "CURRENT_TIMESTAMP"
    @property
    def short_text_type(self) -> str:    
        return "TEXT"
    @property
    def long_text_type(self) -> str:     
        return "TEXT"
    def _to_db_json(self, obj):
        # Immer als String serialisieren; Postgres castet 'TEXT' → JSONB
        return None if obj is None else json.dumps(obj, ensure_ascii=False)
    #   Connection
    def _connect(self):
        """
        Erstellt eine psycopg-3-Verbindung.
        self.dsn kann eine DSN-URL sein („postgresql://…“) *oder* ein Dict
        mit connect-Parametern (host, user, password …).
        """
        if isinstance(self.dsn, str):
            return psycopg.connect(self.dsn)
        return psycopg.connect(**self.dsn)

    #   Cursor
    def dict_cursor(self, conn):
        """
        Gibt einen Cursor zurück, dessen Zeilen als Mapping (dict) erscheinen.
        Das ersetzt das frühere RealDictCursor-Konzept aus psycopg2.
        """
        return conn.cursor(row_factory=dict_row)

    #   executescript
    # Psycopg 3 kann mehrere Statements in einem execute() verarbeiten,
    # deshalb reicht die Fallback-Implementierung der Basisklasse.
    # (Falls du lieber optimieren möchtest, einfach den String splitten
    #  und Statement-weise ausführen.)

    #   Escaping (optional)
    def _escape_identifier(self, identifier: str) -> str:
        # Minimal-Variante mit doppelten Anführungszeichen.
        # Für 100 % sichere Escapes könnte man psycopg.sql.Identifier nutzen:
        #
        #   from psycopg import sql
        #   return sql.Identifier(identifier).as_string(conn)
        #
        return f'"{identifier}"'
