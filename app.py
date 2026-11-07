from __future__ import annotations

from pathlib import Path

from flask import Flask, abort, render_template, request, send_file

from ai_video_generator.config import OUTPUT_DIR, PROJECTS_DIR
from ai_video_generator.generator import AVAILABLE_VOICE_OPTIONS, generate_video_project
from ai_video_generator.research import fetch_wikipedia_summary

app = Flask(__name__)

ROOT_DIR = Path(__file__).resolve().parent


@app.route("/download/<path:relative_path>")
def download_file(relative_path: str):
    requested = (OUTPUT_DIR / relative_path).resolve()
    project_requested = (PROJECTS_DIR / relative_path).resolve()
    allowed = [OUTPUT_DIR.resolve(), PROJECTS_DIR.resolve()]

    if not any(requested == base or requested.is_relative_to(base) for base in allowed):
        if not any(project_requested == base or project_requested.is_relative_to(base) for base in allowed):
            abort(404)
        file_to_send = project_requested
    else:
        file_to_send = requested

    if not file_to_send.exists() or not file_to_send.is_file():
        abort(404)

    return send_file(file_to_send, as_attachment=True)


@app.route("/", methods=["GET", "POST"])
def home():
    status = None
    project = None
    error = None
    voice = "default"
    image_count = 3
    script_text = ""

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        mode = request.form.get("mode", "short")
        duration = int(request.form.get("duration", 45) or 45)
        voice = request.form.get("voice", "default")
        image_count = max(1, min(12, int(request.form.get("image_count", 3) or 3)))
        script_text = request.form.get("script_text", "").strip()
        uploaded_script = request.files.get("script_file")
        if uploaded_script and uploaded_script.filename:
            try:
                script_text = uploaded_script.read().decode("utf-8", errors="replace").strip()
            except Exception:
                script_text = ""
        aspect = request.form.get("aspect", "9:16")
        style = request.form.get("style", "cinematic")

        if not topic and not script_text:
            error = "Please enter a topic, paste the exact script, or upload a script file to generate a video."
        else:
            try:
                research = fetch_wikipedia_summary(topic) if topic else {"title": topic or "Custom script", "summary": script_text, "source_url": ""}
                project = generate_video_project(
                    topic=topic or "Custom script",
                    mode=mode,
                    duration=duration,
                    voice=voice,
                    aspect=aspect,
                    style=style,
                    output_dir=OUTPUT_DIR,
                    project_dir=PROJECTS_DIR,
                    image_count=image_count,
                    research=research,
                    script_text=script_text,
                )
                status = "Video generated successfully."
            except Exception as exc:  # pragma: no cover - UI-level catch
                error = f"Video generation failed: {exc}"

    return render_template(
        "index.html",
        status=status,
        project=project,
        error=error,
        voice_options=AVAILABLE_VOICE_OPTIONS,
        selected_voice=voice if request.method == "POST" else "default",
        selected_image_count=image_count if request.method == "POST" else 3,
        script_text=script_text if request.method == "POST" else "",
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
