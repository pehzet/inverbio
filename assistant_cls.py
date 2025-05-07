from langchain_openai import ChatOpenAI
from env_check import load_and_check_env
from llm_factory import get_llm
from icecream import ic
from image_utils import create_msg_with_img
from langgraph.prebuilt import ToolNode, tools_condition
from state import State, get_sqlite_checkpoint, get_value_from_state
from summary import check_summary, summarize_conversation
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, RemoveMessage, ToolMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from utils import render_graph_to_image
import uuid
from typing import Tuple
from user_db import get_user_db
from langsmith import Client
from tools import get_farmely_tools, get_retriever_tool, get_tool
import json
from langgraph.types import StateSnapshot


class Agent:
    
    def __init__(self, db_source: str = "sqlite"):
        load_and_check_env()
        self.graph = None
        self.user_db = get_user_db(db_source)
        self.langsmith_client = Client()

    def get_langsmith_client(self) -> Client:
        return self.langsmith_client

    def get_prompt_from_langsmith(self, prompt_identifier: str) -> ChatPromptTemplate:
        return self.langsmith_client.pull_prompt(prompt_identifier)

    def initalize_llm_and_tools(self):
        llm: ChatOpenAI = get_llm("openai", "gpt-4o-mini")
        tools = get_farmely_tools()
        llm = llm.bind_tools(tools)
        return llm, tools

    def assistant(self, state: State):
        prompt_identifier = "assistant-system-message"
        prompt = self.get_prompt_from_langsmith(prompt_identifier)
        user_name = get_value_from_state(state, "user_name", "anonymous")
        system_message = prompt.format_prompt(user_name=user_name).to_messages()
        messages = system_message + state["messages"]

        llm, tools = self.initalize_llm_and_tools()
        response = llm.invoke(messages)
        last_message = messages[-1]
        return {"messages": [response], "messages_history": [last_message, response]}

    def custom_tools_condition(self, state: State) -> str:
        tool_call_messages = [
            msg for msg in state["messages"]
            if isinstance(msg, AIMessage) and msg.additional_kwargs.get("tool_calls")
        ]
        tool_responses = {
            msg.tool_call_id for msg in state["messages"]
            if isinstance(msg, ToolMessage)
        }
        for msg in reversed(tool_call_messages):
            for tool_call in msg.additional_kwargs["tool_calls"]:
                if tool_call["id"] not in tool_responses:
                    return tool_call["function"]["name"]
        return END

    def create_graph(self) -> CompiledStateGraph:
        agent_flow = StateGraph(State)
        agent_flow.add_node("assistant", self.assistant)

        rag_tool = get_retriever_tool("retrieve_products")
        stock_tool = get_tool("fetch_product_stock")

        agent_flow.add_node("retrieve_products", ToolNode([rag_tool]))
        agent_flow.add_node("fetch_product_stock", ToolNode([stock_tool]))
        agent_flow.add_node(summarize_conversation)

        agent_flow.set_entry_point("assistant")

        agent_flow.add_conditional_edges(
            "assistant",
            self.custom_tools_condition,
            {
                "retrieve_products": "retrieve_products",
                "fetch_product_stock": "fetch_product_stock",
                END: END,
            }
        )

        agent_flow.add_edge("retrieve_products", "assistant")
        agent_flow.add_edge("fetch_product_stock", "assistant")

        agent_flow.add_conditional_edges(
            "assistant",
            check_summary,
            {
                "summarize_conversation": "summarize_conversation",
                END: END,
            }
        )
        agent_flow.add_edge("summarize_conversation", END)

        cp = get_sqlite_checkpoint()
        graph = agent_flow.compile(checkpointer=cp)
        return graph

    def get_graph(self, force_new=False) -> CompiledStateGraph:
        if force_new or self.graph is None:
            self.graph = self.create_graph()
        return self.graph

    def show_history(self, state: State):
        history = state.values.get("messages_history", [])
        for m in history:
            if isinstance(m, AIMessage):
                print(f"Assistant: {m.content}\n")
            elif isinstance(m, HumanMessage):
                print(f"User: {m.content}\n")
            else:
                print(f"System: {m.content}\n")

    def get_messages_by_thread_id(self, thread_id: str):
        graph = self.get_graph()
        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)

        messages = state.values.get("messages_history") or state.values.get("messages", [])
        messages_content = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                messages_content.append({"role": "assistant", "content": msg.content, "img": None})
            elif isinstance(msg, HumanMessage):
                messages_content.append({"role": "user", "content": msg.content, "img": None})

        return messages_content

    def create_graph_input(self, user_id: str, msg: str, state: StateSnapshot, img=None) -> dict:
        user_object = state.values.get("user", {})
        if not user_object:
            user_object = self.user_db.get_user_from_user_db(user_id)

        msg_object = create_msg_with_img(msg, img) if img else HumanMessage(content=msg)

        return {"messages": [msg_object], "user": user_object}

    def chat(self, msg: str, img: bytes = None, user_id: str = None, thread_id: str = None) -> Tuple[str, str]:
        graph = self.get_graph()
        if not user_id:
            user_id = "anonymous"
        if not thread_id:
            thread_id = f"{user_id}-{uuid.uuid4()}"
            self.user_db.add_thread_to_user_db(thread_id, user_id)

        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)
        graph_input = self.create_graph_input(user_id, msg, state, img)

        result = graph.invoke(graph_input, config)
        return result["messages"][-1].content, thread_id


if __name__ == "__main__":
    agent = Agent()
    thread_id = None
    msg = "Habt ihr Duetto Kakao?"
    result, thread_id = agent.chat(msg, thread_id=thread_id)
    print("Assistant:", result)

    while True:
        print("Type 'exit' to quit.")
        msg = input("User: ")
        if msg.lower() in ["exit", "quit"]:
            break
        result, thread_id = agent.chat(msg, thread_id=thread_id)
        print("Assistant:", result)
