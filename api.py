from assistant import chat
from user_db import get_thread_ids_by_user_id
def chat_api(msg, img=None, user_id=None, thread_id=None):
    #TODO: make stuff
    return chat(msg, img, user_id, thread_id)
def get_thread_ids_api(user_id):
    threads = get_thread_ids_by_user_id(user_id)
    return threads