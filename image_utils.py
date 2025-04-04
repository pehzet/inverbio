import base64
from PIL import Image
from io import BytesIO
from langchain_core.messages import HumanMessage
def _encode_image(image_data:bytes) -> str:
    return base64.b64encode(image_data).decode("utf-8")

def _decode_image(image_data):
    return base64.b64decode(image_data)

def create_msg_with_img(user_query:str, image:bytes=None, image_path:str=None) -> HumanMessage:
    '''
    Create a message with an image to be sent to the user. If no image is provided, the message will only contain the user's query.
    Args:
        user_query (str): The user's query.
        image (bytes): The image to be sent.
        image_path (str): The path to the image to be sent.
    Returns:
        HumanMessage: The message to be sent to the user.
    '''
    print(image)
    if not image and not image_path:
        message = HumanMessage(content=[{"type": "text", "text": user_query}])
        return message

    if image_path and not image:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            image_data = _encode_image(image_data)
    else:
        image_data = _encode_image(image)

    message = HumanMessage(
        content=[
            {"type": "text", "text": user_query},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_data.strip()}"},
            },
        ],
    )
    return message

if __name__ == "__main__":
    with open("test_img.png", "rb") as image_file:
        image_data = image_file.read()
    msg = "What is in this image?"
    msg_object = create_msg_with_img(msg, image_data)

