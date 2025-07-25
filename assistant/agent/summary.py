from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, RemoveMessage, ToolMessage
from assistant.agent.state import ComplexState

def check_summary(state: ComplexState):
    messages = state["messages"]
    if len(messages) > 20:
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
    summary = state.get("summary", "")
    if summary:
        summary_message = (
            f"This is a summary of the conversation so far: {summary}\n\n"
            "Extend this summary based on the latest messages above:"
        )
    else:
        summary_message = "Create a summary of the conversation above:"
    clean_history = _clean_messages(state["messages"])
    messages = clean_history + [HumanMessage(content=summary_message)]
    llm = ChatOpenAI(model="gpt-4o-mini")
    response = llm.invoke(messages)

    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    return {"summary": response.content, "messages": delete_messages}