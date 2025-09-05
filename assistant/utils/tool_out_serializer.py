# tool_output_serializer.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import is_dataclass, asdict
import json
import base64


from langchain_core.messages import (
    BaseMessage, AIMessage, HumanMessage, SystemMessage, ToolMessage, ChatMessage
)

def _maybe_json(text: str) -> Tuple[str, Optional[Union[dict, list]]]:
    """Versucht text -> JSON zu parsen; gibt (text, obj|None) zurück."""
    s = (text or "").strip()
    if not s:
        return text, None
    if s.startswith("{") or s.startswith("["):
        try:
            return text, json.loads(s)
        except Exception:
            return text, None
    return text, None

def _is_pydantic_model(obj: Any) -> bool:
    return hasattr(obj, "model_dump") or hasattr(obj, "dict")

def _to_jsonable(obj: Any, *, max_bytes_preview: int = 8_192) -> Any:
    """Konvertiert beliebige Python-Objekte in etwas, das json.dumps verkraftet."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, bytes):
        # kleine Bytes als Base64, große nur Anriss
        if len(obj) <= max_bytes_preview:
            return {"__bytes_b64__": base64.b64encode(obj).decode("ascii")}
        return {"__bytes_len__": len(obj)}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(x, max_bytes_preview=max_bytes_preview) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v, max_bytes_preview=max_bytes_preview) for k, v in obj.items()}
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj), max_bytes_preview=max_bytes_preview)
    if _is_pydantic_model(obj):
        try:
            # pydantic v2
            return _to_jsonable(obj.model_dump(), max_bytes_preview=max_bytes_preview)  # type: ignore[attr-defined]
        except Exception:
            try:
                # pydantic v1
                return _to_jsonable(obj.dict(), max_bytes_preview=max_bytes_preview)  # type: ignore[attr-defined]
            except Exception:
                pass
    # Fallback: repr (gekürzt)
    r = repr(obj)
    return r if len(r) <= 10_000 else (r[:9_900] + "…")

def _extract_message_id(msg: Any) -> Optional[str]:
    """Robust message_id ermitteln (id, response_metadata.id, additional_kwargs.id)."""
    mid = getattr(msg, "id", None)
    if isinstance(mid, (str, int)) and str(mid).strip():
        return str(mid)
    rm = getattr(msg, "response_metadata", None)
    if isinstance(rm, dict):
        x = rm.get("id") or rm.get("message_id")
        if isinstance(x, (str, int)) and str(x).strip():
            return str(x)
    ak = getattr(msg, "additional_kwargs", None)
    if isinstance(ak, dict):
        x = ak.get("id") or ak.get("message_id")
        if isinstance(x, (str, int)) and str(x).strip():
            return str(x)
    return None

def _role_of(msg: Any) -> str:
    if isinstance(msg, AIMessage):
        return "assistant"
    if isinstance(msg, HumanMessage):
        return "user"
    if isinstance(msg, SystemMessage):
        return "system"
    if isinstance(msg, ToolMessage):
        return "tool"
    if isinstance(msg, ChatMessage):
        # generischer ChatMessage mit freiem "role"
        return getattr(msg, "role", "chat")
    return "unknown"

# ---------- Content-Extraktion ----------

def _extract_content_blocks(raw: Any) -> Tuple[Optional[str], List[Dict[str, Any]], Optional[Union[dict, list]]]:
    """
    Extrahiert aus Message.content:
      - text: str|None
      - images: Liste vereinheitlichter Bild-Refs
      - parsed_json: dict/list, falls content (oder Text) parsebares JSON enthält
    """
    # 1) String-Inhalt
    if isinstance(raw, str):
        text, parsed = _maybe_json(raw)
        return text, [], parsed

    # 2) Content Blocks (LangChain v1 Standard / Provider-native)
    images: List[Dict[str, Any]] = []
    texts: List[str] = []
    parsed_json: Optional[Union[dict, list]] = None

    if isinstance(raw, list):
        for part in raw:
            if not isinstance(part, dict):
                # Provider kann auch Strings mischen
                if isinstance(part, str):
                    texts.append(part)
                continue

            typ = part.get("type") or part.get("kind")  # großzügig
            if typ == "text":
                t = part.get("text", "")
                texts.append(t)
                # evtl. JSON im Text?
                if parsed_json is None:
                    _, parsed_json = _maybe_json(t)
            elif typ in ("image_url", "image"):
                # Vereinheitlichte Ausgabe
                if "image_url" in part:
                    url_or_obj = part["image_url"]
                    if isinstance(url_or_obj, dict):
                        url = url_or_obj.get("url")
                        images.append({"url": url, **{k: v for k, v in url_or_obj.items() if k != "url"}})
                    else:
                        images.append({"url": url_or_obj})
                elif "data" in part:  # LC "image" block mit base64
                    images.append({
                        "data_b64": part.get("data"),
                        "mime_type": part.get("mime_type"),
                        "source_type": part.get("source_type", "base64"),
                    })
            else:
                # Unbekannte Blocks trotzdem mitschreiben (jsonable)
                images.append({"__non_text_block__": _to_jsonable(part)})

    text_joined = " ".join([t for t in texts if t]).strip() or None
    return text_joined, images, parsed_json

# ---------- Public API ----------

def serialize_message(msg: Any) -> Dict[str, Any]:
    """
    Macht ein LangChain-Message-Objekt (inkl. ToolMessage) JSON-serialisierbar.
    Gibt immer ein dict zurück.
    """
    base: Dict[str, Any] = {
        "role": _role_of(msg),
        "message_id": _extract_message_id(msg),
        "additional_kwargs": _to_jsonable(getattr(msg, "additional_kwargs", None)) or None,
        "response_metadata": _to_jsonable(getattr(msg, "response_metadata", None)) or None,
        "metadata": _to_jsonable(getattr(msg, "metadata", None)) or None,
        "type": getattr(msg, "__class__", type("X",(object,),{})).__name__,
    }

    # ToolMessage-Spezifika
    if isinstance(msg, ToolMessage):
        base["tool_call_id"] = getattr(msg, "tool_call_id", None)
        base["name"] = getattr(msg, "name", None)
        # artifact/status sind optional, wenn vorhanden mitnehmen
        for extra in ("artifact", "status"):
            if hasattr(msg, extra):
                base[extra] = _to_jsonable(getattr(msg, extra))

    # Content extrahieren
    text, images, parsed_json = _extract_content_blocks(getattr(msg, "content", None))
    base["content_text"] = text
    base["content_images"] = images or None
    base["content_json"] = _to_jsonable(parsed_json) if parsed_json is not None else None

    return base

def serialize_tool_output(output: Any) -> Dict[str, Any]:
    """
    Serialisiert das Ergebnis einer Toolausführung (egal ob Message, dict, Pydantic, …).
    Gibt ein dict mit 'text', 'json' und 'raw' (jsonable) zurück.
    """
    # Falls das Tool direkt eine Message zurückgibt (kommt vor, z. B. ToolNode)
    if isinstance(output, BaseMessage):
        msg = serialize_message(output)
        return {
            "kind": "message",
            "message": msg,
            "text": msg.get("content_text"),
            "json": msg.get("content_json"),
            "raw": msg,  # bereits jsonable
        }

    # dict/list → direkt als JSON ausgeben
    if isinstance(output, (dict, list)):
        return {
            "kind": type(output).__name__,
            "message": None,
            "text": None,
            "json": _to_jsonable(output),
            "raw": _to_jsonable(output),
        }

    # String → ggf. JSON parsbar?
    if isinstance(output, str):
        text, parsed = _maybe_json(output)
        return {
            "kind": "str",
            "message": None,
            "text": text,
            "json": _to_jsonable(parsed) if parsed is not None else None,
            "raw": text,
        }

    # alles andere jsonable machen
    jsonable = _to_jsonable(output)
    text = None
    if isinstance(jsonable, str):
        text = jsonable if len(jsonable) <= 10_000 else (jsonable[:9_900] + "…")
    return {
        "kind": type(output).__name__,
        "message": None,
        "text": text,
        "json": jsonable if not isinstance(jsonable, str) else None,
        "raw": jsonable,
    }
