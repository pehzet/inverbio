import os
from langchain_openai import ChatOpenAI
from assistant import state
from assistant.llm_factory import get_llm
from assistant.image_utils import create_msg_with_img
from langgraph.prebuilt import ToolNode, tools_condition
from assistant.state import ComplexState, get_checkpoint, get_value_from_state
from assistant.summary import check_summary, summarize_conversation
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, RemoveMessage, ToolMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from assistant.schemas import AgentResponseFormat
from assistant.logger import log_execution
from pathlib import Path
import uuid
from typing import Iterable, Tuple
from assistant.user.database import get_user_db
from langsmith import Client
from assistant.tools import get_farmely_tools, get_retriever_tool, get_tool
import json
from langgraph.types import StateSnapshot
from assistant.image_utils import _encode_image, _decode_image
from typing import List, Dict, Any, Literal
import requests
import time
import datetime
from icecream import ic
from assistant.agent_config import AgentConfig
from barcode.barcode import get_product_by_barcode, get_products_by_barcodes
import pytz
from pydantic import ValidationError
from assistant.suggestion_utils import _collect_all_suggestions, _make_suggestions_msg_all
from assistant.prompt_utils import get_prompt_template_with_placeholders
class Agent:
    def __init__(self, config:AgentConfig = None):
        self.config = config or AgentConfig.as_default()
        self.graph = None
        self.user_db = get_user_db(self.config.get("user_db", "sqlite"), data_source_from_env=True)
        self.langsmith_client = Client()
        self.current_system_msg = None
        self._last_system_msg_fetch = None

    def get_langsmith_client(self) -> Client:
        return self.langsmith_client

    def get_prompt_from_langsmith(self, prompt_identifier: str) -> ChatPromptTemplate:
        return self.langsmith_client.pull_prompt(prompt_identifier)

    def init_llm_and_tools(self) -> Tuple[ChatOpenAI, List[Any]]:
        llm_provider = self.config.get("llm_provider", "openai")
        llm_model = self.config.get("llm_model", "gpt-5-mini")
        llm: ChatOpenAI = get_llm(llm_provider, llm_model)
        tools = get_farmely_tools()
        llm = llm.bind_tools(tools, tool_choice="auto")
        return llm, tools
    def init_formatter_llm(self, format_cls=AgentResponseFormat):
   
        llm = get_llm(self.config.get("llm_provider","openai"),
                      "gpt-5-nano")
                    # self.config.get("llm_model","gpt-5-nano")) # TODO SPECIFY AS PARAMETER
        return llm.with_structured_output(format_cls)
    def _format_products_for_prompt(self, products):
        if not products:
            return ""
        return "\n".join(
            f"- {p['name']} (SKU {p['id']}, {p.get('brand','')})"
            for p in products
        )
    # def _clean_history_for_llm(self, history):
    #     """
    #     Removes RemoveMessages and all ToolMessages whose
    #     triggering assistant/tool_calls message does not (or no longer) exist.
    #     """
    
    #     valid_tool_ids = {
    #         t["id"]
    #         for m in history
    #         if isinstance(m, AIMessage) and m.additional_kwargs.get("tool_calls")
    #         for t in m.additional_kwargs["tool_calls"]
    #     }

  
    #     cleaned = []
    #     for m in history:
    #         if isinstance(m, RemoveMessage):
    #             continue                                
    #         if isinstance(m, ToolMessage) and m.tool_call_id not in valid_tool_ids:
    #             continue                              
    #         cleaned.append(m)

    #     return cleaned
    def _clean_history_for_llm(self, history):
        """
        Removes RemoveMessages and all ToolMessages whose triggering assistant/tool_calls
        message does not (or no longer) exist.
        """
        # 🔧 GPT-5: tool_calls hängen am Top-Level-Attribut `tool_calls`, nicht in additional_kwargs
        valid_tool_ids = set()
        for m in history:
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                for t in m.tool_calls:
                    # LangChain liefert meist Dicts, aber wir sind defensiv:
                    if isinstance(t, dict):
                        valid_tool_ids.add(t.get("id"))
                    else:
                        valid_tool_ids.add(getattr(t, "id", None))

        cleaned = []
        for m in history:
            if isinstance(m, RemoveMessage):
                continue
            if isinstance(m, ToolMessage) and m.tool_call_id not in valid_tool_ids:
                # Nur ToolMessages droppen, die keinem existierenden Call zugeordnet sind
                continue
            cleaned.append(m)

        return cleaned

    def get_format_msg(self) -> str:
        parser = JsonOutputParser(pydantic_object=AgentResponseFormat)
        format_instructions = parser.get_format_instructions()
        format_msg = SystemMessage(
            content=format_instructions,
            additional_kwargs={"internal": True}
        )
        return format_msg

    # @log_execution()
    # def get_system_message(self, state: ComplexState) -> SystemMessage:
    #     """
    #     Returns the system message for the assistant, including current date and time.
    #     """

        
    #     # Define Berlin timezone so it works in any timezone
    #     berlin_tz = pytz.timezone('Europe/Berlin')
    #     now_berlin = datetime.datetime.now(berlin_tz)

    #     current_day = now_berlin.strftime("%A, %d.%m.%Y")
    #     current_time = now_berlin.strftime("%H:%M")
    #     output_schema = self.get_format_instructions()
    #     base_sys = self.get_prompt_from_langsmith("assistant-system-message")\
    #         .format_prompt(
    #             user_name       = state["user"].get("name", "Anonym"),
    #             current_day     = current_day,
    #             current_time    = current_time,
    #             output_schema   = output_schema,
    #         ).to_messages()
    #     return base_sys 
    @log_execution()
    def get_system_message(self, state: ComplexState) -> SystemMessage:
        # fetch system message every 15 minutes -> for TdN set to 1 Min. So its nearly on time
        if not self._last_system_msg_fetch or (time.time() - self._last_system_msg_fetch) > 60:
            berlin_tz = pytz.timezone('Europe/Berlin')
            now_berlin = datetime.datetime.now(berlin_tz)

            current_day = now_berlin.strftime("%A, %d.%m.%Y")
            current_time = now_berlin.strftime("%H:%M")
            output_schema = self.get_format_instructions()
            template = get_prompt_template_with_placeholders(
                "assistant_system_message",
                user_name=state["user"].get("name", "Anonym"),
                current_day=current_day,
                current_time=current_time,
                output_schema=output_schema,
            )
            system_msg = [SystemMessage(content=template, additional_kwargs={"internal": True})]
            self.current_system_msg = system_msg
            self._last_system_msg_fetch = time.time()
        else:
            system_msg = self.current_system_msg
        return system_msg
    def _remap_tool_call_ids_for_openai(self, messages):
        """Mappt ToolMessage.tool_call_id (call_*) auf die von OpenAI erwarteten fc_* IDs."""
        id_map = {}
        out = []
        for m in messages:
            if isinstance(m, AIMessage):
                mapping = (m.additional_kwargs or {}).get("__openai_function_call_ids__")
                if isinstance(mapping, dict):
                    id_map.update(mapping)
            if isinstance(m, ToolMessage) and m.tool_call_id in id_map:
                out.append(m.model_copy(update={"tool_call_id": id_map[m.tool_call_id]}))
            else:
                out.append(m)
        return out
    @log_execution()
    def respond(self, state: ComplexState):


        system_message = self.get_system_message(state)



        history_raw = state["messages"]

        history = self._clean_history_for_llm(history_raw)
        all_suggestions = _collect_all_suggestions(history)
        suggestions_msg = _make_suggestions_msg_all(all_suggestions)

        last_user_idx = max(
            i for i, m in enumerate(history) if isinstance(m, HumanMessage)
        )
        history_before_last = history[:last_user_idx]
        last_user           = history[last_user_idx]
        history_after_last  = history[last_user_idx+1:]
        summary_msg = []
        if state.get("summary"):
            summary_msg = [SystemMessage(
                content=f"<SUMMARY>\n{state['summary']}\n</SUMMARY>"
            )]
        context = state.get("context", {})
        gen_ctx_msg = []
        if context and context.get("location"):
            gen_ctx_payload = {
                "mentioned_products": context.get("mentioned_products", []),
                "location":           context.get("location"),

        }
            gen_ctx_msg = SystemMessage(
                content=f"<GEN-CONTEXT>\n{json.dumps(gen_ctx_payload, ensure_ascii=False)}\n</GEN-CONTEXT>",
                additional_kwargs={"internal": True}
            )
            gen_ctx_msg = [gen_ctx_msg]

        cur_ctx_msg = []
        if context and context.get("current_products"):
            cur_ctx_payload = {
                "current_products": context.get("current_products", []),
                "timestamp_utc":    context.get("last_message_utc"),
            }

            cur_ctx_msg = SystemMessage(
                content=f"<CURRENT-CONTEXT>\n{json.dumps(cur_ctx_payload, ensure_ascii=False)}\n</CURRENT-CONTEXT>",
                additional_kwargs={"internal": True}
            )
            cur_ctx_msg = [cur_ctx_msg]

        messages_for_llm = (
            system_message +
            summary_msg +
            gen_ctx_msg +
            history_before_last +
            ( [suggestions_msg] if suggestions_msg else [] ) +
            cur_ctx_msg +   #  Current Context direkt vor User
            [last_user] + # last user message
            history_after_last # required for tool calls to work properly
        )
        
        llm, _  = self.init_llm_and_tools()

        raw_ai: AIMessage = llm.invoke(messages_for_llm)
 

        return {
            "messages": [raw_ai],
            "messages_history": [last_user, raw_ai],
        }

    # def custom_tools_condition(self, state: ComplexState) -> str:
    #     tool_call_messages = [
    #         msg for msg in state["messages"]
    #         if isinstance(msg, AIMessage) and msg.additional_kwargs.get("tool_calls")
    #     ]
    #     tool_responses = {
    #         msg.tool_call_id for msg in state["messages"]
    #         if isinstance(msg, ToolMessage)
    #     }
    #     for msg in reversed(tool_call_messages):
    #         for tool_call in msg.additional_kwargs["tool_calls"]:
    #             if tool_call["id"] not in tool_responses:
    #                 return tool_call["function"]["name"]
    #     return "format_output"
    def custom_tools_condition(self, state: ComplexState) -> str:
        msg = state["messages"][-1]
        if getattr(msg, "tool_calls", None):
            return "custom_tools"
        return "format_output"


    def get_format_instructions(self, pydantic_object=AgentResponseFormat) -> str:
        parser = JsonOutputParser(pydantic_object=pydantic_object)
        return parser.get_format_instructions()
    # def get_schema_hint_msg(self):
    #     parser = JsonOutputParser(pydantic_object=AgentResponseFormat)
    #     instr = parser.get_format_instructions()
    #     return SystemMessage(
    #         content=(
    #             "Wenn du **fertig** bist und KEIN weiteres Tool brauchst, "
    #             "antworte ausschließlich im folgenden JSON-Format:\n\n"
    #             f"{instr}\n\n"
    #             "Wenn du ein Tool aufrufen willst, mach das wie gewohnt und ignoriere das Schema."
    #         ),
    #         additional_kwargs={"internal": True}
    #     )
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
        profile = self.user_db.get_user(user_id) or {}
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

 
        last_msg = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            None,
        )
        if last_msg is None:
            return {}                     # defensive: should never happen

        meta = last_msg.metadata or {}

        
        new_ctx: Dict[str, Any] = {}

  
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


        if "location" in meta:
            new_ctx["location"] = meta["location"]


        new_ctx["last_message_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
       
        return {"context": new_ctx} if new_ctx else {}

    @log_execution()
    def format_output(self, state: ComplexState):
        last_ai = next(
            m for m in reversed(state["messages"])
            if isinstance(m, AIMessage) and not m.additional_kwargs.get("tool_calls")
        )
        # raw = last_ai.content
        # try:
        #     if isinstance(raw, list):
        #         raw = raw[0]["text"]
        #     if raw.startswith("```"):
        #         raw = raw.strip("`").split("\n", 1)[1]  
        #     if isinstance(raw, str):
        #         structured = AgentResponseFormat.model_validate_json(raw)
        #     elif isinstance(raw, dict):
        #         structured = AgentResponseFormat.model_validate(raw)
        #     else:
        #         structured = AgentResponseFormat.model_validate_json(json.dumps(raw))
        
        raw = last_ai.content
        try:
            if isinstance(raw, list):
                raw = raw[0].get("text", "")

            if isinstance(raw, str):
                raw_str = raw.strip()

                # Falls Antwort im Codeblock zurückkommt
                if raw_str.startswith("```"):
                    raw_str = raw_str.strip("`").split("\n", 1)[1]

                # Prüfen ob es wie JSON aussieht
                if raw_str.startswith("{") or raw_str.startswith("["):
                    structured = AgentResponseFormat.model_validate_json(raw_str)
                else:
                    ic(raw_str)
                    raise ValueError("Antwort ist kein JSON, sondern freier Text.")

            elif isinstance(raw, dict):
                structured = AgentResponseFormat.model_validate(raw)

            else:
                # alles andere serialisieren
                structured = AgentResponseFormat.model_validate_json(json.dumps(raw))
        except Exception as e:
            print("Format Fallback triggered")

            fmt_llm   = self.init_formatter_llm()
            format_msg = self.get_format_msg()
            further_instruction = """
            Sollte in der Antwort ein Bild als image_path enthalten sein, dann strukturiere es so:
            image_path: url
            Beides ohne Anführungszeichen. Dies ist wichtig, damit es im Frontend korrekt dargestellt werden kann.
            """
            format_msg.content += further_instruction
            # clean_ai  = self._strip_tool_calls_none(last_ai)

            # Optional: statt AIMessage → HumanMessage(content=clean_ai.content)
            # human_last = HumanMessage(content=clean_ai.content)
            structured = fmt_llm.invoke([format_msg, last_ai])
        sugs = structured.suggestions or []  # None -> []
        ai_msg = AIMessage(
            content=structured.response,
            additional_kwargs={
                "internal": True,
                "suggestions": sugs,
            },
        )
        return {
            "structured_response": structured.model_dump(),
            "messages": [ai_msg],
            "messages_history":  [ai_msg], # typically no HumanMessage here because user had no turn # gpt suggested state.get("messages_history", []) 
        }

    # def create_graph(self) -> CompiledStateGraph:

    #     agent_flow = StateGraph(ComplexState)

    #     agent_flow.add_node("load_user_profile", self.load_user_profile)
    #     agent_flow.add_node("extract_context",   self.extract_context)
    #     agent_flow.add_node("agent",             self.agent)            # tool caller
    #     agent_flow.add_node("format_output",     self.format_output)    # structured output
    #     agent_flow.add_node("summarize_conversation", summarize_conversation)

    #     #Tools
    #     chroma_dir  = Path(os.getenv("CHROMA_PRODUCT_DB", "chroma_db"))
    #     rag_tool    = get_retriever_tool("retrieve_products", "chroma", chroma_dir=chroma_dir)
    #     stock_tool  = get_tool("fetch_product_stock")
    #     product_info_tool = get_tool("get_product_information_by_id")
    #     producer_info_tool = get_tool("get_producer_information_by_identifier")
    #     agent_flow.add_node("retrieve_products",   ToolNode([rag_tool]))
    #     agent_flow.add_node("fetch_product_stock", ToolNode([stock_tool]))
    #     agent_flow.add_node("get_product_information_by_id", ToolNode([product_info_tool]))
    #     agent_flow.add_node("get_producer_information_by_identifier", ToolNode([producer_info_tool]))

    #     agent_flow.set_entry_point("load_user_profile")
    #     agent_flow.add_edge("load_user_profile", "extract_context")
    #     agent_flow.add_edge("extract_context",   "agent")

    #     # --- ONLY ONE conditional router from "agent" ---
    #     agent_flow.add_conditional_edges(
    #         "agent",
    #         self.custom_tools_condition,
    #         {
    #             "retrieve_products": "retrieve_products",
    #             "fetch_product_stock": "fetch_product_stock",
    #             "format_output": "format_output",
    #         }
    #     )

    #     agent_flow.add_edge("retrieve_products",   "agent")
    #     agent_flow.add_edge("fetch_product_stock", "agent")

    #     # --- Summary decision AFTER formatting ---
    #     agent_flow.add_conditional_edges(
    #         "format_output",
    #         check_summary,
    #         {
    #             "summarize_conversation": "summarize_conversation",
    #             END: END,
    #         }
    #     )

    #     agent_flow.add_edge("summarize_conversation", END)

    #     cp = get_checkpoint(type=self.config.get("checkpoint_type", "sqlite"))


    #     graph = agent_flow.compile(checkpointer=cp)

    #     return graph
    def create_graph(self) -> CompiledStateGraph:
        agent_flow = StateGraph(ComplexState)

        # --------- Nodes, die nichts mit Tools zu tun haben ----------
        agent_flow.add_node("load_user_profile", self.load_user_profile)
        agent_flow.add_node("extract_context",   self.extract_context)
        agent_flow.add_node("respond",             self.respond)            # LLM / Tool-Caller
        agent_flow.add_node("format_output",     self.format_output)    # structured output
        agent_flow.add_node("summarize_conversation", summarize_conversation)

        # --------- EIN ToolNode für alle Farmely-Tools ----------
        tools = get_farmely_tools()                    # liefert [rag_tool, stock_tool, …]
        tool_node = ToolNode(tools)
        agent_flow.add_node("custom_tools", tool_node)

        # --------- Routing ----------
        agent_flow.set_entry_point("load_user_profile")

        agent_flow.add_edge("load_user_profile", "extract_context")
        agent_flow.add_edge("extract_context",   "respond")

        # Nur ein Conditional-Router ab "respond"
        # custom_tools_condition muss "custom_tools" oder "format_output" (oder END) zurückgeben
        agent_flow.add_conditional_edges(
            "respond",
            self.custom_tools_condition,
            {
                "custom_tools":   "custom_tools",   # führt Tool-Call(s) aus
                "format_output":  "format_output",  # Antwort ist fertig
                END:              END,              # optional, falls agent gleich fertig ist
            }
        )

        # Nach jedem Tool-Call zurück zum LLM
        agent_flow.add_edge("custom_tools", "respond")

        # --------- Zusammenfassung nach dem Formatieren ----------
        agent_flow.add_conditional_edges(
            "format_output",
            check_summary,
            {
                "summarize_conversation": "summarize_conversation",
                END:                      END,
            }
        )
        agent_flow.add_edge("summarize_conversation", END)

        # --------- Compile ----------
        cp = get_checkpoint(type=self.config.get("checkpoint_type", "sqlite"))
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
                products = get_product_by_barcode(barcode)
                products = [products] if products else []
            else:
                products = get_products_by_barcodes(barcode)
            if products:
                additional_context["mentioned_products"] = products.values() if isinstance(products, dict) else products
                additional_context["current_products"] = products.values() if isinstance(products, dict) else products
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
    @log_execution()
    def chat(self, content: dict, user:dict=None) -> Tuple[str, str]:


        user_id = user.get("user_id") if user else None
        thread_id = user.get("thread_id") if user else None
        graph = self.get_graph()
        if not user_id:
            user_id = "anonymous"
        if not thread_id:
            thread_id = f"{user_id}-{uuid.uuid4()}"
            self.user_db.add_thread(thread_id, user_id)

        config = {"configurable": {"thread_id": thread_id}}
  
        graph_input = self.create_graph_input(content, user_id)
        result = graph.invoke(graph_input, config)
        message = result["messages"][-1]
        response = message.content
        suggestions = (message.additional_kwargs.get("suggestions") or [])
        return response, suggestions, thread_id


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
