import os
print(os.environ.get("INVERBIO_ENV"))
if os.environ.get("INVERBIO_ENV") == "dev":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agent.env_check import load_and_check_env
    load_and_check_env()

from langchain_openai import ChatOpenAI
from agent.llm_factory import get_llm
from agent.image_utils import create_msg_with_img
from langgraph.prebuilt import ToolNode, tools_condition
from agent.state import ComplexState, get_checkpoint, get_value_from_state
from agent.summary import check_summary, summarize_conversation
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, RemoveMessage, ToolMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from agent.utils import render_graph_to_image
import uuid
from typing import Tuple
from agent.user_management import get_user_db
from langsmith import Client
from agent.tools import get_farmely_tools, get_retriever_tool, get_tool
import json
from langgraph.types import StateSnapshot
from agent.image_utils import _encode_image, _decode_image
from typing import List, Dict, Any, Literal
import requests
import time
import datetime
from icecream import ic

from barcode.barcode import get_product_by_barcode, get_products_by_barcodes

class Agent:
    def __init__(self, db_source: str = "firestore"):
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

    def _format_products_for_prompt(self, products):
        if not products:
            return ""
        return "\n".join(
            f"- {p['name']} (SKU {p['id']}, {p.get('brand','')})"
            for p in products
        )
    def _clean_history_for_llm(self, history):
        """
        Removes RemoveMessages and all ToolMessages whose
        triggering assistant/tool_calls message does not (or no longer) exist.
        """
    
        valid_tool_ids = {
            t["id"]
            for m in history
            if isinstance(m, AIMessage) and m.additional_kwargs.get("tool_calls")
            for t in m.additional_kwargs["tool_calls"]
        }

  
        cleaned = []
        for m in history:
            if isinstance(m, RemoveMessage):
                continue                                
            if isinstance(m, ToolMessage) and m.tool_call_id not in valid_tool_ids:
                continue                              
            cleaned.append(m)

        return cleaned
    def assistant(self, state: ComplexState):

    
        base_sys = self.get_prompt_from_langsmith("assistant-system-message")\
            .format_prompt(
                user_name       = state["user"].get("name", "Anonym"),
                user_preferences = json.dumps(
                    state["user"].get("preferences", {}), ensure_ascii=False)
            ).to_messages()


        history_raw = state["messages"]
        history     = self._clean_history_for_llm(history_raw)


        last_user_idx = max(
            i for i, m in enumerate(history) if isinstance(m, HumanMessage)
        )
        history_before_last = history[:last_user_idx]
        last_user           = history[last_user_idx]
        history_after_last  = history[last_user_idx+1:]


        gen_ctx_payload = {
            "mentioned_products": state["context"].get("mentioned_products", []),
            "location":           state["context"].get("location"),
    
        }
        gen_ctx_msg = SystemMessage(
            content=f"<GEN-CONTEXT>\n{json.dumps(gen_ctx_payload, ensure_ascii=False)}\n</GEN-CONTEXT>",
            additional_kwargs={"internal": True}
        )


        cur_ctx_payload = {
            "current_products": state["context"].get("current_products", []),
            "timestamp_utc":    state["context"].get("last_message_utc"),
        }
        cur_ctx_msg = SystemMessage(
            content=f"<CURRENT-CONTEXT>\n{json.dumps(cur_ctx_payload, ensure_ascii=False)}\n</CURRENT-CONTEXT>",
            additional_kwargs={"internal": True}
        )


        messages_for_llm = (
            base_sys +
            [gen_ctx_msg] +
            history_before_last +
            [cur_ctx_msg, last_user] +   #  ← Current Context direkt vor User
            history_after_last # required for tool calls to work properly
        )

        llm, _  = self.initalize_llm_and_tools()
        response = llm.invoke(messages_for_llm)

        return {
            "messages": [response],
            "messages_history": [last_user, response]
        }


    def custom_tools_condition(self, state: ComplexState) -> str:
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

    def load_user_profile(self, state: ComplexState) -> Dict[str, Any]:
        """
        Graph-node: ensure `state.user` is present.

        • If a profile is already stored in the checkpoint → return {} (no change).
        • Otherwise read the `user_id` carried in the newest HumanMessage’s
        metadata, fetch the profile from `self.user_db`, and return it
        as a patch.  Because `user` uses the `merge_dicts` aggregator,
        the profile will be *deep-merged* with any future updates.
        """
        # 1 — skip when we already have a profile (common case after first turn)
        if state.get("user"):
            return {}

        # 2 — find the most-recent HumanMessage (it’s the one just injected)
        last_msg = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            None,
        )
        if last_msg is None:                 # defensive: should never occur
            return {}

        user_id = last_msg.metadata.get("user_id", "anonymous")

        # 3 — fetch the profile from the store (may be empty {})
        profile = self.user_db.get_user_information_from_user_db(user_id) or {}
        # guarantee the id is inside the profile so later prompts can reference it
        profile.setdefault("user_id", user_id)

        # 4 — return the patch; LangGraph will deep-merge it
        return {"user": profile}

    def extract_context(self, state: ComplexState) -> Dict[str, Any]:
        """
        Graph-node: pull situational facts from the *latest* HumanMessage
        and patch them into `state.context`.

        Currently implemented sources
        -----------------------------
        • `barcode`  – single str or list[str] in message.metadata
        • `location` – optional str in message.metadata (e.g. store ID)
        • automatic timestamp of the utterance

        Behaviour
        ---------
        • If no new facts are found ➜ return {} (no state change).
        • List-type values are *accumulated*: new items are appended to the
        existing list (deduplicated) instead of overwritten.
        • The node does **not** modify state in-place; it returns a patch.
        """

        # 1 — locate the most-recent HumanMessage
        last_msg = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            None,
        )
        if last_msg is None:
            return {}                     # defensive: should never happen

        meta = last_msg.metadata or {}

        # 2 — collect new context ------------------------------------
        new_ctx: Dict[str, Any] = {}

        # ── (a) Bar-codes → product objects -------------------------
        barcode = meta.get("barcode")
        if barcode:
            mentioned: List[Dict[str, Any]] = []

            if isinstance(barcode, str):
                product = get_product_by_barcode(barcode)
                if product:
                    mentioned.append(product)

            elif isinstance(barcode, list):
                products = get_products_by_barcodes(barcode)    # may return dict
                if products:
                    if isinstance(products, dict):
                        mentioned.extend(products.values())
                    else:
                        mentioned.extend(products)

            if mentioned:
                # accumulate with existing list (if any)
                existing = state.get("context", {}).get("mentioned_products", [])
                combined = {p["id"]: p for p in existing + mentioned}  # dedupe by id
                new_ctx["mentioned_products"] = list(combined.values())
                new_ctx["current_products"]   = mentioned              # focus set

        # ── (b) Location -------------------------------------------
        if "location" in meta:
            new_ctx["location"] = meta["location"]

        # ── (c) Timestamp ------------------------------------------
        new_ctx["last_message_utc"] = datetime.datetime.utcnow().isoformat()

        # 3 — return patch or empty dict -----------------------------
        return {"context": new_ctx} if new_ctx else {}


    def create_graph(self) -> CompiledStateGraph:

        agent_flow = StateGraph(ComplexState)
        agent_flow.add_node("load_user_profile", self.load_user_profile)
        agent_flow.add_node("extract_context",   self.extract_context)
        agent_flow.add_node("assistant", self.assistant)
        
        # External Tools
        rag_tool = get_retriever_tool("retrieve_products")
        stock_tool = get_tool("fetch_product_stock")
        agent_flow.add_node("retrieve_products", ToolNode([rag_tool]))
        agent_flow.add_node("fetch_product_stock", ToolNode([stock_tool]))

        # Summarization
        agent_flow.add_node(summarize_conversation)

        agent_flow.set_entry_point("load_user_profile")
        agent_flow.add_edge("load_user_profile", "extract_context")
        agent_flow.add_edge("extract_context",   "assistant")

        # agent_flow.set_entry_point("assistant")

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
    
        cp = get_checkpoint(type="firestore")

        graph = agent_flow.compile(checkpointer=cp)
       
        return graph

    def get_graph(self, force_new=False) -> CompiledStateGraph:
        if force_new or self.graph is None:
            self.graph = self.create_graph()
        return self.graph

    def show_history(self, state: ComplexState):
        history = state.values.get("messages_history", [])
        for m in history:
            if isinstance(m, AIMessage):
                print(f"Assistant: {m.content}\n")
            elif isinstance(m, HumanMessage):
                print(f"User: {m.content}\n")
            else:
                print(f"System: {m.content}\n")


    def get_messages_by_thread_id(self, thread_id: str) -> List[Dict[str, Any]]:

        graph = self.get_graph()

        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)


        messages = state.values.get("messages_history") or state.values.get("messages", [])
        messages_content: List[Dict[str, Any]] = []

        for msg in messages:
            if isinstance(msg, RemoveMessage) or isinstance(msg, ToolMessage):
                continue
            # TEST: Filter out internal messages -> if success merge with if above
            if msg.additional_kwargs.get("internal"):
                continue            
            raw = msg.content
            if not raw:
                continue

            # Wenn content ein einfacher String ist:
            if isinstance(raw, str):
                entry = {
                    "role": "assistant" if isinstance(msg, AIMessage) else "user",
                    "content": raw,
                    "images": None
                }
                messages_content.append(entry)
                continue

            # Ansonsten gehen wir davon aus, dass raw eine Liste von Parts ist
            # (je ein Dict mit type='text' oder type='image_url')
            texts: List[str] = []
            imgs: List[str] = []

            for part in raw:
                ptype = part.get("type")
                if ptype == "text":
                    # sammle reinen Text
                    text = part.get("text", "").strip()
                    if text:
                        texts.append(text)

                elif ptype == "image_url":
                    # strukturiert als {'image_url': {'prefix':..., 'url':...}, 'type':'image_url'}
                    info = part.get("image_url", {})
                    url = info.get("url")
                    prefix = info.get("prefix", "data:image/png;base64")
                    if not url:
                        continue

                    # schon Data-URI?
                    if url.startswith("data:") and ";base64," in url:
                        data_uri = url
                    else:
                        # echtes Bild herunterladen und in Base64 umwandeln
                        resp = requests.get(url)
                        resp.raise_for_status()
                        b64 = _encode_image(resp.content)
                        # Content-Type aus Prefix extrahieren (z.B. "data:image/png;base64")
                        data_uri = f"{prefix},{b64}"

                    imgs.append(data_uri)

            entry = {
                "role": "assistant" if isinstance(msg, AIMessage) else "user",
                "content": " ".join(texts).strip() or None,
                "images": imgs if imgs else None
            }
            messages_content.append(entry)

        return messages_content

    def create_additional_context(self, state: StateSnapshot, content: dict, user: dict) -> str:
   
        additional_context = {}
        barcode = content.get("barcode", None)
        if barcode:
            if isinstance(barcode, str):
                product = get_product_by_barcode(barcode)
                if product:
                    additional_context["mentioned_products"] = [product]
                    additional_context["current_products"] = [product]
            elif isinstance(barcode, list):
                products = get_products_by_barcodes(barcode)
                if products:
                    additional_context["mentioned_products"] = list(products.values()) if isinstance(products, dict) else products
                    additional_context["current_products"] = list(products.values()) if isinstance(products, dict) else products

        return additional_context
    def get_user_information(self, user: dict) -> dict:
        user_id = user.get("user_id") if user else None
        if not user_id:
            user_id = "anonymous"
        return self.user_db.get_user_information_from_user_db(user_id)

    def create_graph_input(self,
                        content: dict,
                        user_id: str) -> dict:
        """
        Serialise the frontend payload into a single HumanMessage.
        """
        text   = content.get("msg", "")
        images = content.get("images", [])
        barcode = content.get("barcode")          # optional

        msg = (
            create_msg_with_img(text, images) if images
            else HumanMessage(content=text)
        )

        # ➜ all identifiers / extra facts go into metadata
        meta = {"user_id": user_id}
        if barcode:
            meta["barcode"] = barcode

        msg = msg.model_copy(update={"metadata": meta})

        return {"messages": [msg]}

    # def chat(self, msg: str, images: list[str] = None, user_id: str = None, thread_id: str = None) -> Tuple[str, str]:
    def chat(self, content: dict, user:dict=None) -> Tuple[str, str]:


        user_id = user.get("user_id") if user else None
        thread_id = user.get("thread_id") if user else None

        graph = self.get_graph()
        if not user_id:
            user_id = "anonymous"
        if not thread_id:
            thread_id = f"{user_id}-{uuid.uuid4()}"
            self.user_db.add_thread_to_user_db(thread_id, user_id)

        config = {"configurable": {"thread_id": thread_id}}
  
     
        graph_input = self.create_graph_input(content, user_id)

        result = graph.invoke(graph_input, config)
        return result["messages"][-1].content, thread_id


if __name__ == "__main__":
    agent = Agent()
    thread_id = None
    msg = "Habt ihr Helles von Friedensreiter?"
    result, thread_id = agent.chat(msg, thread_id=thread_id)
    print(thread_id)
    print("Assistant:", result)

    while True:
        print("Type 'exit' to quit.")
        msg = input("User: ")
        if msg.lower() in ["exit", "quit"]:
            break
        result, thread_id = agent.chat(msg, thread_id=thread_id)
        print("Assistant:", result)
