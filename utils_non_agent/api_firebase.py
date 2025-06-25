


from firebase_functions import https_fn
from firebase_admin import initialize_app
from flask import Request, jsonify

from assistant_cls import Agent
from user_db import UserFirebase
initialize_app()
# Firebase Admin SDK initialisieren (wenn nicht bereits geschehen)
from firebase_utils import initialize_firestore
initialize_firestore()

@https_fn.on_request()
def chat_api(req: Request):
    if req.method != 'POST':
        return jsonify({"error": "Only POST allowed."}), 405

    data = req.get_json(silent=True)
    if not data or "msg" not in data:
        return jsonify({"error": "Parameter 'msg' ist erforderlich."}), 400

    msg = data.get("msg")
    img = data.get("img")
    user_id = data.get("user_id")
    thread_id = data.get("thread_id")

    agent = Agent()
    result = agent.chat(msg, img, user_id, thread_id)

    return jsonify({"response": result}), 200


@https_fn.on_request()
def get_thread_ids_api(req: Request):
    
    if req.method != 'GET':
        return jsonify({"error": "Only GET allowed."}), 405
    user_db = UserFirebase()
    user_id = req.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Query-Parameter 'user_id' ist erforderlich."}), 400

    threads = user_db.get_thread_ids_by_user_id(user_id)
    return jsonify({"threads": threads}), 200


@https_fn.on_request()
def get_threads_api(req: Request):
    if req.method != 'GET':
        return jsonify({"error": "Only GET allowed."}), 405
    user_db = UserFirebase()
    user_id = req.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Query-Parameter 'user_id' ist erforderlich."}), 400

    threads = user_db.get_threads_by_user_id(user_id)
    return jsonify({"threads": threads}), 200
