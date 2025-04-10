import streamlit as st
from assistant import chat, get_messages_by_thread_id
import random
from api import chat_api, get_threads_api
st.title("Farmo - your assistant at farmely")
if not "user_id" in st.session_state:
    st.session_state["user_id"] = None
if not "thread_id" in st.session_state:
    st.session_state["thread_id"] = None

def set_thread_id(thread_id):
    st.session_state.thread_id = thread_id
def set_user_id(user_id):
    st.session_state.user_id = user_id

user_id = st.text_input("User ID", value=st.session_state.user_id)
if user_id:
    set_user_id(user_id)
if st.session_state.user_id:
    st.markdown(f"User ID: {st.session_state.user_id}")
    threads = get_threads_api(user_id=st.session_state.user_id)
thread_id = st.text_input("Thread ID", value=st.session_state.thread_id)
if thread_id:
    set_thread_id(thread_id)
# if st.session_state.thread_id:
#     st.markdown(f"Thread ID: {st.session_state.thread_id}")
# if threads:
#     st.selectbox("Select a thread", options=threads, index=0, on_change=set_thread_id, args=(thread_id,))
# st.button("Start new thread", on_click=set_thread_id, args=(None,))


def get_messages():
    if st.session_state.thread_id:
        messages = get_messages_by_thread_id(st.session_state.thread_id)
        return messages
    return []

messages = get_messages()
if messages:
    for message in messages:
        # sometimes there are empty messages...
        if len(message['content']) > 0:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.markdown(message['content'])
                else:
                    st.markdown(message['content'])
if prompt := st.chat_input("What is up?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    waiting_msgs = ["I look in the basement", "I ask my boss", "I check the fridge", "Computer is thinking... beep boop"] 
    waiting_msg = random.choice(waiting_msgs)
    with st.spinner(waiting_msg):
        response, thread_id = chat_api(prompt, user_id=st.session_state.user_id, thread_id=st.session_state.thread_id)
        set_thread_id(thread_id)
        st.rerun()