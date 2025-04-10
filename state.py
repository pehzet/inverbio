from langgraph.graph import MessagesState
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from user_db import get_user_from_user_db
import os
import json
from typing import Any, Optional
class State(MessagesState):
    summary: str
    messages_history: Annotated[list[AnyMessage], add_messages]
    user: dict 

def get_state():
    return State()

def get_sqlite_checkpoint():
    db_path = "state_db/example.db"
    if not os.path.exists(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    return memory
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