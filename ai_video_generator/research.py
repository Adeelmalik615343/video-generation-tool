from __future__ import annotations

from typing import Any

import requests


WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"


def fetch_wikipedia_summary(topic: str) -> dict[str, Any]:
    cleaned = (topic or "").strip()
    if not cleaned:
        return {"title": "", "summary": "", "source_url": ""}

    query = cleaned.replace(" ", "_")
    url = f"{WIKIPEDIA_API}{query}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
        title = payload.get("title") or cleaned
        summary = payload.get("extract") or "No summary was available for this topic."
        source_url = payload.get("content_urls", {}).get("desktop", {}).get("page") or ""
        return {
            "title": title,
            "summary": summary,
            "source_url": source_url,
            "source": "Wikipedia API",
        }
    except Exception:
        return {
            "title": cleaned,
            "summary": f"This project explores {cleaned} using a generated documentary structure and media workflow.",
            "source_url": "",
            "source": "Fallback summary",
        }
