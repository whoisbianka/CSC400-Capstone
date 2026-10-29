

import runpy
from flask import Flask, jsonify, request, send_from_directory

# Load Gemini without importing the database
service = runpy.run_path("degree_path/gemini_service.py")
ask_gemini = service["ask_gemini"]

app = Flask(__name__)


@app.get("/")
def gemini_demo():
    return send_from_directory(".", "gemini_demo.html")


@app.post("/api/gemini")
def gemini_api():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Please send a JSON object."), 400

    question = data.get("question")
    history = data.get("history", [])

    # Validate the conversation history
    if not isinstance(history, list):
        return jsonify(error="Invalid conversation history."), 400

    # Keep only the most recent 12 messages
    history = history[-12:]

    # Validate the student's question
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 500:
        return jsonify(
            error="Enter a question between 1 and 500 characters."
        ), 400

    try:
        # Send the question and previous messages to Gemini
        answer = ask_gemini(question.strip(), history=history)

        return jsonify(response=answer)

    except Exception:
        app.logger.exception("Gemini request failed")

        return jsonify(
            error="The AI assistant is temporarily unavailable."
        ), 503


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8001, debug=False)
