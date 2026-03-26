"""
main.py — FastAPI backend for the PermitAgent system.

Exposes a single endpoint that accepts a scene description and returns
the full pipeline analysis as structured JSON.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from app.schemas import PipelineResult, SceneInput, ScriptInput, ScriptResult
from workflows.pipeline import run_pipeline, run_script_pipeline

app = FastAPI(
    title="PermitAgent",
    description="Multi-Agent System for Narrative-to-Bureaucratic Alignment in Film Production",
    version="0.1.0",
)


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "PermitAgent"}


@app.post("/analyze_scene", response_model=PipelineResult)
def analyze_scene(scene: SceneInput) -> PipelineResult:
    """
    Analyze a scene description through the full PermitAgent pipeline.

    Accepts free-text scene descriptions and returns a structured
    compliance analysis including:
    - Scene breakdown
    - Environment classification
    - Reportable exposures
    - Matched rules
    - Compliance plan
    - Risk simulation
    """
    if not scene.scene_text.strip():
        raise HTTPException(status_code=400, detail="scene_text must not be empty.")

    result = run_pipeline(scene)
    return result


@app.post("/analyze_script", response_model=ScriptResult)
def analyze_script(script: ScriptInput) -> ScriptResult:
    """
    Analyze a full screenplay through the PermitAgent pipeline.

    Parses the script into individual scenes, analyzes each one,
    and returns aggregated compliance results.
    """
    if not script.script_text.strip():
        raise HTTPException(status_code=400, detail="script_text must not be empty.")

    result = run_script_pipeline(script)
    return result


if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT, DEBUG

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)
