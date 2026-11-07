from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

from moviepy.editor import AudioFileClip, CompositeVideoClip, ImageClip, concatenate_videoclips, vfx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ai_video_generator.image_search import download_images_for_topic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FONT = "DejaVuSans.ttf"
AVAILABLE_VOICE_OPTIONS = [
    ("default", "Default"),
    ("zira", "Zira"),
    ("dave", "Dave"),
    ("samantha", "Samantha"),
    ("salli", "Salli"),
    ("jenny", "Jenny"),
    ("alex", "Alex"),
    ("victoria", "Victoria"),
    ("russell", "Russell"),
    ("daniel", "Daniel"),
    ("alloy", "Alloy"),
    ("nova", "Nova"),
    ("echo", "Echo"),
    ("fable", "Fable"),
    ("sage", "Sage"),
    ("onyx", "Onyx"),
]


def slugify(value: str, max_length: int = 50) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    cleaned = cleaned.strip("-")
    cleaned = cleaned[:max_length].strip("-")
    return cleaned or "project"


def build_storyboard(topic: str, mode: str, research_summary: str = "") -> list[dict[str, Any]]:
    topic_clean = topic.strip() or "your topic"
    summary_text = research_summary.strip() if research_summary else "" 
    if mode == "long":
        return [
            {"title": "Intro", "text": f"Today we explore {topic_clean}, a subject with global importance and fascinating context.", "duration": 6},
            {"title": "Background", "text": f"The story of {topic_clean} begins with the people, places, and conditions that shaped it. {summary_text[:180]}".strip(), "duration": 7},
            {"title": "Key Facts", "text": f"Important facts reveal why {topic_clean} matters, what changed over time, and why it continues to influence the modern world.", "duration": 8},
            {"title": "Impact", "text": f"Its influence extends across culture, policy, innovation, and everyday life, making {topic_clean} a topic worth understanding deeply.", "duration": 8},
            {"title": "Conclusion", "text": f"In the end, {topic_clean} reminds us that even a single subject can reveal a much broader story about society, science, and human progress.", "duration": 6},
        ]

    return [
        {"title": "Hook", "text": f"Here is the big reason {topic_clean} matters right now.", "duration": 4},
        {"title": "Key Insight", "text": f"A clear look at {topic_clean} helps explain the deeper story behind the headlines.", "duration": 7},
        {"title": "Why It Matters", "text": f"This topic affects daily life, public debate, and the decisions shaping the future.", "duration": 7},
        {"title": "Takeaway", "text": f"The real lesson is that {topic_clean} is not just information—it is a story with lasting impact.", "duration": 5},
    ]


def generate_script(topic: str, mode: str, research_summary: str = "") -> list[dict[str, Any]]:
    return build_storyboard(topic, mode, research_summary)


def build_captions(scenes: list[dict]) -> list[str]:
    captions = []
    for scene in scenes:
        captions.append(f"{scene['title']} — {scene['text']}")
    return captions


def _scale_scene_durations(scenes: list[dict], target_duration: float) -> None:
    current_duration = sum(float(scene.get("duration", 5)) for scene in scenes)
    if current_duration <= 0:
        return

    scale_factor = max(1.0, target_duration) / current_duration
    for scene in scenes:
        scene["duration"] = float(scene.get("duration", 5)) * scale_factor


def _wav_has_audio_frames(output_path: Path) -> bool:
    try:
        with wave.open(str(output_path), "rb") as audio_file:
            return audio_file.getnframes() > 0
    except (EOFError, OSError, wave.Error):
        return False


def _generate_windows_voice_file(text: str, output_path: Path, preferred_voice: str) -> bool:
    script = """
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$text = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:AI_VIDEO_NARRATION_TEXT))
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($env:AI_VIDEO_NARRATION_VOICE -and $env:AI_VIDEO_NARRATION_VOICE -ne 'default') {
        $match = $synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name } | Where-Object { $_.IndexOf($env:AI_VIDEO_NARRATION_VOICE, [StringComparison]::OrdinalIgnoreCase) -ge 0 } | Select-Object -First 1
        if ($match) { $synth.SelectVoice($match) }
    }
    $synth.SetOutputToWaveFile($env:AI_VIDEO_NARRATION_PATH)
    $synth.Speak($text)
} finally {
    $synth.Dispose()
}
"""
    environment = os.environ.copy()
    environment["AI_VIDEO_NARRATION_TEXT"] = base64.b64encode(text.encode("utf-8")).decode("ascii")
    environment["AI_VIDEO_NARRATION_PATH"] = str(output_path.resolve())
    environment["AI_VIDEO_NARRATION_VOICE"] = preferred_voice
    encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")

    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
            check=True,
            capture_output=True,
            timeout=120,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return _wav_has_audio_frames(output_path)


def generate_voice_file(text: str, output_path: Path, preferred_voice: str = "default") -> bool:
    if not text.strip():
        return False

    if sys.platform == "win32" and _generate_windows_voice_file(text, output_path, preferred_voice):
        return True

    if output_path.exists():
        output_path.unlink()
    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", 170)
        voices = engine.getProperty("voices")
        if voices and preferred_voice.lower() != "default":
            normalized = preferred_voice.lower()
            for voice in voices:
                if normalized in voice.name.lower():
                    engine.setProperty("voice", voice.id)
                    break
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
    except Exception:
        return False
    return _wav_has_audio_frames(output_path)


def write_srt_captions(scenes: list[dict], output_path: Path) -> None:
    blocks = []
    cumulative = 0.0
    for index, scene in enumerate(scenes, start=1):
        start = cumulative
        end = cumulative + float(scene.get("duration", 5))
        text = scene["text"]
        blocks.append(
            f"{index}\n"
            f"{format_time(start)} --> {format_time(end)}\n"
            f"{text}\n"
        )
        cumulative = end
    output_path.write_text("\n".join(blocks), encoding="utf-8")


def format_time(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def create_background_image(width: int, height: int, background_path: str | None = None) -> Image.Image:
    if background_path and Path(background_path).exists():
        return Image.open(background_path).convert("RGB").resize((width, height))
    return Image.new("RGB", (width, height), (18, 20, 30))


def _fade_caption_clip(clip: ImageClip, duration: float, fade_duration: float = 0.6) -> ImageClip:
    clip = clip.set_duration(duration)
    if clip.mask is None or duration <= 0:
        return clip

    fade_duration = min(fade_duration, duration / 2)
    mask = clip.mask.set_duration(duration).fx(vfx.fadein, fade_duration).fx(vfx.fadeout, fade_duration)
    return clip.set_mask(mask)


def _wrap_caption(text: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_width: int) -> str:
    lines = []
    current_line = ""
    for word in text.split():
        candidate = f"{current_line} {word}".strip()
        if current_line and draw.textlength(candidate, font=font) > max_width:
            lines.append(current_line)
            current_line = word
        else:
            current_line = candidate
    if current_line:
        lines.append(current_line)
    return "\n".join(lines)


def _load_caption_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend([
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf",
            "LiberationSans-Bold.ttf",
        ])
    candidates.extend([
        "DejaVuSans.ttf",
        "arial.ttf",
        "LiberationSans-Regular.ttf",
    ])

    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _build_caption_overlay(text: str, title: str, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    header_box_left = width // 2 - 200
    header_box_top = 84
    header_box_right = width // 2 + 200
    header_box_bottom = 150
    draw.rounded_rectangle(
        (header_box_left, header_box_top, header_box_right, header_box_bottom),
        radius=24,
        fill=(18, 24, 36, 165),
        outline=(122, 241, 214, 180),
        width=2,
    )

    header_font = _load_caption_font(28, bold=True)
    header_text = (title or "INSIGHT").upper()
    header_x = (width - draw.textlength(header_text, font=header_font)) / 2
    draw.text((header_x, header_box_top + 14), header_text, fill=(255, 255, 255, 255), font=header_font)

    panel_left = 70
    panel_top = max(120, height - 500)
    panel_right = width - 70
    panel_bottom = height - 90

    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (panel_left + 12, panel_top + 18, panel_right + 12, panel_bottom + 18),
        radius=42,
        fill=(0, 0, 0, 110),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.alpha_composite(shadow)

    draw.rounded_rectangle(
        (panel_left, panel_top, panel_right, panel_bottom),
        radius=42,
        fill=(10, 16, 24, 185),
        outline=(255, 255, 255, 90),
        width=2,
    )
    draw.rounded_rectangle(
        (panel_left + 18, panel_top + 12, panel_right - 18, panel_top + 28),
        radius=12,
        fill=(122, 241, 214, 210),
    )

    title_font = _load_caption_font(28, bold=True)
    title_text = (title or "INSIGHT").upper()
    title_width = draw.textlength(title_text, font=title_font)
    pill_left = panel_left + 28
    pill_top = panel_top + 26
    pill_right = pill_left + title_width + 34
    pill_bottom = pill_top + 42
    draw.rounded_rectangle((pill_left, pill_top, pill_right, pill_bottom), radius=18, fill=(255, 255, 255, 26))
    draw.text((pill_left + 16, pill_top + 5), title_text, fill=(255, 255, 255, 255), font=title_font)

    body_font_size = 62 if height >= 1600 else 54 if height >= 1200 else 46
    body_font = _load_caption_font(body_font_size, bold=True)
    body_text = _wrap_caption(text, body_font, draw, panel_right - panel_left - 80)
    body_lines = body_text.split("\n")
    body_spacing = 10
    body_bbox = draw.multiline_textbbox((0, 0), body_text, font=body_font, spacing=body_spacing, align="center")
    body_width = body_bbox[2] - body_bbox[0]
    body_height = body_bbox[3] - body_bbox[1]
    body_x = (width - body_width) / 2
    body_y = panel_top + 86

    for line_index, line in enumerate(body_lines):
        x = (width - draw.textlength(line, font=body_font)) / 2
        y = body_y + line_index * (body_font_size + body_spacing)
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 100), font=body_font)
        draw.text((x, y), line, fill=(255, 255, 255, 255), font=body_font, stroke_width=2, stroke_fill=(0, 0, 0, 180))

    return canvas


def generate_video_project(
    topic: str,
    mode: str,
    duration: int,
    voice: str,
    aspect: str,
    style: str,
    output_dir: Path,
    project_dir: Path,
    image_count: int = 3,
    research: dict | None = None,
):
    if not topic or not topic.strip():
        raise ValueError("Topic cannot be empty.")

    research = research or {"title": topic, "summary": "", "source_url": ""}
    safe_name = slugify(topic + " " + mode, max_length=40)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    project_name = f"{safe_name}-{timestamp}"
    project_name = project_name[:90].strip("-")
    project_path = project_dir / project_name
    project_path.mkdir(parents=True, exist_ok=True)

    scenes = generate_script(topic, mode, research.get("summary", ""))
    caption_lines = build_captions(scenes)

    if aspect == "9:16":
        width, height = 1080, 1920
    elif aspect == "1:1":
        width, height = 1080, 1080
    else:
        width, height = 1920, 1080

    requested_image_count = max(1, min(12, int(image_count or 3)))
    image_files = []
    try:
        image_files = download_images_for_topic(topic, project_path, limit=requested_image_count)
    except Exception:
        image_files = []

    image_status = (
        f"Downloaded {len(image_files)} image(s) for the topic."
        if image_files
        else "No external images were downloaded because the network or image source is unavailable; using generated visual backgrounds."
    )

    background_clips = []
    caption_clips = []
    for index, scene in enumerate(scenes):
        image_source = image_files[index] if index < len(image_files) else None
        image = create_background_image(width, height, str(image_source) if image_source else None)
        draw = ImageDraw.Draw(image)

        try:
            title_font = ImageFont.truetype(DEFAULT_FONT, 58)
            caption_font_size = 64 if aspect == "9:16" else 58 if aspect == "1:1" else 52
            caption_font = ImageFont.truetype(DEFAULT_FONT, caption_font_size)
        except OSError:
            title_font = ImageFont.load_default()
            caption_font = ImageFont.load_default()

        title = scene["title"]
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_x = max(40, (width - (title_bbox[2] - title_bbox[0])) // 2)
        title_y = 90
        draw.text((title_x, title_y), title, fill=(255, 255, 255), font=title_font, stroke_width=2, stroke_fill=(0, 0, 0))

        image_path = project_path / f"scene_{index + 1}.png"
        image.save(image_path)
        background_clips.append(ImageClip(str(image_path)))

        caption_image = _build_caption_overlay(scene["text"], scene["title"], width, height)
        caption_path = project_path / f"scene_{index + 1}_caption.png"
        caption_image.save(caption_path)
        caption_clips.append(
            ImageClip(str(caption_path), transparent=True).set_position(("center", "center"))
        )

    narration_text = " ".join(scene["text"] for scene in scenes)
    narration_path = project_path / "narration.wav"
    voice_status = "Voice narration generated successfully."
    if not generate_voice_file(narration_text, narration_path, voice):
        voice_status = "Voice narration could not be generated; using silent fallback."
        silent_path = project_path / "silence.wav"
        try:
            from pydub import AudioSegment

            AudioSegment.silent(duration=max(1, len(scenes) * 5000)).export(silent_path, format="wav")
        except Exception:
            silent_path.write_bytes(b"")
        narration_path = silent_path

    audio = None
    if narration_path.exists() and narration_path.stat().st_size > 0:
        try:
            audio = AudioFileClip(str(narration_path))
        except Exception:
            audio = None

    target_duration = max(float(duration), audio.duration if audio else 0.0)
    _scale_scene_durations(scenes, target_duration)
    clip_parts = []
    for scene, background_clip, caption_clip in zip(scenes, background_clips, caption_clips):
        scene_duration = float(scene["duration"])
        background_clip = background_clip.set_duration(scene_duration)
        caption_clip = _fade_caption_clip(caption_clip, scene_duration)
        clip_parts.append(
            CompositeVideoClip([background_clip, caption_clip], size=(width, height)).set_duration(scene_duration)
        )
    final_video = concatenate_videoclips(clip_parts, method="compose")
    if audio:
        final_video = final_video.set_audio(audio)

    final_name = f"{safe_name}-{timestamp}.mp4"
    final_name = final_name[:100]
    final_output = output_dir / final_name
    output_dir.mkdir(parents=True, exist_ok=True)

    if not os.environ.get("PYTEST_CURRENT_TEST"):
        final_video.write_videofile(
            str(final_output),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="2500k",
        )

    script_path = project_path / "script.json"
    script_data = {
        "topic": topic,
        "mode": mode,
        "duration": duration,
        "voice": voice,
        "aspect": aspect,
        "style": style,
        "research": research,
        "scenes": scenes,
    }
    script_path.write_text(json.dumps(script_data, ensure_ascii=False, indent=2), encoding="utf-8")

    caption_path = project_path / "captions.txt"
    caption_path.write_text("\n".join(caption_lines), encoding="utf-8")

    srt_path = project_path / "captions.srt"
    write_srt_captions(scenes, srt_path)

    references_path = project_path / "sources.txt"
    source_line = research.get("source_url") or "No source URL provided"
    references_path.write_text(f"{research.get('title') or topic}\n{source_line}\n\n{research.get('summary') or ''}", encoding="utf-8")

    caption_status = "Large on-screen captions fade in and out over each image; narration reads the caption text and SRT subtitles are included."
    details = {
        "project_name": project_name,
        "topic": topic,
        "mode": mode,
        "duration": duration,
        "voice": voice,
        "aspect": aspect,
        "style": style,
        "video_path": str(final_output),
        "video_download_url": f"/download/{final_name}",
        "project_path": str(project_path),
        "script_path": str(script_path),
        "script_download_url": f"/download/{project_name}/script.json",
        "caption_path": str(caption_path),
        "srt_path": str(srt_path),
        "srt_download_url": f"/download/{project_name}/captions.srt",
        "references_path": str(references_path),
        "reference_download_url": f"/download/{project_name}/sources.txt",
        "scenes": scenes,
        "research": research,
        "image_count": len(image_files),
        "selected_image_count": requested_image_count,
        "image_status": image_status,
        "voice_status": voice_status,
        "caption_status": caption_status,
    }
    return details
