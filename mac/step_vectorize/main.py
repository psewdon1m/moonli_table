from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.vectorizer import prepare_vector_source

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))


class VectorizeRequest(BaseModel):
    session_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    candidate_uri: str = Field(min_length=1)
    layer_count: int = Field(ge=2, le=6, default=6)


class VectorizeResponse(BaseModel):
    vector_dir: str
    prepared_image_path: str


app = FastAPI(title="table_gen mac step-vectorize", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=VectorizeResponse)
def run_vectorize(payload: VectorizeRequest) -> VectorizeResponse:
    session_dir = DATA_ROOT / "sessions" / payload.session_id / "vectorize"
    session_dir.mkdir(parents=True, exist_ok=True)
    try:
        vector_meta = prepare_vector_source(
            session_dir=session_dir / f"base_{uuid.uuid4().hex[:8]}",
            candidate_id=payload.candidate_id,
            source_image_uri=payload.candidate_uri,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Vectorize failed: {exc}") from exc
    return VectorizeResponse(vector_dir=str(session_dir), prepared_image_path=vector_meta["prepared_image_path"])
