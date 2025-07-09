from langgraph.graph import MessagesState
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph_checkpoint_firestore import FirestoreSaver,FirestoreSerializer
import os
import json
from typing import Any, Optional, Union, Literal
from assistant.checkpointers.firestore import FirebaseImageFirestoreSaver
from assistant.checkpointers.sqlite import get_sqlite_checkpoint
from assistant.checkpointers.firestore import get_firestore_checkpoint
from assistant.checkpointers.mysql import get_mysql_checkpoint
from assistant.checkpointers.postgres import get_postgres_checkpoint
from assistant.utils.utils import merge_dicts
class ComplexState(MessagesState):
    summary: str
    messages_history: Annotated[list[AnyMessage], add_messages]
    user:     Annotated[dict, merge_dicts]
    context:  Annotated[dict, merge_dicts]

def get_state():
    return ComplexState()

def check_checkpoint_env_vars(type:str) -> bool:
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
    checkpoint_db_var = f"{type.upper()}_CHECKPOINT_DB"
    if not os.getenv(checkpoint_db_var):
        raise ValueError(f"Environment variable '{checkpoint_db_var}' is not set.")
    if not os.getenv(user_var):
        raise ValueError(f"Environment variable '{user_var}' is not set.")

    if not os.getenv(password_var):
        raise ValueError(f"Environment variable '{password_var}' is not set.")

    if not os.getenv(host_var):
        raise ValueError(f"Environment variable '{host_var}' is not set.")
    return True

def get_checkpoint(type:Literal["sqlite", "firestore", "mysql", "postgres"]) -> Union[SqliteSaver, FirestoreSaver]:
    if not check_checkpoint_env_vars(type):
        raise ValueError(f"Environment variables for '{type}' checkpoint are not set.")
    if type == "sqlite":
        return get_sqlite_checkpoint()
    elif type == "firestore":
        return get_firestore_checkpoint()
    elif type == "mysql":
        return get_mysql_checkpoint()
    elif type == "postgres":
        return get_postgres_checkpoint()
    else:
        raise ValueError(f"Checkpoint type '{type}' not recognized.")


def get_value_from_state(state: dict, key: str, default: Any = None) -> Any:
    """Recursively search for a key in the state dictionary and return its value.
    If the key is not found, return the default value.
    If multiple keys are found, return the first one.

    Args:
        state (dict): The state dictionary to search.
        key (str): The key to search for.
        default: The default value to return if the key is not found.

    Returns:
        value: The value of the key if found, otherwise the default value.
    """
    if not isinstance(state, dict):
        return default

    if key in state:
        return state[key]

    for val in state.values():
        # Falls es ein JSON-String ist, versuche ihn zu parsen
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                continue

        if isinstance(val, dict):
            result = get_value_from_state(val, key, default)
            if result is not default:
                return result

        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    result = get_value_from_state(item, key, default)
                    if result is not default:
                        return result

    return default