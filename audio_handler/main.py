from __future__ import annotations

import os
import time
import mimetypes
from pathlib import Path
from typing import Any

import httpx
import jwt
from fastapi import FastAPI, File, Form, HTTPException, UploadFile


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


N8N_WEBHOOK_API = _required_env("N8N_WEBHOOK_API")
N8N_TIMEOUT_SECONDS = float(os.getenv("N8N_TIMEOUT_SECONDS", "30"))
MAX_PAYLOAD_BYTES = int(os.getenv("MAX_PAYLOAD_BYTES", str(16 * 1024 * 1024)))
N8N_WEBHOOK_BEARER = os.getenv("N8N_WEBHOOK_BEARER", "").strip()
N8N_BINARY_FIELD_NAME = os.getenv("N8N_BINARY_FIELD_NAME", "audio").strip() or "audio"

N8N_JWT_ENABLE = os.getenv("N8N_JWT_ENABLE", "true").strip().lower() in {"1", "true", "yes", "on"}
N8N_JWT_ALGORITHM = os.getenv("N8N_JWT_ALGORITHM", "RS256").strip() or "RS256"
N8N_JWT_PRIVATE_KEY_PATH = os.getenv("N8N_JWT_PRIVATE_KEY_PATH", "/app/RS256_PEM_PRIVATE_KEY").strip()
N8N_JWT_KID = os.getenv("N8N_JWT_KID", "").strip()
N8N_JWT_ISS = os.getenv("N8N_JWT_ISS", "audio_handler").strip()
N8N_JWT_SUB = os.getenv("N8N_JWT_SUB", "audio_handler").strip()
N8N_JWT_AUD = os.getenv("N8N_JWT_AUD", "").strip()
N8N_JWT_EXP_SECONDS = int(os.getenv("N8N_JWT_EXP_SECONDS", "300"))

app = FastAPI(title="audio_handler", version="0.1.0")


def _normalize_audio_content_type(filename: str, content_type: str | None) -> str:
    raw = (content_type or "").strip().lower()
    alias_map = {
        "application/ogg": "audio/ogg",
        "audio/x-wav": "audio/wav",
        "audio/x-aac": "audio/aac",
        "audio/x-flac": "audio/flac",
        "audio/mp3": "audio/mpeg",
    }
    if raw in alias_map:
        return alias_map[raw]
    if raw and raw != "application/octet-stream":
        return raw

    guessed, _ = mimetypes.guess_type(filename)
    if guessed and guessed.startswith("audio/"):
        return guessed

    ext = Path(filename).suffix.lower()
    fallback_by_ext = {
        ".ogg": "audio/ogg",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
    }
    return fallback_by_ext.get(ext, "application/octet-stream")


def _load_private_key() -> str:
    path = Path(N8N_JWT_PRIVATE_KEY_PATH)
    if not path.exists():
        raise RuntimeError(f"JWT private key file not found: {path}")
    return path.read_text(encoding="utf-8")


def _build_bearer_token() -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "iat": now,
        "exp": now + max(30, N8N_JWT_EXP_SECONDS),
        "iss": N8N_JWT_ISS,
        "sub": N8N_JWT_SUB,
    }
    if N8N_JWT_AUD:
        payload["aud"] = N8N_JWT_AUD
    headers: dict[str, Any] = {}
    if N8N_JWT_KID:
        headers["kid"] = N8N_JWT_KID
    private_key = _load_private_key()
    return jwt.encode(payload, private_key, algorithm=N8N_JWT_ALGORITHM, headers=headers)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/audio/forward")
async def forward_audio(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    user_id: str | None = Form(default=None),
) -> dict[str, Any]:
    filename = file.filename or "audio.bin"
    content_type = _normalize_audio_content_type(filename, file.content_type)
    payload = await file.read()
    size = len(payload)

    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if size > MAX_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size} bytes). Max allowed is {MAX_PAYLOAD_BYTES} bytes.",
        )
    if not (
        content_type.startswith("audio/")
        or filename.lower().endswith((".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac"))
    ):
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload an audio file.")

    headers: dict[str, str] = {}
    if N8N_WEBHOOK_BEARER:
        headers["Authorization"] = f"Bearer {N8N_WEBHOOK_BEARER}"
    elif N8N_JWT_ENABLE:
        try:
            headers["Authorization"] = f"Bearer {_build_bearer_token()}"
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to build JWT token: {exc}") from exc

    data = {
        "filename": filename,
        "content_type": content_type,
        "size_bytes": str(size),
    }
    if session_id:
        data["session_id"] = session_id
    if user_id:
        data["user_id"] = user_id

    try:
        async with httpx.AsyncClient(timeout=N8N_TIMEOUT_SECONDS) as client:
            response = await client.post(
                N8N_WEBHOOK_API,
                headers=headers,
                data=data,
                files={N8N_BINARY_FIELD_NAME: (filename, payload, content_type)},
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail=f"n8n webhook timeout: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to call n8n webhook: {exc}") from exc

    response_text = response.text
    if len(response_text) > 4000:
        response_text = response_text[:4000]

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"n8n webhook returned {response.status_code}: {response_text}",
        )

    parsed: Any
    try:
        parsed = response.json()
    except Exception:
        parsed = {"raw": response_text}

    return {
        "ok": True,
        "webhook_status": response.status_code,
        "webhook_response": parsed,
        "sent": {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size,
            "session_id": session_id,
            "user_id": user_id,
        },
    }
