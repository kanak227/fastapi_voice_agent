import os
import json

DHOME = "src"


def gemini_model_for_chat() -> str:
    """Model name for langchain_google_genai (strip optional ``models/`` prefix)."""
    raw = (os.getenv("GEMINI_MODEL") or "gemini-2.0-flash").strip()
    if raw.startswith("models/"):
        return raw[len("models/") :]
    return raw

LOGS = os.path.join(os.getcwd(), "runtime", "logs")

def write_to_json_file(output_json_file, json_data):
    dest_folder = os.path.dirname(output_json_file)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    with open(output_json_file, "w") as output_file:
        json.dump(json_data, output_file, indent=4)