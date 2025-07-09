import os, json, time
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS     
from assistant.agent import Agent
from assistant.agent_config import AgentConfig
from icecream import ic
from barcode.barcode import get_product_by_barcode
if os.getenv("INVERBIO_ENV") == "dev":
    from assistant.env_check import load_and_check_env
    load_and_check_env()
else:

    # from firebase_admin import initialize_app
    # initialize_app()
    pass

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})      # Access-Control-Allow-Origin: *

agent_config = AgentConfig.as_default()
agent = Agent(agent_config)
@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():

    data = request.get_json(silent=True) or {}
    if "msg" not in data:
        return jsonify(error="Parameter 'msg' ist erforderlich."), 400

    msg       = data.get("msg")
    img       = data.get("img")
    user_id   = data.get("user_id")
    thread_id = data.get("thread_id")

   
    answer, thread_id = agent.chat(msg, img, user_id, thread_id)

    return jsonify(response=answer, thread_id=thread_id), 200



@app.route("/messages", methods=["GET", "POST", "OPTIONS"])
def get_messages_by_thread_id():

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

@app.route("/product_by_barcode", methods=["GET", "OPTIONS"])
def get_product_by_barcode_route():

    barcode = request.args.get("barcode")
    if not barcode:
        return jsonify(error="Parameter 'barcode' ist erforderlich."), 400

    product_info = get_product_by_barcode(barcode)
    if not product_info:
        return jsonify(exists=False, product_info={}), 404

    return jsonify(exists=True, product_info=product_info), 200
