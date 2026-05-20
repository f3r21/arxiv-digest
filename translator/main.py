"""Servicio de traduccion EN->ES con MyMemory como backend."""

import hashlib
import logging
import os
import re

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

logger = logging.getLogger("translator")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s INIT: %(message)s",
)

MYMEMORY_URL = "https://api.mymemory.translated.net/get"
MYMEMORY_EMAIL = os.environ.get("MYMEMORY_EMAIL", "").strip()
MAX_CHUNK_CHARS = 450
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_cache: dict[str, str] = {}


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str = "en"
    target: str = "es"


class TranslateResponse(BaseModel):
    translated: str
    cached: bool


app = FastAPI(title="arxiv-digest translator")


def _cache_key(text: str, source: str, target: str) -> str:
    raw = f"{source}|{target}|{text}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _split_for_translation(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Parte texto por oraciones para respetar el limite de MyMemory."""
    if len(text) <= max_chars:
        return [text]
    sentences = SENTENCE_SPLIT.split(text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(sentence) <= max_chars:
            current = sentence
        else:
            for i in range(0, len(sentence), max_chars):
                chunks.append(sentence[i : i + max_chars])
            current = ""
    if current:
        chunks.append(current)
    return chunks


async def _call_mymemory(client: httpx.AsyncClient, chunk: str, source: str, target: str) -> str:
    params = {"q": chunk, "langpair": f"{source}|{target}"}
    if MYMEMORY_EMAIL:
        params["de"] = MYMEMORY_EMAIL
    try:
        resp = await client.get(MYMEMORY_URL, params=params, timeout=10.0)
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("PROFILE: MyMemory request fallo: %s", exc)
        return chunk
    if payload.get("responseStatus") != 200:
        logger.warning(
            "PROFILE: MyMemory respondio status=%s details=%s",
            payload.get("responseStatus"),
            payload.get("responseDetails"),
        )
        return chunk
    translated = payload.get("responseData", {}).get("translatedText", "").strip()
    return translated or chunk


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest) -> TranslateResponse:
    key = _cache_key(req.text, req.source, req.target)
    if key in _cache:
        return TranslateResponse(translated=_cache[key], cached=True)

    chunks = _split_for_translation(req.text)
    async with httpx.AsyncClient() as client:
        translated_chunks = [
            await _call_mymemory(client, chunk, req.source, req.target)
            for chunk in chunks
        ]
    result = " ".join(translated_chunks)
    _cache[key] = result
    logger.info(
        "RESULT: traduccion %s->%s chunks=%d in=%d out=%d",
        req.source,
        req.target,
        len(chunks),
        len(req.text),
        len(result),
    )
    return TranslateResponse(translated=result, cached=False)
