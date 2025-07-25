import os
import json
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

from icecream import ic
from langchain_openai import ChatOpenAI
from langsmith import Client
from pydantic import ValidationError

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode


from langchain_core.messages import (
    AIMessage,
    SystemMessage,
    HumanMessage,
    RemoveMessage,
    ToolMessage,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from assistant.agent.agent_config import AgentConfig
from assistant.agent.image_utils import create_msg_with_img, _encode_image
from assistant.agent.llm_factory import get_llm
from assistant.agent.schemas import AgentResponseFormat
from assistant.agent.state import ComplexState, get_checkpoint
from assistant.agent.summary import check_summary, summarize_conversation
from assistant.tools import get_farmely_tools, get_retriever_tool, get_tool
from assistant.user.database import get_user_db
from barcode.barcode import get_product_by_barcode, get_products_by_barcodes

from assistant.agent.utils import (
    clean_history_for_llm,
    strip_tool_calls_none,
    get_berlin_now
)



class Agent:
    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig.as_default()
        self.graph: CompiledStateGraph | None = None
        self.user_db = get_user_db(
            self.config.get("user_db", "sqlite"), data_source_from_env=True
        )
        self.langsmith_client = Client()

    # Langsmith stuff
    def get_langsmith_client(self) -> Client:
        return self.langsmith_client

    def get_prompt_from_langsmith(self, prompt_identifier: str) -> ChatPromptTemplate:
        return self.langsmith_client.pull_prompt(prompt_identifier)


    def init_llm_and_tools(self) -> Tuple[ChatOpenAI, List[Any]]:
        llm_provider = self.config.get("llm_provider", "openai")
        llm_model = self.config.get("llm_model", "gpt-4o-mini")
        llm: ChatOpenAI = get_llm(llm_provider, llm_model)
        tools = get_farmely_tools()
        llm = llm.bind_tools(tools, tool_choice="auto")
        return llm, tools

    def init_formatter_llm(self, format_cls=AgentResponseFormat):
        llm = get_llm(self.config.get("llm_provider", "openai"), "gpt-4.1-nano")
        return llm.with_structured_output(format_cls)


    def get_format_instructions(self, pydantic_object=AgentResponseFormat) -> str:
        parser = JsonOutputParser(pydantic_object=pydantic_object)
        return parser.get_format_instructions()

    def get_format_msg(self) -> SystemMessage:
        parser = JsonOutputParser(pydantic_object=AgentResponseFormat)
        return SystemMessage(
            content=parser.get_format_instructions(), additional_kwargs={"internal": True}
        )

    def get_system_message(self, state: ComplexState) -> SystemMessage:
        now_berlin = get_berlin_now(iso_format=False)
        base_sys = (
            self.get_prompt_from_langsmith("assistant-system-message")
            .format_prompt(
                user_name=state["user"].get("name", "Anonym"),
                current_day=now_berlin.strftime("%A, %d.%m.%Y"),
                current_time=now_berlin.strftime("%H:%M"),
                output_schema=self.get_format_instructions(),
            )
            .to_messages()
        )
        return base_sys


    def agent(self, state: ComplexState) -> Dict[str, Any]:
        system_message = self.get_system_message(state)

        history_raw = state["messages"]
        history = clean_history_for_llm(history_raw)

        last_user_idx = max(i for i, m in enumerate(history) if isinstance(m, HumanMessage))
        history_before_last = history[:last_user_idx]
        last_user = history[last_user_idx]
        history_after_last = history[last_user_idx + 1 :]

        gen_ctx_payload = {
            "mentioned_products": state["context"].get("mentioned_products", []),
            "location": state["context"].get("location"),
        }
        gen_ctx_msg = SystemMessage(
            content=f"<GEN-CONTEXT>\n{json.dumps(gen_ctx_payload, ensure_ascii=False)}\n</GEN-CONTEXT>",
            additional_kwargs={"internal": True},
        )

        cur_ctx_payload = {
            "current_products": state["context"].get("current_products", []),
            "timestamp_utc": state["context"].get("last_message_utc"),
        }
        cur_ctx_msg = SystemMessage(
            content=f"<CURRENT-CONTEXT>\n{json.dumps(cur_ctx_payload, ensure_ascii=False)}\n</CURRENT-CONTEXT>",
            additional_kwargs={"internal": True},
        )

        messages_for_llm = (
            system_message
            + [gen_ctx_msg]
            + history_before_last
            + [cur_ctx_msg, last_user]
            + history_after_last
        )

        llm, _ = self.init_llm_and_tools()
        raw_ai: AIMessage = llm.invoke(messages_for_llm)

        return {
            "messages": [raw_ai],
            "messages_history": [last_user, raw_ai],
        }

    def custom_tools_condition(self, state: ComplexState) -> str:
        tool_call_messages = [
            m
            for m in state["messages"]
            if isinstance(m, AIMessage) and m.additional_kwargs.get("tool_calls")
        ]
        answered = {t.tool_call_id for t in state["messages"] if isinstance(t, ToolMessage)}
        for msg in reversed(tool_call_messages):
            for call in msg.additional_kwargs["tool_calls"]:
                if call["id"] not in answered:
                    return call["function"]["name"]
        return "format_output"

    def load_user_profile(self, state: ComplexState) -> Dict[str, Any]:
        if state.get("user"):
            return {}

        last_msg = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
        )
        if last_msg is None:
            return {}

        user_id = last_msg.metadata.get("user_id", "anonymous")
        profile = self.user_db.get_user(user_id) or {}
        profile.setdefault("user_id", user_id)
        return {"user": profile}

    def extract_context(self, state: ComplexState) -> Dict[str, Any]:
        last_msg = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
        )
        if last_msg is None:
            return {}

        meta = last_msg.metadata or {}
        ctx: Dict[str, Any] = {}

        barcode = meta.get("barcode")
        if barcode:
            items: List[Dict[str, Any]] = []
            if isinstance(barcode, str):
                prod = get_product_by_barcode(barcode)
                if prod:
                    items.append(prod)
            else:
                prods = get_products_by_barcodes(barcode)
                if prods:
                    items.extend(prods.values() if isinstance(prods, dict) else prods)

            if items:
                existing = state.get("context", {}).get("mentioned_products", [])
                combined = {p["id"]: p for p in existing + items}
                ctx["mentioned_products"] = list(combined.values())
                ctx["current_products"] = items

        if "location" in meta:
            ctx["location"] = meta["location"]

        ctx["last_message_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return {"context": ctx} if ctx else {}

    def format_output(self, state: ComplexState) -> Dict[str, Any]:
        last_ai = next(
            m
            for m in reversed(state["messages"])
            if isinstance(m, AIMessage) and not m.additional_kwargs.get("tool_calls")
        )

        try:
            raw = last_ai.content
            if raw.startswith("```"):
                raw = raw.strip("`").split("\n", 1)[1]
            if isinstance(raw, str):
                structured = AgentResponseFormat.model_validate_json(raw)
            elif isinstance(raw, dict):
                structured = AgentResponseFormat.model_validate(raw)
            else:
                structured = AgentResponseFormat.model_validate_json(json.dumps(raw))
        except ValidationError:
            fmt_llm = self.init_formatter_llm()
            fmt_msg = self.get_format_msg()
            fmt_msg.content += (
                "If your answer contains an image_path, write it as:\n"
                "image_path: url\n"
                "without quotes."
            )
            clean_ai = strip_tool_calls_none(last_ai)
            structured = fmt_llm.invoke([fmt_msg, clean_ai])

        ai_msg = AIMessage(
            content=structured.response,
            additional_kwargs={
                "internal": True,
                "suggestions": getattr(structured, "suggestions", None),
            },
        )
        return {
            "structured_response": structured.model_dump(),
            "messages": [ai_msg],
            "messages_history": [],
        }


    def create_graph(self) -> CompiledStateGraph:
        flow = StateGraph(ComplexState)

        flow.add_node("load_user_profile", self.load_user_profile)
        flow.add_node("extract_context", self.extract_context)
        flow.add_node("agent", self.agent)
        flow.add_node("format_output", self.format_output)
        flow.add_node("summarize_conversation", summarize_conversation)

        chroma_dir = Path(os.getenv("CHROMA_PRODUCT_DB", "chroma_db"))
        rag_tool = get_retriever_tool("retrieve_products", "chroma", chroma_dir=chroma_dir)
        stock_tool = get_tool("fetch_product_stock")

        flow.add_node("retrieve_products", ToolNode([rag_tool]))
        flow.add_node("fetch_product_stock", ToolNode([stock_tool]))

        flow.set_entry_point("load_user_profile")
        flow.add_edge("load_user_profile", "extract_context")
        flow.add_edge("extract_context", "agent")

        flow.add_conditional_edges(
            "agent",
            self.custom_tools_condition,
            {
                "retrieve_products": "retrieve_products",
                "fetch_product_stock": "fetch_product_stock",
                "format_output": "format_output",
            },
        )

        flow.add_edge("retrieve_products", "agent")
        flow.add_edge("fetch_product_stock", "agent")

        flow.add_conditional_edges(
            "format_output",
            check_summary,
            {"summarize_conversation": "summarize_conversation", END: END},
        )
        flow.add_edge("summarize_conversation", END)

        checkpointer = get_checkpoint(type=self.config.get("checkpoint_type", "sqlite"))
        return flow.compile(checkpointer=checkpointer)

    def get_graph(self, force_new: bool = False) -> CompiledStateGraph:
        if force_new or self.graph is None:
            self.graph = self.create_graph()
        return self.graph

    # Public API for the agent
    def create_graph_input(self, content: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        text = content.get("msg", "")
        images = content.get("images", [])
        barcode = content.get("barcode")

        msg = create_msg_with_img(text, images) if images else HumanMessage(content=text)
        meta = {"user_id": user_id, **({"barcode": barcode} if barcode else {})}
        msg = msg.model_copy(update={"metadata": meta})
        return {"messages": [msg]}

    def chat(
        self, content: Dict[str, Any], user: Dict[str, Any] | None = None
    ) -> Tuple[str, List[str], str]:
        user = user or {}
        user_id = user.get("user_id", "anonymous")
        thread_id = user.get("thread_id") or f"{user_id}-{uuid.uuid4()}"

        graph = self.get_graph()
        if not user.get("thread_id"):
            self.user_db.add_thread(thread_id, user_id)

        config = {"configurable": {"thread_id": thread_id}}
        graph_input = self.create_graph_input(content, user_id)
        result = graph.invoke(graph_input, config)

        msg: AIMessage = result["messages"][-1]
        return msg.content, msg.additional_kwargs.get("suggestions", []), thread_id


if __name__ == "__main__":
    agent = Agent()
    thread_id = None

    resp, sugg, thread_id = agent.chat({"msg": "Habt ihr Helles von Friedensreiter?"})
    print(thread_id)
    print("Assistant:", resp)

    while True:
        txt = input("User (exit=quit): ")
        if txt.lower() in {"exit", "quit"}:
            break
        resp, sugg, thread_id = agent.chat({"msg": txt}, {"thread_id": thread_id})
        print("Assistant:", resp)
