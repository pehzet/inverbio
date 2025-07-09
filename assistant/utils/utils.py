
from copy import deepcopy
from typing import Any, Dict, Optional

def render_graph_to_image(graph, output_path="graph.png",):
    img = graph.get_graph().draw_mermaid_png()
    with open(output_path, "wb") as f:
        f.write(img)
    print(f"Graph image saved to {output_path}")


def merge_dicts(old: Optional[Dict[str, Any]],
                new: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    LangGraph aggregator that **deep-merges** two dictionaries
    without mutating either input.

    Rules
    -----
    • If *old* is None → return a (deep-)copy of *new*  
    • If *new* is None → return a (deep-)copy of *old*  
    • Otherwise walk through *new*:
        – If the current key exists in *old* **and** both values are dicts,
          recurse to merge them.
        – In every other case the *new* value replaces the *old* one.
    • The returned dict is a brand-new object, so LangGraph can treat
      the operation as pure and deterministic.

    The function is **idempotent** and has no side effects, which keeps
    state-checkpoints reproducible.
    """
    if old is None:
        return deepcopy(new) if new is not None else {}

    if new is None:
        return deepcopy(old)

    merged = deepcopy(old)  # never mutate the original

    for key, new_val in new.items():
        old_val = merged.get(key)
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            merged[key] = merge_dicts(old_val, new_val)  # recurse
        else:
            merged[key] = deepcopy(new_val)

    return merged
