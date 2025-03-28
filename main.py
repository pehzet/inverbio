from langchain_openai import ChatOpenAI
from env_check import load_and_check_env
from llm_factory import get_llm
from rag_factory import get_retriever_tool
from image_utils import create_msg_with_img
from langgraph.prebuilt import ToolNode, tools_condition
from state import State, get_sqlite_checkpoint
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, RemoveMessage
load_and_check_env()
llm:ChatOpenAI = get_llm("openai", "gpt-4o-mini")
CHROMA_DIR = "chroma_db"
retriever_tool = get_retriever_tool("retrieve_products")
tools = [retriever_tool]
llm = llm.bind_tools(tools)

def assistant(state: State):
    system_message = "You are a helpful virtual shopping assistant for an autonomous smart store called 'Farmely' from Osnabrück that sells regional and organic products."
   
    #summary = state.get("summary")
    #if summary:
    #   system_message += f"\n\nHere is a summary of the conversation earlier: {summary}"

    messages = [SystemMessage(content=system_message)] + state["messages"]
    response = llm.invoke(messages)

    last_message = messages[-1]

    return {"messages": [response], "messages_history": [last_message, response]}



# Build Graph
agent_flow = StateGraph(State)
agent_flow.add_node("assistant", assistant)

rag = ToolNode([retriever_tool])
agent_flow.add_node("rag", rag)
#agent_flow.add_node("check_summary", check_summary)
#agent_flow.add_node("summarize_conversation", summarize_conversation)

# replaced START
agent_flow.set_entry_point("assistant")

agent_flow.add_conditional_edges(
    "assistant",
    tools_condition,
    {
        "tools" : "rag",
        END: END,
    }
)

agent_flow.add_edge("rag", "assistant")

#agent_flow.add_edge("check_summary", "summarize_conversation")
#agent_flow.add_edge("summarize_conversation", END)

# Compile graph
cp = get_sqlite_checkpoint()
graph = agent_flow.compile(checkpointer=cp)

config = {"configurable": {"thread_id": "5"}}

current_state = graph.get_state(config)
history = current_state.values["messages_history"] if current_state.values else []

for m in history:
    if isinstance(m, AIMessage):
        print(f"Assistant: {m.content}\n")
    elif isinstance(m, HumanMessage):
        print(f"User: {m.content}\n")
    else:
        print(f"System: {m.content}\n")

while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break

    user_message = [HumanMessage(content=user_input)]
    result = graph.invoke({"messages": user_message}, config)

    last_message = result["messages"][-1]

    if isinstance(last_message, AIMessage):
        print(f"\nAssistant: {last_message.content}\n")
    elif isinstance(last_message, list):
        for msg in last_message:
            if isinstance(msg, AIMessage):
                print(f"\nAssistant: {msg.content}\n")
    else:
        print(f"\nAssistant returned unexpected message: {last_message}\n")