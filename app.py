import streamlit as st
from assistant import chat, get_messages_by_thread_id
import random
st.title("Farmo - your assistant at farmely")
if not "user_id" in st.session_state:
    st.session_state["user_id"] = None
if not "thread_id" in st.session_state:
    st.session_state["thread_id"] = None

def set_user_id(user_id):
    st.session_state.user_id = user_id


def set_thread_id(thread_id=None):
    st.session_state.thread_id = thread_id

st.text_input("User ID", on_change=set_user_id)
st.text_input("Thread ID", on_change=set_thread_id)

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
        response, thread_id = chat(prompt, thread_id=st.session_state.thread_id)
        st.session_state.thread_id = thread_id
        st.rerun()