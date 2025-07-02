


from firebase_functions import https_fn, options 
from firebase_admin import initialize_app
import json
import os
import time
from agent.assistant_cls import Agent
from icecream import ic
if os.environ.get("INVERBIO_ENV") == "dev":
    from agent.env_check import load_and_check_env
    load_and_check_env()
else:
    initialize_app()
SECRETS = ["LANGSMITH_TRACING", "LANGSMITH_ENDPOINT", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT", "OPENAI_API_KEY", "FARMELY_HOST", "FARMELY_API_KEY"]
RESPONSE_HEADERS = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
@https_fn.on_request(timeout_sec=300, memory=options.MemoryOption.GB_1, secrets=SECRETS)
def chat(req: https_fn.Request):

    if req.method == 'OPTIONS':
        return https_fn.Response('', status=204, headers=RESPONSE_HEADERS)
    if req.method != 'POST':
        response = {
            "error": "Only POST allowed."
        }
        response = json.dumps(response)
        return https_fn.Response(response, status=405)


    data = req.get_json(silent=True)
    if not data or "msg" not in data:
        response = {
            "error": "Parameter 'msg' ist erforderlich."
        }
        response = json.dumps(response)
        return https_fn.Response(response, status=400)
 
    keys = data.keys()

    msg = data.get("msg")
    img = data.get("img")

    user_id = data.get("user_id")
    thread_id = data.get("thread_id")

    agent = Agent()
    answer, thread_id = agent.chat(msg, img, user_id, thread_id)
   
    response = {
        "response": answer,
        "thread_id": thread_id
    }
    response = json.dumps(response)
    ic(response)
    return https_fn.Response(response, status=200, headers=RESPONSE_HEADERS)

@https_fn.on_request(timeout_sec=300, memory=options.MemoryOption.GB_1, secrets=SECRETS)
def get_messages_by_thread_id(req: https_fn.Request):
    if req.method == 'OPTIONS':
        return https_fn.Response('', status=204, headers=RESPONSE_HEADERS)
    if req.method == 'POST':
        data = req.get_json(silent=True)
    elif req.method == 'GET':
        data = req.args
    else:
        response = {
            "error": "Only POST or GET allowed."
        }
        response = json.dumps(response)
        return https_fn.Response(response, status=405)
    if not data or "thread_id" not in data:
        response = {
            "error": "Parameter 'thread_id' ist erforderlich."
        }
        response = json.dumps(response)
        return https_fn.Response(response, status=400)
    thread_id = data.get("thread_id")
    t0 = time.time()
    agent = Agent()
    t1 = time.time()
    print(f"Agent initialized in {t1 - t0:.2f} seconds")
    t0 = time.time()
    messages = agent.get_messages_by_thread_id(thread_id)
    t1 = time.time()
    print(f"Messages fetched in {t1 - t0:.2f} seconds")
    response = {
        "messages": messages
    }
    response = json.dumps(response)

    return https_fn.Response(response, status=200, headers=RESPONSE_HEADERS)

# def chat_history(req: https_fn.Request):
#     if req.method != 'GET':
#         response = {
#             "error": "Only GET allowed."
#         }
#         response = json.dumps(response)
#         return https_fn.Response(response, status=405)


#     data = req.get_json(silent=True)
#     if not data or "user_id" not in data:
#         response = {
#             "error": "Parameter 'user_id' ist erforderlich."
#         }
#         response = json.dumps(response)
#         return https_fn.Response(response, status=400)
 

#     user_id = data.get("user_id")
#     agent = Agent()
#     threads = agent.get_threads(user_id)
#     response = {
#         "threads": threads
#     }
#     response = json.dumps(response)
#     return https_fn.Response(response, status=200)