from assistant import chat
from user_db import get_threads_by_user_id
def chat_api(msg, img=None, user_id=None, thread_id=None):
    #TODO: make stuff
    return chat(msg, img, user_id, thread_id)
def get_threads_api(user_id):
    threads = get_threads_by_user_id(user_id)
    return threads