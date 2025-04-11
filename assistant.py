from langchain_openai import ChatOpenAI
from env_check import load_and_check_env
from llm_factory import get_llm
from rag_factory import get_retriever_tool
from image_utils import create_msg_with_img
from langgraph.prebuilt import ToolNode, tools_condition
from state import State, get_sqlite_checkpoint, get_value_from_state
from summary import check_summary, summarize_conversation
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, RemoveMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from utils import render_graph_to_image
import uuid
from typing import Tuple
from user_db import get_user_from_user_db, add_thread_to_user_db
from langsmith import Client
from icecream import ic
import json
from langgraph.types import StateSnapshot 

load_and_check_env()
def get_langsmith_client() -> Client:
    if "langsmith_client" not in globals():
        globals()["langsmith_client"] = Client()
    return globals()["langsmith_client"]


def get_prompt_from_langsmith(prompt_identifier:str) -> ChatPromptTemplate:
    client:Client = get_langsmith_client()
    prompt:ChatPromptTemplate = client.pull_prompt(prompt_identifier)
    return prompt





def assistant(state: State):

    prompt_identifier = "assistant-system-message"
    prompt = get_prompt_from_langsmith(prompt_identifier)
    user_name = get_value_from_state(state, "user_name", "anonymous")

    system_message = prompt.format_prompt(user_name = user_name).to_messages()
    messages = system_message + state["messages"]
    llm, tools = initalize_llm_and_tools()
    response = llm.invoke(messages)
    last_message = messages[-1]
    return {"messages": [response], "messages_history": [last_message, response]}

def initalize_llm_and_tools():
    llm:ChatOpenAI = get_llm("openai", "gpt-4o-mini")
    retriever_tool = get_retriever_tool("retrieve_products")
    tools = [retriever_tool]
    llm = llm.bind_tools(tools)
    return llm, tools
def create_graph() -> CompiledStateGraph:
    
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
    # agent_flow.add_conditional_edges("assistant", check_summary)
    agent_flow.add_conditional_edges(
        "assistant",
        check_summary,
        {
            "summarize_conversation": "summarize_conversation",
            END: END,
        }
    )
    # # agent_flow.add_edge("check_summary", "summarize_conversation")
    agent_flow.add_edge("summarize_conversation", END)

    # Compile graph
    cp = get_sqlite_checkpoint()
    
    graph = agent_flow.compile(checkpointer=cp)
    # render_graph_to_image(graph, "graph_with_new_edge.png")
    return graph

def get_graph(force_new=False) -> CompiledStateGraph:
    '''Get the graph. If it does not exist, create it.
    Args:
        force_new (bool): Whether to create a new graph. Defaults to False.
        
        Returns:
        CompiledStateGraph: The graph.'''

    if force_new or "graph" not in globals():
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

def create_graph_input(user_id:str, msg:str, state:StateSnapshot, img=None) -> dict:
    '''Create the input for the graph.
    Args:
        msg (str): The message to send to the assistant.
        img (bytes): The image to send to the assistant. Can be None.
        user_id (str): The user ID. Can be None.
        
        Returns:
        dict: The input for the graph.'''
    
    user_object = state.values.get("user", {}) 
    if not user_object:
        user_object = get_user_from_user_db(user_id)

    if img:
        msg_object = create_msg_with_img(msg, img)
    else:
        msg_object = HumanMessage(content=msg)

    return {"messages": [msg_object], "user" : user_object}

def chat(msg:str, img=None, user_id=None, thread_id=None) -> Tuple[str, str]:

    graph: CompiledStateGraph = get_graph()

    if not user_id:
        user_id = "anonymous"
    if not thread_id:  
        thread_id = str(user_id) + "-" + str(uuid.uuid4())
        add_thread_to_user_db(thread_id, user_id)
    config = {"configurable": {"thread_id": thread_id}}
    state:StateSnapshot = graph.get_state(config)
 
    graph_input = create_graph_input(user_id, msg, state, img)
    
    

    result = graph.invoke(graph_input, config)
  
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

