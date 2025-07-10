# checkpoints/postgres.py

import os
import psycopg  # Psycopg 3 (wird per default mit langgraph-checkpoint-postgres installiert)
from psycopg.rows import dict_row
from psycopg.connection import Connection
from psycopg import ConnectionInfo
from langgraph.checkpoint.postgres import PostgresSaver

def _create_postgres_connection(host:str=None, user:str=None, password:str=None) -> psycopg.Connection:
    pg_host = host or os.getenv("POSTGRES_HOST", "localhost")
    pg_user = user or os.getenv("POSTGRES_USER")
    pg_pwd = password or os.getenv("POSTGRES_PASSWORD")
    pg_db = os.getenv("POSTGRES_STATE_DB", "user")  # Standard-Datenbank für User
    pg_port = os.getenv("POSTGRES_PORT", "14678")
    if pg_pwd is None:
        raise ValueError("POSTGRES_PASSWORD environment variable is not set.")

    return Connection.connect(
        host=pg_host,
        port=pg_port,
        user=pg_user,
        password=pg_pwd,
        dbname=pg_db,
        autocommit=True,
        row_factory=dict_row
    )

def setup_postgres_saver() -> PostgresSaver:
    conn = _create_postgres_connection()
    saver = PostgresSaver(conn)
    saver.setup()               # einmalig Tabellen anlegen
    return saver

def get_postgres_checkpoint(setup: bool = False) -> PostgresSaver:
    """
    Gibt einen PostgresSaver zurück.
    Wenn setup=True, wird vorher .setup() aufgerufen.
    """
    if setup:
        return setup_postgres_saver()
    else:
        conn = _create_postgres_connection()
        return PostgresSaver(conn)

if __name__ == "__main__":
    cp = get_postgres_checkpoint()
    print("Postgres Checkpoint setup successfully.")
    print(cp)
