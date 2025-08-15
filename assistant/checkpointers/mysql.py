from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
import pymysql
import os
from icecream import ic
def _create_mysql_connection(host:str=None, user:str=None, password:str=None) -> pymysql.Connection:
    mysql_host = host or os.getenv("MYSQL_HOST", "localhost")
    mysql_user = user or os.getenv("MYSQL_USER", "root")
    mysql_pwd = password or os.getenv("MYSQL_PASSWORD", None)
    if mysql_pwd is None:
        raise ValueError("MYSQL_PASSWORD environment variable is not set.")
    conn = pymysql.connect(
    host=mysql_host,
    user=mysql_user,
    password=mysql_pwd,
    database="langgraph",
    port=3306,
    autocommit=True,
)
    return conn

def setup_mysql_saver() -> None:
    conn = _create_mysql_connection()
    checkpointer = PyMySQLSaver(conn)
    checkpointer.setup()
    return checkpointer

def get_mysql_checkpoint(setup=False) -> PyMySQLSaver:
    """
    Returns a PyMySQLSaver instance configured for the 'functions' database.
    """
    if setup:
        return setup_mysql_saver()
    else:
        conn = _create_mysql_connection()
        return PyMySQLSaver(conn)
    
if __name__ == "__main__":
    # Example usage
    checkpoint = get_mysql_checkpoint()
    print("MySQL Checkpoint setup successfully.")



