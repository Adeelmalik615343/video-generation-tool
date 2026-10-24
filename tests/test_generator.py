from ai_video_generator.generator import _build_caption_overlay, _fade_caption_clip, _scale_scene_durations, create_background_image, generate_script, generate_video_project, slugify, write_srt_captions
from ai_video_generator.image_search import fetch_pixabay_images
from pathlib import Path
from PIL import Image
import wave
import pytest

from ai_video_generator.generator import _wav_has_audio_frames


def test_generate_script_returns_scenes():
    scenes = generate_script("Climate change and renewable energy", "short")
    assert isinstance(scenes, list)
    assert len(scenes) >= 3
    assert all("title" in scene and "text" in scene for scene in scenes)


def test_generate_script_long_mode_has_intro_and_outro():
    scenes = generate_script("History of the Suez Canal", "long")
    assert scenes[0]["title"].lower().startswith("intro") or "opening" in scenes[0]["title"].lower()
    assert scenes[-1]["title"].lower().startswith("outro") or "conclusion" in scenes[-1]["title"].lower()


def test_slugify_truncates_long_topics_for_windows_paths():
    long_topic = "The hidden world of Antarctica: facts about the coldest driest and windiest continent on earth with subglacial lakes research stations and climate science"
    short_slug = slugify(long_topic, max_length=50)
    assert len(short_slug) <= 50
    assert short_slug.endswith("-") is False


def test_fetch_pixabay_images_uses_configured_api_key(monkeypatch):
    monkeypatch.setenv("PIXABAY_API_KEY", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "hits": [
                    {"webformatURL": "https://example.com/image.jpg"},
                    {"webformatURL": "https://example.com/second.jpg"},
                    {"webformatURL": "https://example.com/third.jpg"},
                ]
            }

    def fake_get(url, *, params, timeout):
        assert url == "https://pixabay.com/api/"
        assert params["key"] == "test-key"
        assert params["q"] == "ocean science"
        assert params["safesearch"] == "true"
        assert params["per_page"] == 3
        assert timeout == 20
        return FakeResponse()

    monkeypatch.setattr("ai_video_generator.image_search.requests.get", fake_get)

    assert fetch_pixabay_images("ocean science: surprising facts", limit=1) == ["https://example.com/image.jpg"]


def test_wav_audio_validation_rejects_empty_audio(tmp_path):
    path = tmp_path / "empty.wav"
    with wave.open(str(path), "wb") as audio_file:
        audio_file.setparams((1, 2, 22050, 0, "NONE", "not compressed"))

    assert _wav_has_audio_frames(path) is False


def test_background_image_does_not_add_color_overlay(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (20, 20), (120, 80, 40)).save(source)

    result = create_background_image(20, 20, str(source))

    assert result.getpixel((0, 0)) == (120, 80, 40)


def test_srt_keeps_full_caption_text(tmp_path):
    text = "A complete caption that is intentionally longer than one hundred and eighty characters. " * 3
    output = tmp_path / "captions.srt"

    write_srt_captions([{"text": text, "duration": 5}], output)

    assert text in output.read_text(encoding="utf-8")


def test_caption_layer_fades_without_fading_its_background(tmp_path):
    caption_path = tmp_path / "caption.png"
    Image.new("RGBA", (10, 10), (255, 255, 255, 255)).save(caption_path)
    from moviepy.editor import ImageClip

    caption = _fade_caption_clip(ImageClip(str(caption_path), transparent=True), 2)

    assert caption.mask.get_frame(0).max() == pytest.approx(0)
    assert caption.mask.get_frame(1).max() == pytest.approx(1)
    assert caption.mask.get_frame(1.9).max() < 1


def test_caption_overlay_uses_pro_style_panel_and_shadow():
    overlay = _build_caption_overlay("A polished caption for the video", "Hook", width=1080, height=1920)

    assert overlay.size == (1080, 1920)
    assert overlay.getbbox() is not None
    assert overlay.getpixel((540, 100))[3] > 0
    assert overlay.getpixel((540, 1500))[3] > 0


def test_scene_durations_expand_to_cover_voiceover():
    scenes = [{"duration": value} for value in (4, 7, 7, 5)]

    _scale_scene_durations(scenes, 35)

    assert sum(scene["duration"] for scene in scenes) == pytest.approx(35)


def test_generate_video_project_tracks_voice_and_caption_status():
    result = generate_video_project(
        topic="Ocean science",
        mode="short",
        duration=30,
        voice="default",
        aspect="9:16",
        style="cinematic",
        output_dir=Path("output"),
        project_dir=Path("projects"),
    )
    assert "voice_status" in result
    assert "caption_status" in result
    assert "voice" in result["voice_status"].lower()
    assert "caption" in result["caption_status"].lower()
