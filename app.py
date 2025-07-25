import os
import secrets
from functools import wraps
from pathlib import Path
import base64 
import io
import json

from PIL import Image 


is_production = os.environ.get("INVERBIO_ENV") == "prod" or os.environ.get("INVERBIO_ENV") == "production"
BASE_DIR = Path(__file__).parent
os.environ["BASE_DIR"] = str(BASE_DIR)
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
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from assistant.agent import Agent
from assistant.agent_config import AgentConfig
from icecream import ic
from barcode.barcode import get_product_by_barcode
API_KEY = os.environ.get("INVERBIO_API_KEY")  
MAX_SIDE   = 1280      # for image resize
JPEG_QUAL  = 85        # for image resize
app = Flask(__name__)
DIST_DIR = "/home/nmeseth/inverbio/frontend/dist" # TODO: add to env var
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     allow_headers=["Content-Type", "X-API-Key"]
     )     


def require_api_key(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        #  Preflight-Anfragen (OPTIONS) nicht blockieren:
        if request.method == "OPTIONS":
            return route_func(*args, **kwargs)

        key = request.headers.get("X-API-Key")          # Header-Name frei wählbar
        if key and secrets.compare_digest(key, API_KEY):
            return route_func(*args, **kwargs)

        return jsonify(error="Invalid or missing API key"), 401
    return wrapper


def _downscale_image(raw: bytes) -> bytes:
    """ verkleinert Bild auf MAX_SIDE und JPEG_QUAL, sonst unverändert """
    img = Image.open(io.BytesIO(raw))
    if max(img.size) <= MAX_SIDE:
        return raw
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUAL)
    return buf.getvalue()

def _files_to_b64(files):
    pass

agent_config = AgentConfig.as_default()
agent = Agent(agent_config)

@app.route("/")
def index():
    return send_from_directory(DIST_DIR, "index.html")

# optionaler SPA-Fallback, falls du später Unterseiten hast
@app.route("/<path:path>")
def spa_fallback(path):
    if path.startswith("api/"):        # API-Routes weiterhin an Flask
        abort(404)
    return send_from_directory(DIST_DIR, "index.html")


# @app.route("/chat", methods=["POST"])
# @require_api_key
# def chat():
  
#     data = request.get_json(silent=True) or {}

#     content = data.get("content", None)

#     if not content or content.get("msg") is None:
#         return jsonify(error="Parameter 'content' with 'msg' is required."), 400
#     user = data.get("user", {})
#     answer, thread_id = agent.chat(content, user)
#     return jsonify(response=answer, thread_id=thread_id), 200

@app.route("/chat", methods=["POST"])
@require_api_key
def chat():
    ic(request)
    ic(request.form.get("payload"))
    if request.content_type and request.content_type.startswith("multipart/"):
        payload_str = request.form.get("payload")
        if not payload_str:
            return jsonify(error="Form field 'payload' missing."), 400

        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError:
            return jsonify(error="Invalid JSON in 'payload'."), 400

        # Dateien → Base64‑Data‑URLs
        images_b64 = []
        for up in request.files.getlist("files"):
            raw = up.read()
            raw = _downscale_image(raw)           # optionales Resize
            b64 = base64.b64encode(raw).decode()
            images_b64.append(f"data:{up.mimetype};base64,{b64}")

        # JSON‑Struktur beibehalten
        data.setdefault("content", {}).setdefault("images", []).extend(images_b64)

   
    else:
        data = request.get_json(silent=True) or {}

 
    content = data.get("content") or {}
    if content.get("msg") is None:
        return jsonify(error="Parameter 'content' with 'msg' is required."), 400

    user = data.get("user", {})
    response, suggestions, thread_id = agent.chat(content, user)
    return jsonify(response=response, suggestions=suggestions, thread_id=thread_id), 200


@app.route("/messages", methods=["GET", "POST"])
@require_api_key
def get_messages_by_thread_id():

    # POST -> JSON-Body, GET -> Query-Params
    data = request.get_json(silent=True) if request.method == "POST" else request.args
    if not data or "thread_id" not in data:
        return jsonify(error="Parameter 'thread_id' ist erforderlich."), 400

    thread_id = data.get("thread_id")
    t0 = time.time()

    print(f"Agent initialized in {time.time() - t0:.2f}s")

    t0 = time.time()
    messages = agent.get_messages_by_thread_id(thread_id) if thread_id else []
    print(f"Messages fetched in {time.time() - t0:.2f}s")

    return jsonify(messages=messages), 200

@app.route("/product_by_barcode", methods=["GET"])
@require_api_key
def get_product_by_barcode_route():

    barcode = request.args.get("barcode")
    if not barcode:
        return jsonify(error="Parameter 'barcode' ist erforderlich."), 400

    product = get_product_by_barcode(barcode)
    if not product:
        return jsonify(exists=False, product={}), 200

    return jsonify(exists=True, product=product), 200


if __name__ == "__main__":
    os.environ["INVERBIO_ENV"] = "dev"  # Set environment variable for development
    app.run()