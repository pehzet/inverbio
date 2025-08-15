from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, RemoveMessage, ToolMessage
from assistant.state import ComplexState
from icecream import ic
def check_summary(state: ComplexState):
    messages = state["messages"]
    messages = _clean_messages(messages)
    # len(messages) = 10 is more or less 5 turns
    if len(messages) > 10:
        return "summarize_conversation"
    return END

def _clean_messages(messages):
    clean_history = [
        m for m in messages
        if not (
            (isinstance(m, AIMessage) and m.additional_kwargs.get("tool_calls"))
            or isinstance(m, ToolMessage)
            or isinstance(m, RemoveMessage)
        )
    ]
    return clean_history

def summarize_conversation(state: ComplexState):
    ic("SUMMARIZE_CONVERSATION CALLED")
    summary = state.get("summary", "")
    if summary:
        ic(f"summary: {summary}")
        summary_message = (
            f"Dies ist eine Zusammenfassung des bisherigen Gesprächs: {summary}\n\n"
            "Erweitere diese Zusammenfassung basierend auf den letzten Nachrichten oben:"
        )
    else:
        summary_message = """
            Erstelle eine Zusammenfassung des obigen Gesprächs. Halte die genannten Produkte und Themen klar und strukturiert.
        """
    ic(f"summary_message: {summary_message}")
    clean_history = _clean_messages(state["messages"])

    messages = clean_history + [HumanMessage(content=summary_message)]

    llm = ChatOpenAI(model="gpt-4o-mini")
    response = llm.invoke(messages)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]

    return {"summary": response.content, "messages": delete_messages}