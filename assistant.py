from langchain_openai import ChatOpenAI
from env_check import load_and_check_env
from llm_factory import get_llm
from rag_factory import get_retriever_tool
from image_utils import create_msg_with_img
from langgraph.prebuilt import ToolNode, tools_condition
from state import State, get_sqlite_checkpoint
from summary import check_summary, summarize_conversation
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, RemoveMessage
from utils import render_graph_to_image
import uuid
from typing import Tuple
load_and_check_env()


def initalize_llm_and_tools():
    llm:ChatOpenAI = get_llm("openai", "gpt-4o-mini")
    retriever_tool = get_retriever_tool("retrieve_products")
    tools = [retriever_tool]
    llm = llm.bind_tools(tools)
    return llm, tools



def assistant(state: State):
#     system_message = """
#     You are a helpful virtual shopping assistant for an autonomous smart store called 'Farmely' from Osnabrück that sells regional and organic products. Your name is 'Farmo'. Introduce yourself shortly at the begging of the conversation .Your task is to help the customer on his customer journey. 
# The Farmely store is a local smart store for regional and organic food. Customer can only buy products at the point of sale. Not online or via Assistant.
# Farmely is placed in Osnabrück, lower saxony, Germany."""
    system_message = "youre a helpful assistant"
    summary = state.get("summary")
    if summary:
      system_message += f"\n\nHere is a summary of the conversation earlier: {summary}"

    messages = [SystemMessage(content=system_message)] + state["messages"]
    # llm:ChatOpenAI = get_llm("openai", "gpt-4o-mini")
    llm, tools = initalize_llm_and_tools()
    response = llm.invoke(messages)

    last_message = messages[-1]

    return {"messages": [response], "messages_history": [last_message, response]}

def create_graph():
    
    # Build Graph
    agent_flow = StateGraph(State)
    # Add all nodes
    agent_flow.add_node("assistant", assistant)
    tools = get_retriever_tool("retrieve_products")
    rag = ToolNode([tools])
    agent_flow.add_node("rag", rag)
    # agent_flow.add_node("check_summary", check_summary)
    agent_flow.add_node(summarize_conversation)

    # replaced START
    agent_flow.set_entry_point("assistant")
    # RAG edges
    agent_flow.add_conditional_edges(
        "assistant",
        tools_condition,
        {
            "tools" : "rag",
            END: END,
        }
    )
    agent_flow.add_edge("rag", "assistant")

    # Summary edges
    agent_flow.add_conditional_edges("assistant", check_summary)
    # # agent_flow.add_edge("check_summary", "summarize_conversation")
    agent_flow.add_edge("summarize_conversation", END)

    # Compile graph
    cp = get_sqlite_checkpoint()
    
    graph = agent_flow.compile(checkpointer=cp)
    # render_graph_to_image(graph, "graph_4.png")
    return graph

def get_graph():
    if "graph" not in globals():
        globals()["graph"] = create_graph()
    graph = globals()["graph"]
    return graph

def show_history(state: State):
    history = state.values["messages_history"] if state.values else []
    for m in history:
        if isinstance(m, AIMessage):
            print(f"Assistant: {m.content}\n")
        elif isinstance(m, HumanMessage):
            print(f"User: {m.content}\n")
        else:
            print(f"System: {m.content}\n")

def get_messages_by_thread_id(thread_id: str): 
    '''Get all messages by thread ID.
    Args:
        thread_id (str): The thread ID to filter messages by.
        
        Returns:
        list: A list of messages that belong to the specified thread ID.'''
    graph:StateGraph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    # history = graph.get_state_history(config)
    state = graph.get_state(config)
    messages = state.values.get("messages_history")
    if not messages:
        messages = state.values.get("messages", [])
    messages_content = []
    # Extract Content. Tool Messages are not included in the messages list.
    for msg in messages:
        if isinstance(msg, AIMessage):
            msg_content = {"role": "assistant", "content": msg.content, "img":None}
            messages_content.append(msg_content)
        elif isinstance(msg, HumanMessage):
            msg_content = {"role": "user", "content": msg.content, "img": None}
            messages_content.append(msg_content)

    return messages_content

def chat(msg:str, img=None, user_id=None, thread_id=None) -> Tuple[str, str]:
    '''Chat with the assistant.
    Generates a response to the user's message and image.
    If an image is provided, it will be sent to the assistant.
    If no image is provided, only the message will be sent.
    The user ID and thread ID are used to identify the conversation.
    If no user ID is provided, the conversation will be anonymous.
    If no thread ID is provided, a new one will be generated.
    Args:
        msg (str): The message to send to the assistant.
        img (bytes): The image to send to the assistant. Can be None.
        user_id (str): The user ID. Can be None.
        thread_id (str): The thread ID. Can be None.
        
        Returns:
        str: The response from the assistant.
        str: The thread ID.'''
    graph = get_graph()


    if img:
        msg_object = create_msg_with_img(msg, img)
    else:
        msg_object = HumanMessage(content=msg)

    if not user_id:
        user_id = "anonym"
    if not thread_id:
        thread_id = str(user_id) + "-" + str(uuid.uuid4())

    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke({"messages": [msg_object]}, config)
  
    return result["messages"][-1].content, thread_id


if __name__ == "__main__":
    thread_id = None
    while True:
        print("Type 'exit' to quit.")
        msg = input("User: ")
        if msg.lower() in ["exit", "quit"]:
            break
        result, thread_id = chat(msg, thread_id=thread_id)
        print("Assistant: ", result)

