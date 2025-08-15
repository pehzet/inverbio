from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, RemoveMessage, ToolMessage
from assistant.state import ComplexState
from icecream import ic
def check_summary(state: ComplexState):
    messages = state["messages"]
    messages = _clean_messages(messages)
    # len(messages) = 10 is more or less 5 turns
    if len(messages) > 20:
        return "summarize_conversation"
    return END

# def _clean_messages(messages):
#     clean_history = [
#         m for m in messages
#         if not (
#             (isinstance(m, AIMessage) and m.additional_kwargs.get("tool_calls"))
#             or isinstance(m, ToolMessage)
#             or isinstance(m, RemoveMessage)
#         )
#     ]
#     return clean_history
def _clean_messages(messages):
    def is_toolcall_ai(m):
        if not isinstance(m, AIMessage):
            return False
        # GPT-5 / Responses: tool_calls ist ein Top-Level-Attribut
        if getattr(m, "tool_calls", None):
            return True
        # Fallbacks für ältere/andere Clients
        ak = m.additional_kwargs or {}
        return bool(ak.get("tool_calls") or ak.get("function_call") or ak.get("tool_call"))

    clean = []
    for m in messages:
        # 1) Raus: RemoveMessage, ToolMessage, AI-Nachrichten mit Toolcalls
        if isinstance(m, RemoveMessage) or isinstance(m, ToolMessage) or is_toolcall_ai(m):
            continue

        # 2) Optional: leere AI-Nachrichten (z. B. aus Toolcall-Turns) entfernen
        if isinstance(m, AIMessage):
            c = m.content
            if c is None or (isinstance(c, str) and not c.strip()) or (isinstance(c, list) and not c):
                continue

        clean.append(m)
    return clean
def summarize_conversation(state: ComplexState):

    summary = state.get("summary", "")
    if summary:
        summary_message = (
            f"Dies ist eine Zusammenfassung des bisherigen Gesprächs: {summary}\n\n"
            "Erweitere diese Zusammenfassung basierend auf den letzten Nachrichten oben:"
        )
    else:
        summary_message = """
            Erstelle eine Zusammenfassung des obigen Gesprächs. Halte die genannten Produkte und Themen klar und strukturiert.
        """

    clean_history = _clean_messages(state["messages"])

    messages = clean_history + [HumanMessage(content=summary_message)]

    llm = ChatOpenAI(model="gpt-5-mini")
    response = llm.invoke(messages)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]

    return {"summary": response.content, "messages": delete_messages}