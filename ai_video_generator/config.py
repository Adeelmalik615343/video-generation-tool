from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

OUTPUT_DIR = ROOT_DIR / "output"
PROJECTS_DIR = ROOT_DIR / "projects"
TEMP_DIR = ROOT_DIR / "temp"

ASPECT_MAP = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}

for folder in (OUTPUT_DIR, PROJECTS_DIR, TEMP_DIR):
    folder.mkdir(exist_ok=True)
