from __future__ import annotations

import os
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))
VECTORIZE_URL = os.getenv("STEP_VECTORIZE_URL", "http://step-vectorize:8002")
SEGMENT_URL = os.getenv("STEP_SEGMENT_URL", "http://step-segment:8004")
STEP_TIMEOUT_SECONDS = float(os.getenv("STEP_TIMEOUT_SECONDS", "180"))

app = FastAPI(title="table_gen mac pipeline-api", version="1.0.0")
DATA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=str(DATA_ROOT)), name="data")


class ProcessUrlRequest(BaseModel):
    image_url: str = Field(min_length=1)
    session_id: str | None = None
    candidate_id: str | None = None
    layer_count: int = Field(default=6, ge=2, le=6)
    callback_url: str | None = None


class ProcessLocalRequest(BaseModel):
    local_path: str = Field(min_length=1, description="Path relative to /app/data, e.g. incoming/frame.png")
    session_id: str | None = None
    candidate_id: str | None = None
    layer_count: int = Field(default=6, ge=2, le=6)
    callback_url: str | None = None


def _to_data_uri(path: str | None) -> str | None:
    if not path:
        return None
    norm = path.replace("\\", "/")
    marker = "/app/data/"
    idx = norm.find(marker)
    if idx >= 0:
        return f"/data/{norm[idx + len(marker):]}"
    return None


def _resolve_local_input_path(local_path: str) -> Path:
    rel = local_path.replace("\\", "/").lstrip("/")
    if not rel:
        raise HTTPException(status_code=400, detail="local_path is empty")
    candidate = (DATA_ROOT / rel).resolve()
    data_root_resolved = DATA_ROOT.resolve()
    if not str(candidate).startswith(str(data_root_resolved)):
        raise HTTPException(status_code=400, detail="local_path must stay inside /app/data")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail=f"local input file not found: {rel}")
    if not candidate.is_file():
        raise HTTPException(status_code=400, detail=f"local_path is not a file: {rel}")
    return candidate


async def _run_pipeline(
    source_uri: str,
    session_id: str,
    candidate_id: str,
    layer_count: int,
    callback_url: str | None,
) -> dict:
    async with httpx.AsyncClient(timeout=STEP_TIMEOUT_SECONDS) as client:
        r_vec = await client.post(
            f"{VECTORIZE_URL.rstrip('/')}/run",
            json={
                "session_id": session_id,
                "candidate_id": candidate_id,
                "candidate_uri": source_uri,
                "layer_count": layer_count,
            },
        )
        r_vec.raise_for_status()
        vec = r_vec.json()

        r_seg = await client.post(
            f"{SEGMENT_URL.rstrip('/')}/run",
            json={
                "session_id": session_id,
                "candidate_id": candidate_id,
                "prepared_image_path": vec.get("prepared_image_path"),
                "layer_count": layer_count,
            },
        )
        r_seg.raise_for_status()
        seg = r_seg.json()

    result = {
        "status": "completed",
        "session_id": session_id,
        "candidate_id": candidate_id,
        "source_uri": source_uri,
        "prepared_image_path": vec.get("prepared_image_path"),
        "segment_dir": seg.get("segment_dir"),
        "master_svg_path": seg.get("master_svg_path"),
        "master_svg_uri": _to_data_uri(seg.get("master_svg_path")),
        "layer_count": seg.get("layer_count", layer_count),
    }

    if callback_url:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                await client.post(callback_url, json=result)
            result["callback"] = {"ok": True, "url": callback_url}
        except Exception as exc:
            result["callback"] = {"ok": False, "url": callback_url, "error": str(exc)}

    return result


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/process")
async def process(
    file: UploadFile | None = File(default=None),
    image_url: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
    candidate_id: str | None = Form(default=None),
    layer_count: int = Form(default=6),
    callback_url: str | None = Form(default=None),
) -> dict:
    if not file and not image_url:
        raise HTTPException(status_code=400, detail="Provide either file or image_url")
    if file and image_url:
        raise HTTPException(status_code=400, detail="Provide only one source: file or image_url")
    if layer_count < 2 or layer_count > 6:
        raise HTTPException(status_code=400, detail="layer_count must be in range 2..6")

    sess = session_id or f"sess_{uuid.uuid4().hex[:12]}"
    cand = candidate_id or f"cand_{uuid.uuid4().hex[:8]}"

    source_uri: str
    if file:
        payload = await file.read()
        if not payload:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        incoming_dir = DATA_ROOT / "incoming" / sess
        incoming_dir.mkdir(parents=True, exist_ok=True)
        name = file.filename or f"{cand}.png"
        out = incoming_dir / name
        out.write_bytes(payload)
        source_uri = str(out)
    else:
        source_uri = str(image_url).strip()

    try:
        return await _run_pipeline(
            source_uri=source_uri,
            session_id=sess,
            candidate_id=cand,
            layer_count=layer_count,
            callback_url=callback_url,
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1200] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"step call failed: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"pipeline failed: {exc}") from exc


@app.post("/process/url")
async def process_url(payload: ProcessUrlRequest) -> dict:
    sess = payload.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    cand = payload.candidate_id or f"cand_{uuid.uuid4().hex[:8]}"
    try:
        return await _run_pipeline(
            source_uri=payload.image_url,
            session_id=sess,
            candidate_id=cand,
            layer_count=payload.layer_count,
            callback_url=payload.callback_url,
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1200] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"step call failed: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"pipeline failed: {exc}") from exc


@app.post("/process/local")
async def process_local(payload: ProcessLocalRequest) -> dict:
    local_file = _resolve_local_input_path(payload.local_path)
    sess = payload.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    cand = payload.candidate_id or f"cand_{uuid.uuid4().hex[:8]}"
    try:
        return await _run_pipeline(
            source_uri=str(local_file),
            session_id=sess,
            candidate_id=cand,
            layer_count=payload.layer_count,
            callback_url=payload.callback_url,
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1200] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"step call failed: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"pipeline failed: {exc}") from exc
