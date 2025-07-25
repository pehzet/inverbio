# context_utils.py
# heavier context extraction helpers
from typing import Dict, Any, List
import datetime as _dt
from langgraph.types import StateSnapshot
from barcode.barcode import get_product_by_barcode, get_products_by_barcodes
from assistant.agent.utils import get_berlin_now

def create_additional_context(
    state: StateSnapshot,
    content: Dict[str, Any],
    user: Dict[str, Any]
) -> Dict[str, Any]:
    """Build extra context dict from incoming message payload.

    Args:
        state: Current graph snapshot (unused, but kept for symmetry).
        content: Front-end payload (may hold 'barcode').
        user: User profile (unused here).

    Returns:
        Dict with keys ``mentioned_products``, ``current_products`` and
        ``last_message_utc`` when applicable, else empty dict.
    """
    ctx: Dict[str, Any] = {}
    barcode = content.get("barcode")

    products: List[dict] = []
    if barcode:
        if isinstance(barcode, str):
            prod = get_product_by_barcode(barcode)
            products = [prod] if prod else []
        else:
            prods = get_products_by_barcodes(barcode)
            products = list(prods.values()) if isinstance(prods, dict) else prods

    if products:
        ctx["mentioned_products"] = products
        ctx["current_products"] = products

    ctx["last_message_utc"] = get_berlin_now()
    return ctx if len(ctx) > 1 else {}
