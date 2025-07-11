import os
from pathlib import Path
is_production = os.environ.get("INVERBIO_ENV") == "prod" or os.environ.get("INVERBIO_ENV") == "production"
BASE_DIR = Path(__file__).resolve().parent          # /home/.../backend
print("Base dir:", BASE_DIR)
if is_production:
    from setup_assistant import check_setup
    BASE_DIR = Path(__file__).resolve().parent          # /home/.../backend
    print("Base dir:", BASE_DIR)
    req_var_file = BASE_DIR / "assistant" / "required_env_vars.txt"
    check_setup(required_vars_file=req_var_file)
else:
    from assistant.utils.env_check import load_and_check_env
    load_and_check_env()
    from setup_assistant import check_setup
    check_setup(required_vars_file=Path("assistant/required_env_vars.txt")) # test

import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from assistant.agent import Agent
from assistant.agent_config import AgentConfig
from icecream import ic
from barcode.barcode import get_product_by_barcode



app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})      # Access-Control-Allow-Origin: *

agent_config = AgentConfig.as_default()
agent = Agent(agent_config)
@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():

    data = request.get_json(silent=True) or {}
    content = data.get("content", None)
    if not content or content.get("msg") is None:
        return jsonify(error="Parameter 'content' with 'msg' is required."), 400
    user = data.get("user", {})

    answer, thread_id = agent.chat(content, user)

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


if __name__ == "__main__":
    os.environ["INVERBIO_ENV"] = "dev"  # Set environment variable for development
    app.run()