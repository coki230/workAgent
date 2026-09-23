import os
from pathlib import Path

from app.config import get_settings

settings = get_settings()

def ensure_user_dir(user_id: int) -> Path:
    path = Path(settings.UPLOAD_DIR) / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_upload_file(user_id: int, filename: str, content: bytes) -> str:
    user_dir = ensure_user_dir(user_id)
    file_path = user_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)
    return str(file_path)

def str_2_file(file_path: str, text: str)   :
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

def file_2_str(file_path: str) -> str :
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content