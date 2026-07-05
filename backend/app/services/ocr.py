import base64
import mimetypes
from pathlib import Path

import httpx

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def is_image_path(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def extract_image_text(path: Path, *, api_key: str | None = None) -> str:
    key = (api_key or OPENAI_API_KEY or "").strip()
    if not key:
        return (
            "[Image file — OCR requires an OpenAI API key. "
            "Set OPENAI_API_KEY or add a provider in Settings, then re-process this file.]"
        )
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    payload = {
        "model": OPENAI_MODEL if "gpt-4" in OPENAI_MODEL else "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract all readable text from this image. "
                            "Preserve structure with line breaks. Output text only."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
                ],
            }
        ],
        "max_tokens": 4096,
    }
    try:
        with httpx.Client(timeout=90) as client:
            res = client.post(
                f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json=payload,
            )
            res.raise_for_status()
            content = res.json()["choices"][0]["message"]["content"]
            return (content or "").strip() or "[No text detected in image]"
    except Exception as exc:
        return f"[OCR failed: {exc}]"
