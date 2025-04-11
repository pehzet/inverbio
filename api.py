from flask import Flask, request, jsonify
from assistant import chat
from user_db import get_thread_ids_by_user_id, get_threads_by_user_id

app = Flask(__name__)

@app.route('/chat', methods=['POST'])
def chat_api():
    # Erwartet einen JSON-Request im Format:
    # {
    #   "msg": "Deine Nachricht",
    #   "img": "optional: Bilddaten oder URL",
    #   "user_id": "optional: Benutzer-ID",
    #   "thread_id": "optional: Thread-ID"
    # }
    data = request.get_json()

    if not data or "msg" not in data:
        return jsonify({"error": "Parameter 'msg' ist erforderlich."}), 400

    msg = data.get("msg")
    img = data.get("img")
    user_id = data.get("user_id")
    thread_id = data.get("thread_id")

    result = chat(msg, img, user_id, thread_id)
    return jsonify({"response": result}), 200

@app.route('/thread_ids', methods=['GET'])
def get_thread_ids_api():
    # Erwartet einen Query-Parameter "user_id", z.B.:
    # /threads?user_id=123
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Query-Parameter 'user_id' ist erforderlich."}), 400

    threads = get_thread_ids_by_user_id(user_id)
    return jsonify({"threads": threads}), 200


@app.route('/threads', methods=['GET'])
def get_threads_api():
    # Erwartet einen Query-Parameter "user_id", z.B.:
    # /threads?user_id=123
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Query-Parameter 'user_id' ist erforderlich."}), 400

    threads = get_threads_by_user_id(user_id)
    return jsonify({"threads": threads}), 200
if __name__ == '__main__':
    app.run(debug=True)
