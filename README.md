# PermitAgent

**A Multi-Agent System for Narrative-to-Bureaucratic Alignment in Film Production**

PermitAgent takes free-text scene descriptions and produces structured, permit-ready compliance plans. It bridges the gap between creative filmmaking language and municipal permit requirements.

## Quick Start

```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API server
cd PermitAgent
python -m app.main
```

The API will be available at `http://localhost:8000`.

## Streamlit Frontend

Run the frontend with the virtualenv Python interpreter instead of the
`venv/bin/streamlit` wrapper script. This avoids stale shebang issues if the
project folder has been moved.

```bash
cd PermitAgent
venv/bin/python -m streamlit run frontend.py
```

If you see `ModuleNotFoundError: No module named 'pydantic'`, you are almost
certainly launching Streamlit with your system Python instead of the project
virtualenv.

## Usage

Send a POST request to `/analyze_scene`:

```bash
curl -X POST http://localhost:8000/analyze_scene \
  -H "Content-Type: application/json" \
  -d '{
    "scene_text": "EXT. VENICE BEACH - NIGHT. A drone rises over the boardwalk as two actors sprint through a crowd of 50 extras.",
    "location": "Venice Beach, Los Angeles, CA",
    "notes": "Night shoot with drone."
  }'
```

The response is a full `PipelineResult` JSON containing:

- Scene breakdown
- Environment classification
- Reportable exposures
- Matched rules and regulations
- Compliance plan (permit-ready)
- Risk simulation with mitigations

## Architecture

```
SceneInput → Scene Breakdown
               │
          ┌────┴────┐
          ▼         ▼
     Environment  Exposure     (parallel)
     Classifier   Detector
          └────┬────┘
               ▼
          Rule Matcher
               ▼
         Document Aligner
               ▼
       Compliance Simulator
               │
               ▼
         PipelineResult
```

Six specialized agents run in a structured pipeline. Each agent takes typed input and produces typed output (Pydantic models). No free-text chaining.

## Project Structure

```
PermitAgent/
├── app/                 # FastAPI app, schemas, config, utilities
├── agents/              # Six specialized agent modules
├── workflows/           # Pipeline orchestration
├── data/                # Rules and exposure databases (expandable)
├── prompts/             # LLM prompt templates for each agent
├── tests/               # Sample scene test data
├── docs/                # System documentation
└── requirements.txt
```

## Current Status

This is a working prototype with heuristic logic. LLM calls are stubbed with placeholder functions ready for integration with OpenAI, Anthropic, or local models.

## API Docs

With the server running, visit `http://localhost:8000/docs` for interactive Swagger documentation.
