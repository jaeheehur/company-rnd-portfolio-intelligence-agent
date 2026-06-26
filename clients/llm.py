"""Gemini 2.5 Pro 래퍼. chat / structured JSON / 임베딩 세 인터페이스만 노출."""
from google import genai
from google.genai import types
import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)


def chat(prompt: str) -> str:
    """단순 텍스트 생성."""
    response = _client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
    )
    return response.text


def structured(prompt: str, schema: type) -> dict | list:
    """JSON 강제 모드. schema는 Pydantic 모델 또는 Python 타입 힌트."""
    response = _client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return response.parsed


def embed(text: str) -> list[float]:
    """텍스트 임베딩. ip_agent의 cosine re-rank에 사용."""
    result = _client.models.embed_content(
        model=config.GEMINI_EMBED_MODEL,
        contents=text,
    )
    return result.embeddings[0].values
