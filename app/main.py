from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import (
    DATA_DIR,
    PACKS_DIR,
    SESSION_GENERATE_BACKEND,
    STEP_GENERATE_URL,
    STEP_HTTP_TIMEOUT_SECONDS,
    STEP_SEGMENT_URL,
    STEP_VECTORIZE_URL,
    ensure_directories,
)
from app.models import (
    CandidateImage,
    CandidateShortlist,
    GenerationRequest,
    JobRecord,
    LibraryItem,
    PackBuildResponse,
    PublishPackRequest,
    PublishPackResponse,
    SessionRecord,
    SelectCompositionRequest,
    SelectPaletteRequest,
    ValidationReport,
)
from app.presets import PALETTE_PRESETS
from app.services.pipeline import build_pack, generate_candidates as run_generation, list_library_items, publish_pack
from app.services.store import find_job_by_pack_id, load_job, load_session, save_job, save_session
from app.services.validation import validate_manifest


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_directories()
    yield


app = FastAPI(
    title="table_gen API",
    version="0.1.0",
    description="Phase 1 API-first prototype",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")


@app.get("/")
def frontend() -> FileResponse:
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/proxy/image")
def proxy_image(url: str) -> Response:
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must be http/https")
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url)
            r.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"image proxy failed: {exc}") from exc
    media_type = r.headers.get("content-type", "application/octet-stream")
    return Response(content=r.content, media_type=media_type)


def _to_data_uri(path: str | None) -> str | None:
    if not path:
        return None
    norm = path.replace("\\", "/")
    marker = "/app/data/"
    idx = norm.find(marker)
    if idx >= 0:
        return f"/data/{norm[idx + len(marker):]}"
    return None


@app.get("/library/items", response_model=list[LibraryItem])
def library_items() -> list[LibraryItem]:
    return list_library_items()


@app.get("/palettes/presets")
def palette_presets() -> dict[str, list[str]]:
    return PALETTE_PRESETS


@app.get("/palettes/session")
def session_palettes() -> dict[str, list[str]]:
    return SESSION_PALETTES


@app.post("/sessions", response_model=SessionRecord)
def create_session() -> SessionRecord:
    session = SessionRecord.new(session_id=f"sess_{uuid.uuid4().hex[:12]}")
    save_session(session)
    return session


@app.get("/sessions/{session_id}", response_model=SessionRecord)
def get_session(session_id: str) -> SessionRecord:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/sessions/{session_id}/mode", response_model=SessionRecord)
def select_session_mode(session_id: str, payload: dict[str, str]) -> SessionRecord:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    mode = payload.get("mode")
    if mode not in {"library", "generate"}:
        raise HTTPException(status_code=400, detail="mode must be library or generate")
    session.mode = mode
    session.status = "mode_selected"
    save_session(session)
    return session


@app.post("/sessions/{session_id}/library/select", response_model=SessionRecord)
def select_library_for_session(session_id: str, payload: dict[str, str]) -> SessionRecord:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.mode != "library":
        raise HTTPException(status_code=400, detail="Session mode must be library")
    pack_id = payload.get("pack_id")
    if not pack_id:
        raise HTTPException(status_code=400, detail="pack_id is required")
    try:
        published = publish_pack(pack_id=pack_id, destination="runtime_cache")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.selected_pack_id = pack_id
    session.runtime_pack_path = published.published_path
    session.status = "ready_for_runtime"
    save_session(session)
    return session


@app.post("/sessions/{session_id}/generate/start", response_model=SessionRecord)
def start_generate_session(session_id: str, payload: dict) -> SessionRecord:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.mode != "generate":
        raise HTTPException(status_code=400, detail="Session mode must be generate")

    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    min_colors = int(payload.get("min_colors", 2))
    max_colors = int(payload.get("max_colors", 6))
    if min_colors < 2 or max_colors > 6 or min_colors > max_colors:
        raise HTTPException(status_code=400, detail="Color range must be between 2 and 6")

    # Force session generate flow to nano_banana_pro.
    backend = "nano_banana_pro"
    request_payload = {
        "prompt": prompt,
        "min_colors": min_colors,
        "max_colors": max_colors,
        "backend": backend,
        "count": 1,
    }
    try:
        with httpx.Client(timeout=STEP_HTTP_TIMEOUT_SECONDS) as client:
            response = client.post(f"{STEP_GENERATE_URL}/run", json=request_payload)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        session.status = "failed"
        session.error = f"generate step failed: {exc}"
        save_session(session)
        raise HTTPException(status_code=502, detail=session.error) from exc

    session.user_prompt = prompt
    session.min_colors = min_colors
    session.max_colors = max_colors
    session.candidates = [CandidateImage.model_validate(item) for item in data.get("candidates", [])]
    session.status = "candidates_generated"
    save_session(session)
    return session


@app.post("/sessions/{session_id}/generate/select", response_model=SessionRecord)
def select_generated_candidate(session_id: str, payload: dict[str, str]) -> SessionRecord:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.mode != "generate" or session.status != "candidates_generated":
        raise HTTPException(status_code=400, detail="Invalid session state for candidate selection")

    candidate_id = payload.get("candidate_id")
    if not candidate_id:
        raise HTTPException(status_code=400, detail="candidate_id is required")
    if not any(item.candidate_id == candidate_id for item in session.candidates):
        raise HTTPException(status_code=400, detail="candidate_id not found in generated candidates")
    selected_candidate = next((item for item in session.candidates if item.candidate_id == candidate_id), None)
    if not selected_candidate:
        raise HTTPException(status_code=400, detail="candidate_id not found in generated candidates")
    selected_candidate_uri = (
        selected_candidate.uri if hasattr(selected_candidate, "uri") else str(selected_candidate.get("uri", ""))
    )
    if not selected_candidate_uri:
        raise HTTPException(status_code=400, detail="Selected candidate does not contain uri")

    session.selected_candidate_id = candidate_id
    session.selected_candidate_uri = selected_candidate_uri
    session.status = "candidate_selected"
    save_session(session)

    try:
        with httpx.Client(timeout=STEP_HTTP_TIMEOUT_SECONDS) as client:
            r_vec = client.post(
                f"{STEP_VECTORIZE_URL}/run",
                json={
                    "session_id": session_id,
                    "candidate_id": candidate_id,
                    "candidate_uri": selected_candidate_uri,
                    "layer_count": session.max_colors,
                },
            )
            r_vec.raise_for_status()
            vec_payload = r_vec.json()
            session.status = "vectorized"
            save_session(session)
            r_seg = client.post(
                f"{STEP_SEGMENT_URL}/run",
                json={
                    "session_id": session_id,
                    "candidate_id": candidate_id,
                    "prepared_image_path": vec_payload.get("prepared_image_path"),
                    "layer_count": session.max_colors,
                },
            )
            r_seg.raise_for_status()
            seg_payload = r_seg.json()
        session.status = "segmented"
        session.vector_preview_uri = _to_data_uri(seg_payload.get("master_svg_path"))
        session.palette_variants = []
        save_session(session)
    except Exception as exc:
        session.status = "failed"
        session.error = f"vectorize step failed: {exc}"
        save_session(session)
        raise HTTPException(status_code=502, detail=session.error) from exc
    return session


@app.post("/sessions/{session_id}/variant/select", response_model=SessionRecord)
def select_palette_variant(session_id: str, payload: dict[str, str]) -> SessionRecord:
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.mode != "generate" or session.status != "palette_variants_generated":
        raise HTTPException(status_code=400, detail="Invalid session state for variant selection")

    pack_id = payload.get("pack_id")
    if not pack_id:
        raise HTTPException(status_code=400, detail="pack_id is required")
    match = next((item for item in session.palette_variants if item.get("pack_id") == pack_id), None)
    if not match:
        raise HTTPException(status_code=400, detail="pack_id not found in variants")
    try:
        runtime_copy = publish_pack(pack_id=pack_id, destination="runtime_cache")
        publish_pack(pack_id=pack_id, destination="library")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"publish failed: {exc}") from exc

    session.selected_pack_id = pack_id
    session.runtime_pack_path = runtime_copy.published_path
    session.status = "ready_for_runtime"
    save_session(session)
    return session


@app.post("/jobs", response_model=JobRecord)
def create_job(payload: GenerationRequest) -> JobRecord:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = JobRecord.new(job_id=job_id, request=payload)
    save_job(job)
    return job


@app.get("/jobs/{job_id}", response_model=JobRecord)
def get_job(job_id: str) -> JobRecord:
    job = load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs/{job_id}/generate", response_model=CandidateShortlist)
def generate_job_candidates(job_id: str) -> CandidateShortlist:
    job = load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        candidates = run_generation(job, count=6)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Generation backend failure: {exc}") from exc
    job.shortlist = candidates[:4]
    job.status = "candidates_ready"
    save_job(job)
    return CandidateShortlist(items=job.shortlist)


@app.get("/jobs/{job_id}/shortlist", response_model=CandidateShortlist)
def get_shortlist(job_id: str) -> CandidateShortlist:
    job = load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return CandidateShortlist(items=job.shortlist)


@app.post("/jobs/{job_id}/selection/composition", response_model=JobRecord)
def select_composition(job_id: str, payload: SelectCompositionRequest) -> JobRecord:
    job = load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {"candidates_ready", "composition_selected"}:
        raise HTTPException(status_code=400, detail="Invalid job state for composition selection")
    if not any(item.candidate_id == payload.candidate_id for item in job.shortlist):
        raise HTTPException(status_code=400, detail="Candidate is not in shortlist")
    job.selected_candidate_id = payload.candidate_id
    job.status = "composition_selected"
    save_job(job)
    return job


@app.post("/jobs/{job_id}/selection/palette", response_model=JobRecord)
def select_palette(job_id: str, payload: SelectPaletteRequest) -> JobRecord:
    job = load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {"composition_selected", "palette_selected"}:
        raise HTTPException(status_code=400, detail="Invalid job state for palette selection")
    if not job.selected_candidate_id:
        raise HTTPException(status_code=400, detail="Select composition first")
    if len(payload.colors) > job.request.max_colors:
        raise HTTPException(status_code=400, detail="Palette exceeds max_colors from request")
    job.selected_palette = payload.colors
    job.status = "palette_selected"
    save_job(job)
    return job


@app.post("/jobs/{job_id}/build", response_model=PackBuildResponse)
def build_job_pack(job_id: str) -> PackBuildResponse:
    job = load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "palette_selected":
        raise HTTPException(status_code=400, detail="Invalid job state for build")
    try:
        result = build_pack(job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job.pack_id = result.pack_id
    job.status = "packed"
    save_job(job)
    return result


@app.post("/packs/{pack_id}/publish", response_model=PublishPackResponse)
def publish(pack_id: str, payload: PublishPackRequest) -> PublishPackResponse:
    try:
        published = publish_pack(pack_id=pack_id, destination=payload.destination)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    job = find_job_by_pack_id(pack_id)
    if job:
        job.status = "published"
        save_job(job)
    return published


@app.get("/packs/{pack_id}/validate", response_model=ValidationReport)
def validate_pack(pack_id: str) -> ValidationReport:
    manifest_path = PACKS_DIR / pack_id / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"Manifest not found for pack: {pack_id}")
    return validate_manifest(manifest_path)
