import base64
from PIL import Image
from io import BytesIO
from langchain_core.messages import HumanMessage
def _encode_image(image_data:bytes) -> str:
    return base64.b64encode(image_data).decode("utf-8")

def _decode_image(image_data):
    return base64.b64decode(image_data)

def create_msg_with_img(
    user_query: str,
    images: list[str] | None = None,
    image_path: str | None = None
) -> HumanMessage:
    """
    Create a message with one or more images to be sent to the user.
    If no image is provided, the message will only contain the user's query.

    Args:
        user_query (str): The user's query.
        images (list[str], optional): A list of base64-encoded image strings
            or full data-URL strings.
        image_path (str, optional): Path to an image file (only used if images is None).

    Returns:
        HumanMessage: The message to be sent to the user.
    """
    content: list[dict] = [{"type": "text", "text": user_query}]

    if images:
        for img_str in images:
            # img_str = img_str.strip()
            # if it's already a data URL, use it verbatim
            if img_str.startswith("data:") and "base64," in img_str:
                image_data = img_str
            else:
                # otherwise assume it's raw base64 and prepend
                image_data = f"data:image/png;base64,{img_str}"
            content.append({
                "type": "image_url",
                "image_url": {"url": f"{image_data}"}
            })

    elif image_path:
        with open(image_path, "rb") as f:
            raw = f.read()
        b64 = _encode_image(raw)
        content.append({
            "type": "image_url",
            "image_url": f"data:image/png;base64,{b64}"
        })

    return HumanMessage(content=content)


if __name__ == "__main__":
    with open("test_img.png", "rb") as image_file:
        image_data = image_file.read()
    msg = "What is in this image?"
    msg_object = create_msg_with_img(msg, image_data)

