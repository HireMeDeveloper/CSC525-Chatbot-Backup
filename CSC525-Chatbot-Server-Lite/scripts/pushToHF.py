# Imports
from pathlib import Path
from huggingface_hub import HfApi

# Model repo name on Hugging Face
REPO_ID = "HireMeDeveloper/Chatbot-Lite"

# Upload the model artifacts to Hugging Face
script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
model_dir = (server_dir / "model").resolve()
if not model_dir.exists() or not model_dir.is_dir():
    raise SystemExit(f"Model directory not found: {model_dir}")
token = input("Enter your Hugging Face token: ").strip()
if not token:
    raise SystemExit("Token is required.")
api = HfApi(token=token)
api.create_repo(
    repo_id=REPO_ID,
    repo_type="model",
    exist_ok=True,
)
api.upload_folder(
    repo_id=REPO_ID,
    repo_type="model",
    folder_path=str(model_dir),
    commit_message="Upload model artifacts",
)
print(f"Done. Model uploaded to Hugging Face: {REPO_ID}")
