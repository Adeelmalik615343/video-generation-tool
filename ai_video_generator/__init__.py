"""AI media generator package."""

from .generator import generate_video_project
from .research import fetch_wikipedia_summary

__all__ = ["generate_video_project", "fetch_wikipedia_summary"]
