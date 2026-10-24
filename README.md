# AI Video Generator

This project is a lightweight Python + HTML/CSS web app that turns a topic into a simple AI-style video workflow. It creates a script, prepares scene cards, and renders an MP4 using MoviePy and FFmpeg.

## Features

- Simple browser-based interface
- Topic input and mode selection
- Short video and documentary-style script generation
- Narration generation with `pyttsx3`
- Scene-by-scene visual text slides
- MP4 export using FFmpeg
- Project folder output and generated JSON script

## Requirements

- Python 3.11+
- FFmpeg installed and available in PATH
- Windows recommended for `pyttsx3`

## Setup

1. Open a terminal in the project folder.
2. Run:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Start the app:

```powershell
$env:PIXABAY_API_KEY = "your-new-pixabay-api-key"
python app.py
```

Pixabay image search uses `PIXABAY_API_KEY` when set and falls back to Wikimedia Commons otherwise. Set the variable in the same terminal before starting the app.

4. Open this URL in a browser:

```text
http://127.0.0.1:5000/
```

## File layout

- `app.py` – main Flask entry point
- `templates/index.html` – UI form and preview
- `static/style.css` – styling
- `ai_video_generator/generator.py` – core generation logic
- `output/` – exported MP4s
- `projects/` – generated project data
- `tests/` – validation tests

## Important notes

- `pyttsx3` works best on Windows and may require Microsoft voices.
- FFmpeg must be installed and accessible.
- This version is a working MVP for automation and can be extended with real research APIs, image search, and a richer video editor later.
