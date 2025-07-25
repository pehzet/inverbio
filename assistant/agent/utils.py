# utils.py
# generic helpers, agnostic to Agent internals
from typing import List
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, RemoveMessage, BaseMessage
import datetime as _dt
import pytz as _pytz

_BERLIN = _pytz.timezone("Europe/Berlin")

def format_products_for_prompt(products: List[dict]) -> str:
    """Return a bullet-list string for the given product dicts.

    Args:
        products: List of product records.

    Returns:
        '\n'-joined string or '' when list is empty.
    """
    return "\n".join(
        f"- {p['name']} (SKU {p['id']}, {p.get('brand', '')})"
        for p in products or []
    )


def clean_history_for_llm(history: List[BaseMessage]) -> List[BaseMessage]:
    """Remove RemoveMessage and orphaned ToolMessage objects.

    Args:
        history: Complete message list.

    Returns:
        History pruned for LLM consumption.
    """
    valid_ids = {
        t["id"]
        for m in history
        if isinstance(m, AIMessage) and m.additional_kwargs.get("tool_calls")
        for t in m.additional_kwargs["tool_calls"]
    }

    return [
        m for m in history
        if not isinstance(m, RemoveMessage)
        and not (isinstance(m, ToolMessage) and m.tool_call_id not in valid_ids)
    ]


def strip_tool_calls_none(msg: AIMessage) -> AIMessage:
    """Drop the key ``tool_calls`` when its value is ``None``.

    Args:
        msg: AIMessage to sanitise.

    Returns:
        New AIMessage without meaningless ``tool_calls`` entry.
    """
    kws = dict(msg.additional_kwargs or {})
    if kws.get("tool_calls") is None:
        kws.pop("tool_calls", None)
    return msg.model_copy(update={"additional_kwargs": kws})


def show_history(messages: List[BaseMessage]) -> None:
    """Print role and content of each message (debug only).

    Args:
        messages: Message list.
    """
    for m in messages:
        role = (
            "assistant" if isinstance(m, AIMessage)
            else "user" if isinstance(m, HumanMessage)
            else "system"
        )
        print(f"{role.capitalize()}: {m.content}\n")



def get_berlin_now(iso_format: bool = True) -> _dt.datetime:
    """Return timezone-aware ``datetime.now`` in Europe/Berlin."""
    dt = _dt.datetime.now(_BERLIN)
    return dt.isoformat() if iso_format else dt