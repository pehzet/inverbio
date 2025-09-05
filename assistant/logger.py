import functools
import logging
from typing import Any, Callable, Optional, Type, Dict, List
import time
from datetime import datetime, timezone, timedelta
import datetime as dt
from pathlib import Path
import json
from langchain_core.callbacks import BaseCallbackHandler



def get_assistant_logger(
    name: str = "assistant_logger",
    level: int = logging.INFO,
    fmt: str = "%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
    handler: Optional[logging.Handler] = None,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Creates (or returns, if already existing) a logger named 'assistant_logger'.
    Also writes all INFO and DEBUG messages to a timestamped log file.

    :param name:    Name of the logger (default: "assistant_logger")
    :param level:   Logging level for console (default: INFO)
    :param fmt:     Format string for log messages
    :param datefmt: Date format for log timestamps
    :param handler: Optional custom console handler.
                    If None, a StreamHandler with the default formatter is created.
    :param log_dir: Directory where the log file will be created (default: current directory)
    :return:        Configured Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # capture everything DEBUG and above

    if not logger.handlers:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        # 1) Console handler at specified level
        console_handler = handler or logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 2) File handler capturing INFO and DEBUG with timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logfile = f"{log_dir}/assistant_{timestamp}.log"
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Prevent log messages from being propagated to the root logger
        logger.propagate = False

    return logger
def log_execution(
    level_success: int = logging.INFO,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that wraps every function in a try/except block.
    
    - On successful execution, logs at `level_success`.
    - On exception, logs at `level_error` and re-raises the exception.
    
    :param level_success: Logging level for successful execution (default: INFO)
    :param level_error:   Logging level for exceptions (default: ERROR)
    :param logger:        Optional logger instance. If None, uses a logger named after the function’s module.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        log = get_assistant_logger() if logger is None else logger

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                _start = time.time()
                result = func(*args, **kwargs)
                log.log(
                    level_success,
                    "Function '%s' executed successfully. duration=%.2fms",
                    func.__name__,  (time.time() - _start) * 1000
                )
                return result
            except Exception as e:
                log.error("Function '%s' failed: %s",
                          func.__name__, e.__class__.__name__, exc_info=True)
                # Exception is re-raised to allow callers to handle it
                raise

        return wrapper

    return decorator


def _iso_now() -> str:
    # ISO 8601 mit UTC-Zeitzone
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"

def _to_str_safe(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        s = str(v)
        # kürzen, falls versehentlich riesige Inputs reinkommen
        return s if len(s) <= 20000 else s[:20000] + "…"
    except Exception:
        return None

def _ctx_sanitized(ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    ctx = ctx or {}
    out = {}
    for k, v in ctx.items():
        out[k] = v if isinstance(v, (int, float)) or v is None else _to_str_safe(v)
    return out
def _parse_iso_z(s: str):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

class LocalToolLogger(BaseCallbackHandler):
    """
    - Loggt Tool-Events (start/end/error) inkl. parent_run_id.
    - Loggt LLM-End-Events inkl. extrahierter message_ids.
    - Bietet API, um nachträglich Tool-Runs mit Message-IDs zu verknüpfen.

    Fileformat (JSONL), Beispielevents:
      {"event":"tool_start", "run_id":"...", "parent_run_id":"...", "tool_name":"...", "input":"...", "ts_start":"...", "user_id":"...", "thread_id":"..."}
      {"event":"tool_end",   "run_id":"...", "parent_run_id":"...", "tool_name":"...", "execution_time_s":0.12, "ts_end":"...", "user_id":"...", "thread_id":"..."}
      {"event":"tool_error", ...}
      {"event":"llm_end",    "llm_run_id":"...", "parent_run_id":"...", "message_ids":["...","..."], "ts_end":"...", "user_id":"...", "thread_id":"..."}

    Hinweis:
      - message_ids werden best effort aus LLM-Response extrahiert (versch. Clients legen IDs woanders ab).
      - Ein LLM-Run kann mehrere Messages erzeugen.
    """

    def __init__(
        self,
        logfile: str = "logs/tool_logs.jsonl",
        write_file: bool = True,
        extra_ctx: Optional[Dict[str, Any]] = None,
    ):
        self.write_file = write_file
        self.logfile = Path(logfile)
        if write_file:
            self.logfile.parent.mkdir(parents=True, exist_ok=True)
        self._ctx = _ctx_sanitized(extra_ctx)
        self._starts: Dict[str, float] = {}                    # tool run start perf counter
        self._runs: Dict[str, Dict[str, Any]] = {}             # in-memory tool runs (letzter Stand)
        self._llm_run_to_msgs: Dict[str, List[str]] = {}       # in-memory map: llm_run_id -> message_ids

    # -------- LLM lifecycle --------
    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        # message_ids extrahieren
        message_ids = self._extract_message_ids(response)
        self._llm_run_to_msgs[str(run_id)] = message_ids or []

        rec = {
            "event": "llm_end",
            "llm_run_id": str(run_id),
            "parent_run_id": _to_str_safe(parent_run_id),
            "message_ids": message_ids or [],
            "ts_end": _iso_now(),
            **self._ctx,
        }
        self._append_file(rec)

    # -------- TOOL lifecycle --------
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: str,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self._starts[run_id] = time.perf_counter()
        name = (serialized or {}).get("name") or "unknown_tool"
        rec = {
            "run_id": run_id,
            "parent_run_id": _to_str_safe(parent_run_id),
            "tool_name": _to_str_safe(name),
            "input": _to_str_safe(input_str),
            "execution_time_s": None,
            "ts_start": _iso_now(),
            "ts_end": None,
            **self._ctx,
        }
        self._runs[run_id] = rec
        self._append_file({"event": "tool_start", **rec})

    def on_tool_end(self, output: Any, *, run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        # output bewusst ignorieren!
        start = self._starts.pop(run_id, None)
        dur = (time.perf_counter() - start) if start is not None else None
        rec = self._runs.get(run_id)
        if rec:
            rec["execution_time_s"] = dur
            rec["ts_end"] = _iso_now()
            # parent_run_id ggf. aktualisieren (falls Framework es erst hier setzt)
            if parent_run_id and not rec.get("parent_run_id"):
                rec["parent_run_id"] = _to_str_safe(parent_run_id)
            self._append_file({
                "event": "tool_end",
                "run_id": rec["run_id"],
                "parent_run_id": rec.get("parent_run_id"),
                "tool_name": rec["tool_name"],
                "execution_time_s": rec["execution_time_s"],
                "ts_end": rec["ts_end"],
                "user_id": rec.get("user_id"),
                "thread_id": rec.get("thread_id"),
            })

    def on_tool_error(self, error: BaseException, *, run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        # kein error-Objekt speichern
        start = self._starts.pop(run_id, None)
        dur = (time.perf_counter() - start) if start is not None else None
        rec = self._runs.get(run_id)
        if rec:
            rec["execution_time_s"] = dur
            rec["ts_end"] = _iso_now()
            if parent_run_id and not rec.get("parent_run_id"):
                rec["parent_run_id"] = _to_str_safe(parent_run_id)
            self._append_file({
                "event": "tool_error",
                "run_id": rec["run_id"],
                "parent_run_id": rec.get("parent_run_id"),
                "tool_name": rec["tool_name"],
                "execution_time_s": rec["execution_time_s"],
                "ts_end": rec["ts_end"],
                "user_id": rec.get("user_id"),
                "thread_id": rec.get("thread_id"),
            })

    # -------- Message-ID Extraction (best effort) --------
    def _extract_message_ids(self, response: Any) -> List[str]:
        """
        Versucht, aus LangChain/LangGraph LLM-Responses Message-IDs zu ziehen.
        Unterstützt typische Strukturen:
          response.generations[*][*].message.id
          response.generations[*][*].message.response_metadata['id']
          response.generations[*][*].message.additional_kwargs['id']
          response.message (einzelne) ebenfalls geprüft.
        Fällt ansonsten auf leere Liste zurück.
        """
        ids: List[str] = []

        # 1) generations (häufigster Fall)
        gens = getattr(response, "generations", None)
        if gens:
            try:
                for genlist in gens:
                    for g in genlist:
                        msg = getattr(g, "message", None)
                        mid = self._id_from_message_obj(msg)
                        if mid:
                            ids.append(mid)
            except Exception:
                pass

        # 2) single message (manche Clients packen eine message oben drauf)
        if not ids:
            msg = getattr(response, "message", None)
            mid = self._id_from_message_obj(msg)
            if mid:
                ids.append(mid)

        # 3) raw dict fallback
        if not ids and isinstance(response, dict):
            try:
                gen = response.get("generations") or []
                for genlist in gen:
                    for g in genlist:
                        msg = g.get("message") if isinstance(g, dict) else None
                        mid = self._id_from_message_obj(msg)
                        if mid:
                            ids.append(mid)
            except Exception:
                pass

        # Duplikate entfernen, Reihenfolge beibehalten
        seen = set()
        out = []
        for x in ids:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def _id_from_message_obj(self, msg: Any) -> Optional[str]:
        if msg is None:
            return None
        # 1) direkte ID
        mid = getattr(msg, "id", None)
        if mid:
            return str(mid)
        # 2) response_metadata.id
        rm = getattr(msg, "response_metadata", None)
        if isinstance(rm, dict):
            mid = rm.get("id") or rm.get("message_id")
            if mid:
                return str(mid)
        # 3) additional_kwargs.id
        ak = getattr(msg, "additional_kwargs", None)
        if isinstance(ak, dict):
            mid = ak.get("id") or ak.get("message_id")
            if mid:
                return str(mid)
        # 4) dict-artig
        if isinstance(msg, dict):
            return msg.get("id") or (msg.get("response_metadata") or {}).get("id") \
                   or (msg.get("additional_kwargs") or {}).get("id")
        return None

    # -------- JSONL Reader --------
    def _iter_log_records(self):
        try:
            if not self.logfile.exists():
                return
            with self.logfile.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        if isinstance(rec, dict):
                            yield rec
                    except Exception:
                        continue
        except Exception:
            return
    def _build_llm_events_from_file(self) -> list[dict]:
        events = []
        for rec in self._iter_log_records() or []:
            if rec.get("event") == "llm_end":
                events.append({
                    "llm_run_id": str(rec.get("llm_run_id")),
                    "parent_run_id": str(rec.get("parent_run_id") or ""),
                    "message_ids": rec.get("message_ids") or [],
                    "ts_end": rec.get("ts_end"),
                    "thread_id": str(rec.get("thread_id") or ""),
                    "user_id": str(rec.get("user_id") or ""),
                })
        return events
    
    def get_tools_by_message_id(self, message_id: str) -> List[Dict[str, Any]]:
        runs = self._build_runs_from_file()
        llm_events = self._build_llm_events_from_file()

        # 1) Direkte Zuordnung: message_id -> llm_run_id(s)
        candidate_llm_runs = {
            e["llm_run_id"] for e in llm_events
            if str(message_id) in (e.get("message_ids") or [])
        }

        def _fmt(r):
            return {
                "run_id": _to_str_safe(r.get("run_id")),
                "parent_run_id": _to_str_safe(r.get("parent_run_id")),
                "tool_name": _to_str_safe(r.get("tool_name")),
                "input": _to_str_safe(r.get("input")),
                "execution_time_s": float(r["execution_time_s"]) if r.get("execution_time_s") is not None else None,
                "ts_start": _to_str_safe(r.get("ts_start")),
                "ts_end": _to_str_safe(r.get("ts_end")),
                "user_id": _to_str_safe(r.get("user_id")),
                "thread_id": _to_str_safe(r.get("thread_id")),
            }

        # 1a) Direkter Parent-Match (alt)
        out = [ _fmt(r) for r in runs.values() if r.get("parent_run_id") in candidate_llm_runs ]
        out.sort(key=lambda r: r.get("ts_start") or "")
        if out:
            return out

        # 2) Fallback A: Sibling-Heuristik über gemeinsamen Parent des LLM-Runs
        parents_of_llm = {
            e.get("parent_run_id") for e in llm_events
            if e["llm_run_id"] in candidate_llm_runs and e.get("parent_run_id")
        }
        sibling = [ _fmt(r) for r in runs.values() if r.get("parent_run_id") in parents_of_llm ]
        sibling.sort(key=lambda r: r.get("ts_start") or "")
        if sibling:
            return sibling

        # 3) Fallback B: Zeitfenster-Heuristik im selben Thread
        #    (typisch: Tools laufen kurz vor dem finalen LLM-Ende)
        window_sec = 120
        time_based: List[Dict[str, Any]] = []
        for e in llm_events:
            if str(message_id) not in (e.get("message_ids") or []):
                continue
            t = _parse_iso_z(e.get("ts_end") or "")
            if not t:
                continue
            t_min = t - timedelta(seconds=window_sec)
            t_max = t + timedelta(seconds=10)
            for r in runs.values():
                if _to_str_safe(r.get("thread_id")) != _to_str_safe(e.get("thread_id")):
                    continue
                r_end = _parse_iso_z(r.get("ts_end") or "")
                if r_end and t_min <= r_end <= t_max:
                    time_based.append(_fmt(r))

        time_based.sort(key=lambda r: r.get("ts_start") or "")
        return time_based
    def _build_runs_from_file(self) -> Dict[str, Dict[str, Any]]:
        """
        Rekonstruiert den letzten bekannten Zustand pro tool run_id aus der JSONL-Datei.
        """
        runs: Dict[str, Dict[str, Any]] = {}
        for rec in self._iter_log_records() or []:
            rid = rec.get("run_id")
            ev = rec.get("event")

            if ev == "tool_start" and rid:
                runs[rid] = {
                    "run_id": rec.get("run_id"),
                    "parent_run_id": rec.get("parent_run_id"),
                    "tool_name": rec.get("tool_name"),
                    "input": rec.get("input"),
                    "execution_time_s": rec.get("execution_time_s"),
                    "ts_start": rec.get("ts_start"),
                    "ts_end": rec.get("ts_end"),
                    "user_id": rec.get("user_id"),
                    "thread_id": rec.get("thread_id"),
                }
            elif ev in ("tool_end", "tool_error") and rid:
                cur = runs.get(rid, {"run_id": rid})
                for k in ("parent_run_id", "tool_name", "ts_end", "execution_time_s", "user_id", "thread_id"):
                    if rec.get(k) is not None:
                        cur[k] = rec.get(k)
                runs[rid] = cur
            # llm_end wird separat gesammelt
        return runs

    def _build_llm_map_from_file(self) -> Dict[str, List[str]]:
        """
        Baut Map: llm_run_id -> [message_ids] aus JSONL.
        """
        m: Dict[str, List[str]] = {}
        for rec in self._iter_log_records() or []:
            if rec.get("event") == "llm_end":
                lrid = rec.get("llm_run_id")
                mids = rec.get("message_ids") or []
                if lrid:
                    m[str(lrid)] = [str(x) for x in mids if isinstance(x, (str, int))]
        return m

    # -------- API (aus JSONL) --------
    def get_run_summary_by_thread_id(self, thread_id: str) -> List[Dict[str, Any]]:
        tid_safe = _to_str_safe(thread_id)
        runs = self._build_runs_from_file()
        items = [r for r in runs.values() if _to_str_safe(r.get("thread_id")) == tid_safe]
        items.sort(key=lambda r: r.get("ts_start") or "")
        out: List[Dict[str, Any]] = []
        for r in items:
            out.append({
                "run_id": _to_str_safe(r.get("run_id")),
                "parent_run_id": _to_str_safe(r.get("parent_run_id")),
                "tool_name": _to_str_safe(r.get("tool_name")),
                "input": _to_str_safe(r.get("input")),
                "execution_time_s": float(r["execution_time_s"]) if r.get("execution_time_s") is not None else None,
                "ts_start": _to_str_safe(r.get("ts_start")),
                "ts_end": _to_str_safe(r.get("ts_end")),
                "user_id": _to_str_safe(r.get("user_id")),
                "thread_id": _to_str_safe(r.get("thread_id")),
            })
        return out

    def get_run_summary_by_run_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        runs = self._build_runs_from_file()
        r = runs.get(run_id)
        if not r:
            return None
        return {
            "run_id": _to_str_safe(r.get("run_id")),
            "parent_run_id": _to_str_safe(r.get("parent_run_id")),
            "tool_name": _to_str_safe(r.get("tool_name")),
            "input": _to_str_safe(r.get("input")),
            "execution_time_s": float(r["execution_time_s"]) if r.get("execution_time_s") is not None else None,
            "ts_start": _to_str_safe(r.get("ts_start")),
            "ts_end": _to_str_safe(r.get("ts_end")),
            "user_id": _to_str_safe(r.get("user_id")),
            "thread_id": _to_str_safe(r.get("thread_id")),
        }

    # -------- Korrelationen (aus JSONL) --------
    def get_message_ids_by_llm_run_id(self, llm_run_id: str) -> List[str]:
        """
        Liest JSONL und liefert alle message_ids zu einem LLM-Run.
        """
        m = self._build_llm_map_from_file()
        return m.get(str(llm_run_id), [])

   

    def get_tool_run_with_messages(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Liefert einen Tool-Run inkl. der korrelierten message_ids (über parent_run_id -> llm_end).
        """
        runs = self._build_runs_from_file()
        rec = runs.get(run_id)
        if not rec:
            return None
        llm_map = self._build_llm_map_from_file()
        mids = llm_map.get(_to_str_safe(rec.get("parent_run_id")), [])
        enriched = {
            "run_id": _to_str_safe(rec.get("run_id")),
            "parent_run_id": _to_str_safe(rec.get("parent_run_id")),
            "tool_name": _to_str_safe(rec.get("tool_name")),
            "input": _to_str_safe(rec.get("input")),
            "execution_time_s": float(rec["execution_time_s"]) if rec.get("execution_time_s") is not None else None,
            "ts_start": _to_str_safe(rec.get("ts_start")),
            "ts_end": _to_str_safe(rec.get("ts_end")),
            "user_id": _to_str_safe(rec.get("user_id")),
            "thread_id": _to_str_safe(rec.get("thread_id")),
            "message_ids": mids,
        }
        return enriched

    # -------- In-Memory Summaries (für laufende Session) --------
    def get_run_summaries(self) -> List[Dict[str, Any]]:
        items = sorted(self._runs.values(), key=lambda r: r.get("ts_start") or "")
        out: List[Dict[str, Any]] = []
        for r in items:
            out.append({
                "run_id": _to_str_safe(r.get("run_id")),
                "parent_run_id": _to_str_safe(r.get("parent_run_id")),
                "tool_name": _to_str_safe(r.get("tool_name")),
                "input": _to_str_safe(r.get("input")),
                "execution_time_s": float(r["execution_time_s"]) if r.get("execution_time_s") is not None else None,
                "ts_start": _to_str_safe(r.get("ts_start")),
                "ts_end": _to_str_safe(r.get("ts_end")),
                "user_id": _to_str_safe(r.get("user_id")),
                "thread_id": _to_str_safe(r.get("thread_id")),
            })
        return out

    def reset(self) -> None:
        self._starts.clear()
        self._runs.clear()
        self._llm_run_to_msgs.clear()

    # -------- File IO --------
    def _append_file(self, data: Dict[str, Any]) -> None:
        if not self.write_file:
            return
        try:
            safe: Dict[str, Any] = {}
            for k, v in data.items():
                if isinstance(v, (int, float)) or v is None:
                    safe[k] = v
                else:
                    # Listen (z. B. message_ids) unverändert reinschreiben
                    if isinstance(v, list):
                        safe[k] = v
                    else:
                        safe[k] = _to_str_safe(v)
            with self.logfile.open("a", encoding="utf-8") as f:
                f.write(json.dumps(safe, ensure_ascii=False) + "\n")
        except Exception:
            # bewusst still; Logging darf keine Pipeline brechen
            pass
