from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import requests


def fetch_pixabay_images(topic: str, limit: int = 4) -> list[str]:
    cleaned = (topic or "").strip()
    api_key = os.getenv("PIXABAY_API_KEY", "").strip()
    if not cleaned or not api_key or limit <= 0:
        return []

    search_term = cleaned.split(":", 1)[0].strip()
    try:
        response = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": api_key,
                "q": search_term,
                "image_type": "photo",
                "safesearch": "true",
                "per_page": min(max(limit, 3), 200),
            },
            timeout=20,
        )
        response.raise_for_status()
        hits = response.json().get("hits", [])
        urls = [hit["webformatURL"] for hit in hits if hit.get("webformatURL")]
        return urls[:limit]
    except Exception:
        return []


def fetch_wikimedia_images(topic: str, limit: int = 4) -> list[str]:
    cleaned = (topic or "").strip()
    if not cleaned:
        return []

    query = quote(cleaned)
    url = (
        "https://commons.wikimedia.org/w/api.php?"
        "action=query&generator=search&gsrsearch="
        f"{query}&gsrnamespace=6&gsrlimit={limit}&prop=imageinfo&"
        "iiprop=url&format=json"
    )

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        payload = response.json()
        pages = payload.get("query", {}).get("pages", {})
        urls = []
        for page in pages.values():
            imageinfo = page.get("imageinfo") or []
            if not imageinfo:
                continue
            url_value = imageinfo[0].get("url")
            if url_value:
                urls.append(url_value)
        return urls
    except Exception:
        return []


def download_images_for_topic(topic: str, project_dir: Path, limit: int = 3) -> list[Path]:
    project_dir.mkdir(parents=True, exist_ok=True)
    urls = fetch_pixabay_images(topic, limit=limit)
    if not urls:
        urls = fetch_wikimedia_images(topic, limit=limit)
    downloaded: list[Path] = []

    for index, image_url in enumerate(urls[:limit]):
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            file_name = f"image_{index + 1}.jpg"
            path = project_dir / file_name
            path.write_bytes(response.content)
            downloaded.append(path)
        except Exception:
            continue

    return downloaded
