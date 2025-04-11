import streamlit as st
from assistant import chat, get_messages_by_thread_id
import random
from api import chat_api, get_thread_ids_api


st.title("Farmo - your assistant at farmely")

# Initialisiere Session State
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = None
if "selected_thread" not in st.session_state:
    st.session_state["selected_thread"] = None
if "input_thread_id" not in st.session_state:
    st.session_state["input_thread_id"] = ""

# Callback zum Setzen der thread_id
def update_thread_id():
    input_id = st.session_state.input_thread_id
    selected = st.session_state.selected_thread
    st.session_state.thread_id = input_id if input_id else selected

# Callback zum Setzen der user_id
def set_user_id(user_id):
    st.session_state.user_id = user_id

# Eingabe User ID
user_id = st.text_input("User ID", value=st.session_state.user_id or "")
if user_id:
    set_user_id(user_id)

# Zeige aktuelle User ID
if st.session_state.user_id:
    st.markdown(f"**User ID:** {st.session_state.user_id}")
    threads = get_thread_ids_api(user_id=st.session_state.user_id)
else:
    threads = []

# Manuelle Eingabe Thread ID
st.text_input("Enter Thread ID manually (optional)", key="input_thread_id", on_change=update_thread_id)

# Auswahl aus bestehenden Threads
if threads:
    st.selectbox("Or select a thread", options=threads, key="selected_thread", on_change=update_thread_id)



# Button für neuen Thread
new_thread = st.button("Start new thread")
if new_thread:
    st.session_state.thread_id = None

# Zeige aktuelle Thread ID
if st.session_state.thread_id:
    st.markdown(f"**Thread ID:** {st.session_state.thread_id}")




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
        st.session_state.thread_id = thread_id
        st.rerun()