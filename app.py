from __future__ import annotations

from pathlib import Path

from flask import Flask, render_template, request

from ai_video_generator.config import OUTPUT_DIR, PROJECTS_DIR
from ai_video_generator.generator import generate_video_project
from ai_video_generator.research import fetch_wikipedia_summary

app = Flask(__name__)

ROOT_DIR = Path(__file__).resolve().parent


@app.route("/", methods=["GET", "POST"])
def home():
    status = None
    project = None
    error = None

    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        mode = request.form.get("mode", "short")
        duration = int(request.form.get("duration", 45) or 45)
        voice = request.form.get("voice", "default")
        aspect = request.form.get("aspect", "9:16")
        style = request.form.get("style", "cinematic")

        if not topic:
            error = "Please enter a topic, fact, or idea to generate a video."
        else:
            try:
                research = fetch_wikipedia_summary(topic)
                project = generate_video_project(
                    topic=topic,
                    mode=mode,
                    duration=duration,
                    voice=voice,
                    aspect=aspect,
                    style=style,
                    output_dir=OUTPUT_DIR,
                    project_dir=PROJECTS_DIR,
                    research=research,
                )
                status = "Video generated successfully."
            except Exception as exc:  # pragma: no cover - UI-level catch
                error = f"Video generation failed: {exc}"

    return render_template(
        "index.html",
        status=status,
        project=project,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
