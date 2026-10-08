# Imports and dependencies
import json
import os
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

# The fallback Hugging Face token to use if the HF_TOKEN environment variable is not set
HF_TOKEN_FALLBACK = "" # removed for git
HF_MODEL_REPO = "HireMeDeveloper/Chatbot-Lite"

# Clean model output into JSON before returning it to the frontend
def extractJsonPayload(rawText):
    text = (rawText or "").strip()
    if not text:
        raise ValueError("Empty model response")
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    if text.startswith("```json"):
        text = text[len("```json") :].strip()
    if text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    payload = json.loads(text)
    if isinstance(payload, dict) and "game_idea" in payload:
        return payload
    if isinstance(payload, dict) and "gameIdea" in payload:
        return {"message": payload.get("message", ""), "game_idea": payload["gameIdea"]}
    raise ValueError("Model response was not valid JSON")


# Load the local model files from the project folder
def ensureLocalModelFiles(localModelPath):
    modelFiles = [entry for entry in localModelPath.iterdir()] if localModelPath.exists() else []
    if localModelPath.exists() and modelFiles:
        return

    repoId = HF_MODEL_REPO
    token = os.getenv("HF_TOKEN") or HF_TOKEN_FALLBACK
    print(f"Local model folder missing or empty. Downloading from Hugging Face: {repoId}")

    localModelPath.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repoId,
        local_dir=str(localModelPath),
        local_dir_use_symlinks=False,
        token=token,
    )
    print("Model download complete.")


def loadModelAndTokenizer():
    localModelPath = Path(__file__).resolve().parent / "model"
    ensureLocalModelFiles(localModelPath)

    tokenizerInstance = AutoTokenizer.from_pretrained(str(localModelPath), local_files_only=True)
    modelInstance = AutoModelForCausalLM.from_pretrained(
        str(localModelPath),
        device_map="auto",
        local_files_only=True,
    )
    return tokenizerInstance, modelInstance

# Create the Flask app and load the model
app = Flask(__name__)
CORS(app)
try:
    tokenizer, model = loadModelAndTokenizer()
    print("Model loaded successfully.")
except Exception as exc:
    tokenizer = None
    model = None
    print(f"Model load failed: {exc}")
    import traceback
    traceback.print_exc()

# Load the rules file
rulesFile = Path(__file__).parent / "rules.md"
systemPrompt = rulesFile.read_text(encoding="utf-8").strip() if rulesFile.exists() else ""

frontendRoot = Path(__file__).resolve().parent.parent / "CSC525-Chatbot-Frontend"


@app.route("/", methods=["GET"])
def index():
    return Response((frontendRoot / "index.html").read_text(encoding="utf-8"), mimetype="text/html")


@app.route("/script.js", methods=["GET"])
def script():
    return Response((frontendRoot / "script.js").read_text(encoding="utf-8"), mimetype="application/javascript")

# Endpoint to handle chat requests
chatSessions = {}


def shutdownBackend():
    os._exit(0)


@app.route("/api/close", methods=["POST"])
def close():
    payload = request.get_json(silent=True) or {}
    _ = payload.get("session_id")
    threading.Timer(0.5, shutdownBackend).start()
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
def chat():
    if not model or not tokenizer:
        return jsonify({"error": "Model not loaded"}), 503

    payload = request.get_json(silent=True) or {}
    sessionId = str(payload.get("session_id") or "default-session").strip() or "default-session"
    userMessage = str(payload.get("inputs", "")).strip()
    if not userMessage:
        return jsonify({"error": "No message"}), 400

    history = chatSessions.setdefault(sessionId, [])
    history.append({"role": "user", "content": userMessage})

    messages = [{"role": "system", "content": systemPrompt}]
    messages.extend(history)
    chatText = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    tokenizerInputs = tokenizer(chatText, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **tokenizerInputs,
        max_new_tokens=128,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
    )

    generatedText = tokenizer.decode(
        outputs[0][tokenizerInputs["input_ids"].shape[1] :],
        skip_special_tokens=True,
    ).strip()

    responsePayload = extractJsonPayload(generatedText)
    history.append({"role": "assistant", "content": json.dumps(responsePayload)})
    return jsonify(responsePayload)


# Endpoint to reset the chat session for a given session ID
@app.route("/api/chat/reset", methods=["POST"])
def resetChat():
    payload = request.get_json(silent=True) or {}
    sessionId = str(payload.get("session_id") or "default-session").strip() or "default-session"
    chatSessions.pop(sessionId, None)
    return jsonify({"ok": True, "session_id": sessionId})


# App entry
if __name__ == "__main__":
    portNumber = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=portNumber, debug=False)
