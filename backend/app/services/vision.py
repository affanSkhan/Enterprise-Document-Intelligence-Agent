import base64
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings


SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp"}


def describe_image(path: str, instruction: str = "Describe the chart, table, or figure and preserve visible numbers and labels.") -> dict[str, Any]:
    """Optional Gemini vision adapter. OCR/vision quality must be benchmarked on a real dataset."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required for visual understanding")
    image_path = Path(path)
    if image_path.suffix.lower() not in SUPPORTED_IMAGES:
        raise ValueError("Unsupported image format")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    llm = ChatGoogleGenerativeAI(model=settings.PRIMARY_LLM_MODEL, google_api_key=settings.GEMINI_API_KEY)
    message = HumanMessage(content=[
        {"type": "text", "text": instruction},
        {"type": "image_url", "image_url": f"data:image/{image_path.suffix[1:]};base64,{encoded}"},
    ])
    response = llm.invoke([message])
    return {"description": response.content, "model": settings.PRIMARY_LLM_MODEL, "benchmark_status": "not_yet_benchmarked"}
