# imports and dependencies
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


# Constants
ROOT_DIR = Path(__file__).resolve().parent
SERVER_DIR = ROOT_DIR / "CSC525-Chatbot-Server-Lite"
BACKEND_APP = SERVER_DIR / "app.py"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = int(os.getenv("PORT", "5000"))


# Function to wait for the server port to be available
def wait_for_port(host, port, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.2)
    return False


# Main function to start the backend server and open the frontend
def main():
    env = os.environ.copy()
    env.setdefault("PORT", str(DEFAULT_PORT))

    backend = subprocess.Popen(
        [sys.executable, str(BACKEND_APP)],
        cwd=str(SERVER_DIR),
        env=env,
    )

    try:
        if wait_for_port(DEFAULT_HOST, DEFAULT_PORT, timeout=45):
            webbrowser.open(f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/")

        return backend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        try:
            return backend.wait(timeout=10)
        except subprocess.TimeoutExpired:
            backend.kill()
            return backend.wait()


# Entry point
if __name__ == "__main__":
    raise SystemExit(main())