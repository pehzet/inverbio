import os

from typing import List, Union

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from assistant.agent.agent import Agent
# 1. Graph mit InMemory-Saver kompilieren (ersetzt InMemorySaver bei Bedarf durch deinen Postgres/Sqlite-Saver)
from icecream import ic

from langchain_community.chat_message_histories import FirestoreChatMessageHistory
def get_firestore_history(thread_id: str, user_id: str, collection="checkpoints") -> List[BaseMessage]:
    history = FirestoreChatMessageHistory(session_id=thread_id, user_id=user_id, collection_name=collection)
    return history.messages

def get_history_without_tool_calls(thread_id: str) -> List[Union[HumanMessage, AIMessage]]:
    """
    Holt den neuesten Snapshot, filtert nur HumanMessage und AIMessage
    und entfernt alle mit leerem content (z.B. Tool-Aufrufe).
    """

    graph = Agent().get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshots = graph.get_state_history(config)
    snapshot = list(snapshots)[-1]


    messages: List[BaseMessage] = snapshot.values.get("messages", [])


    clean = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            clean.append(msg)
        elif isinstance(msg, AIMessage):
            # skippt alle AI‐Messages, die nur Tool-Aufrufe sind
            if msg.content == "":
                continue
            clean.append(msg)
    return clean
def format_messages(messages: List[BaseMessage]) -> List[dict]:
    """
    Formatiert die Nachrichten für die Ausgabe.
    """
    formatted_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            formatted_messages.append({"role": "assistant", "content": msg.content})
        else:
            pass
    return formatted_messages

def get_messages_by_thread_id(thread_id: str) -> List[dict]:
    """
    Holt die Nachrichten für einen bestimmten Thread.
    """
    messages = get_history_without_tool_calls(thread_id)
    formatted_messages = format_messages(messages)
    return formatted_messages


def get_messages_test(thread_id: str) -> List[dict]:
    """
    Holt die Nachrichten für einen bestimmten Thread.
    """
    agent = Agent()
    messages = agent.get_messages_by_thread_id(thread_id)
    return messages
if __name__ == "__main__":
    thread_id = "anonymous-2b4199fb-2d92-4292-8f16-4dbb3b5a73b3"
    user_id = "anonymous"
    messages = get_messages_test(thread_id)
    print(messages)
    # history = get_firestore_history(thread_id, user_id, collection="writes")
    # print(history) # returns: []