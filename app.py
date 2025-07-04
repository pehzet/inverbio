import os, json, time
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS     
from agent.assistant_cls import Agent
from icecream import ic

if os.getenv("INVERBIO_ENV") == "dev":
    from agent.env_check import load_and_check_env
    load_and_check_env()
else:

    # from firebase_admin import initialize_app
    # initialize_app()
    pass

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})      # Access-Control-Allow-Origin: *


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():

    if request.method == "OPTIONS":      # Preflight
        return ("", 204)

    data = request.get_json(silent=True) or {}
    if "msg" not in data:
        return jsonify(error="Parameter 'msg' ist erforderlich."), 400

    msg       = data.get("msg")
    img       = data.get("img")
    user_id   = data.get("user_id")
    thread_id = data.get("thread_id")

    agent = Agent()
    answer, thread_id = agent.chat(msg, img, user_id, thread_id)

    return jsonify(response=answer, thread_id=thread_id), 200



@app.route("/messages", methods=["GET", "POST", "OPTIONS"])
def get_messages_by_thread_id():

    if request.method == "OPTIONS":
        return ("", 204)

    # POST -> JSON-Body, GET -> Query-Params
    data = request.get_json(silent=True) if request.method == "POST" else request.args
    if not data or "thread_id" not in data:
        return jsonify(error="Parameter 'thread_id' ist erforderlich."), 400

    thread_id = data.get("thread_id")

    t0 = time.time()
    agent = Agent()
    print(f"Agent initialized in {time.time() - t0:.2f}s")

    t0 = time.time()
    messages = agent.get_messages_by_thread_id(thread_id)
    print(f"Messages fetched in {time.time() - t0:.2f}s")

    return jsonify(messages=messages), 200


if __name__ == "__main__":
    app.run(debug=True)
