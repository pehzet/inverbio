import sqlite3
import json
from typing import List, Dict
import firebase_admin
from firebase_admin import credentials, firestore
from typing import List, Dict, Literal, Union
from datetime import datetime
import json
import os
from assistant.user.sqlite import SQLiteUserSQL
from assistant.user.firestore import UserFirestore
from assistant.user.mysql import MySQLUserSQL
from assistant.user.postgres import PostgresUserSQL
from icecream import ic
def check_user_db_env_vars(type:str) -> bool:
    if type== "firestore":
        project_id_var = "FIRESTORE_PROJECT_ID"
        if not os.getenv(project_id_var):
            raise ValueError(f"Environment variable '{project_id_var}' is not set.")
    if type == "sqlite":
        db_path_var = "SQLITE_DB_PATH"
        if not os.getenv(db_path_var):
            raise ValueError(f"Environment variable '{db_path_var}' is not set.")
    # rest of the types use user, password and host
    user_var = f"{type.upper()}_USER"
    password_var = f"{type.upper()}_PASSWORD"
    host_var = f"{type.upper()}_HOST"
    user_db_var = f"{type.upper()}_USER_DB"
    if not os.getenv(user_db_var):
        raise ValueError(f"Environment variable '{user_db_var}' is not set.")
    if not os.getenv(user_var):
        raise ValueError(f"Environment variable '{user_var}' is not set.")

    if not os.getenv(password_var):
        raise ValueError(f"Environment variable '{password_var}' is not set.")

    if not os.getenv(host_var):
        raise ValueError(f"Environment variable '{host_var}' is not set.")
    return True

def get_data_source_from_env(type: Literal["sqlite", "firestore", "mysql", "postgres"]) -> Union[str, Dict[str, str]]:
    if type == "sqlite":
        db_path = os.getenv("SQLITE_DB_PATH", "user_db/user.db")
        return db_path
    elif type == "firestore":
        project_id = os.getenv("FIRESTORE_PROJECT_ID")
        if not project_id:
            raise ValueError("Environment variable 'FIRESTORE_PROJECT_ID' is not set.")
        return {"project_id": project_id}
    elif type == "mysql":
        return {
            "host": os.getenv("MYSQL_HOST"),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_USER_DB")
        }
    elif type == "postgres":
        return {
            "host": os.getenv("POSTGRES_HOST"),
            "user": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD"),
            "dbname": os.getenv("POSTGRES_USER_DB"),
            "port": int(os.getenv("POSTGRES_PORT", 5432))
        }
    else:
        raise ValueError(f"Invalid database type: {type}")

def get_user_db(type: Literal["sqlite", "firestore", "mysql", "postgres"] = "sqlite", data_source_name: Union[str, Dict[str, str]] = "user_db/user.db", data_source_from_env=False) -> Union[SQLiteUserSQL, UserFirestore, MySQLUserSQL, PostgresUserSQL]:
    
    if data_source_from_env:
        if not check_user_db_env_vars(type):
            raise ValueError(f"Environment variables for '{type}' user database are not set.")
        data_source_name = get_data_source_from_env(type)
    if type == "sqlite":
        return SQLiteUserSQL(data_source_name)
    elif type == "firestore":
        return UserFirestore(data_source_name)
    elif type == "mysql":
        return MySQLUserSQL(data_source_name)
    elif type == "postgres":
        return PostgresUserSQL(data_source_name)
    raise ValueError("Invalid type")

def setup_user_db(type: Literal["sqlite", "firestore", "mysql", "postgres"] = "sqlite", data_source_name: Union[str, Dict[str, str]] = "user_db/user.db") -> bool:
    db = get_user_db(type, data_source_name)
    table_bool = db.create_tables()
    user_bool = db._create_anonymous_user()
    return table_bool and user_bool