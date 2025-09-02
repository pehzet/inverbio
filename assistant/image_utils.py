import base64
from PIL import Image
from io import BytesIO
import mimetypes
import re
from langchain_core.messages import HumanMessage
from typing import Iterable, Optional
def _encode_image(image_data:bytes) -> str:
    return base64.b64encode(image_data).decode("utf-8")

def _decode_image(image_data):
    return base64.b64decode(image_data)

_DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<b64>.+)$", re.IGNORECASE)


# --- Hilfsfunktionen ---------------------------------------------------------

def _is_data_url(s: str) -> bool:
    return bool(_DATA_URL_RE.match(s.strip()))


def _extract_mime_from_data_url(s: str) -> Optional[str]:
    m = _DATA_URL_RE.match(s.strip())
    return m.group("mime").lower() if m else None


def _encode_image(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _build_data_url(mime: str, b64: str) -> str:
    return f"data:{mime};base64,{b64}"


def _mime_from_extension(path: str) -> Optional[str]:
    extras = {
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".jfif": "image/jpeg",
        ".jpe": "image/jpeg",
        ".tif": "image/tiff",
    }
    for ext, mime in extras.items():
        if path.lower().endswith(ext):
            return mime
    mime, _ = mimetypes.guess_type(path)
    return mime


def _mime_from_bytes(raw: bytes) -> Optional[str]:
    """
    Nutzt Pillow, um das Format zu erkennen. Liefert den passenden MIME-Typ zurück.
    """
    try:
        with Image.open(BytesIO(raw)) as img:
            fmt = (img.format or "").lower()
    except Exception:
        return None

    format_to_mime = {
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "webp": "image/webp",
    }
    return format_to_mime.get(fmt)


def _normalize_image_string(img_str: str) -> str:
    """
    Wandelt einen Base64-String oder eine data:-URL in eine gültige data:-URL mit erkanntem MIME-Typ um.
    """
    s = img_str.strip()
    if _is_data_url(s):
        return s

    try:
        raw = base64.b64decode(s, validate=True)
    except Exception:
        raise ValueError(
            "Bild-String ist weder eine gültige data:-URL noch ein gültiger Base64-String."
        )

    mime = _mime_from_bytes(raw) or "image/png"
    return _build_data_url(mime, _encode_image(raw))


def _make_image_content_item(data_url: str) -> dict:
    return {
        "type": "image_url",
        "image_url": {"url": data_url}
    }


# --- Hauptfunktion -----------------------------------------------------------

def create_msg_with_img(
    user_query: str,
    images: Optional[Iterable[str]] = None,
    image_path: Optional[str] = None
) -> HumanMessage:
    """
    Erzeugt eine HumanMessage mit Text und optional einem oder mehreren Bildern.
    Unterstützt mehrere Bildtypen (png, jpg/jpeg, gif, webp, bmp, tiff, svg).
    """
    content: list[dict] = []

    if images:
        for img_str in images:
            data_url = _normalize_image_string(img_str)
            content.append(_make_image_content_item(data_url))

    elif image_path:
        with open(image_path, "rb") as f:
            raw = f.read()

        mime = _mime_from_extension(image_path) or _mime_from_bytes(raw) or "image/png"
        b64 = _encode_image(raw)
        data_url = _build_data_url(mime, b64)
        content.append(_make_image_content_item(data_url))
    text = {"type": "text", "text": user_query}
    content.append(text)
    return HumanMessage(content=content)
if __name__ == "__main__":
    with open("assistant/graph.png", "rb") as image_file:
        image_data = image_file.read()

    msg = "What is in this image?"
    b64 = base64.b64encode(image_data).decode("ascii")
    msg_object = create_msg_with_img(msg, images=[b64])  # Liste von Strings!
    print(msg_object)

