from langgraph.graph import MessagesState
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
import os
class State(MessagesState):
    summary: str
    messages_history: Annotated[list[AnyMessage], add_messages]

def get_state():
    return State()

def get_sqlite_checkpoint():
    db_path = "state_db/example.db"
    if not os.path.exists(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    return memory
