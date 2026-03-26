# PermitAgent — Project Context for Claude

> Read this file first when resuming work on this project.

## What is this project?

**PermitAgent** is a CHI research prototype — a multi-agent system that takes film scene descriptions (or full screenplays) and produces structured, permit-ready compliance analysis for Los Angeles filming permits.

It is a **structured pipeline system**, NOT a chatbot.

## Current status: Fully functional prototype (v0.3.0)

Everything works end-to-end. The system is runnable and demo-ready.

## Tech stack

- **Python 3.9** (venv at `./venv`)
- **FastAPI** — API backend (`app/main.py`)
- **Streamlit** — Frontend UI (`frontend.py`)
- **OpenAI GPT-4o** — LLM for all 7 agents (with heuristic fallback)
- **Google Maps API** — Geocoding + nearby sensitive site detection
- **Pydantic** — All data structures
- **python-docx** — Permit document generation

## API keys (in `.env`)

```
OPENAI_API_KEY=sk-proj-...    # OpenAI GPT-4o
GOOGLE_MAPS_API_KEY=AIza...   # Google Maps Geocoding + Places
```

⚠️ Both keys were previously exposed in conversation. User should rotate them.

## How to run

```bash
cd /Users/wu.w4/Desktop/LA_Film/PermitAgent
source venv/bin/activate

# Frontend (primary)
streamlit run frontend.py
# → http://localhost:8501

# API server (alternative)
python -m app.main
# → http://localhost:8000/docs
```

## Architecture

### Pipeline flow

```
SceneInput (text + location + notes)
    │
    ▼
Script Parser (if full script mode)
    │ splits into individual scenes
    ▼
Scene Breakdown Agent
    │
    ├──parallel──┐
    ▼             ▼
Environment    Exposure
Classifier     Detector
(+ geocoding)
    │             │
    └──────┬──────┘
           ▼
    Rule Matcher
    (loads from data/rules/*.json)
           ▼
    Document Aligner
           ▼
    Compliance Simulator
           ▼
    PipelineResult
           ▼
    Doc Generator (DOCX export)
```

### 7 agents (all in `agents/`)

| Agent | File | Input → Output |
|-------|------|----------------|
| Script Parser | `script_parser.py` | Full screenplay → list[ParsedScene] |
| Scene Breakdown | `scene_breakdown.py` | SceneInput → SceneBreakdown |
| Environment Classifier | `environment_classifier.py` | SceneBreakdown + location → EnvironmentClassification |
| Exposure Detector | `exposure_detector.py` | SceneBreakdown → ExposureReport |
| Rule Matcher | `rule_matcher.py` | ExposureReport + EnvironmentClassification → RuleMatchResult |
| Document Aligner | `document_aligner.py` | All upstream data → CompliancePlan |
| Compliance Simulator | `compliance_simulator.py` | CompliancePlan + ExposureReport → ComplianceSimulation |

Every agent: tries LLM first → falls back to heuristic logic if LLM unavailable.

### Key files

```
PermitAgent/
├── app/
│   ├── main.py          # FastAPI endpoints: /analyze_scene, /analyze_script
│   ├── schemas.py       # All Pydantic models (SceneInput → PipelineResult → ScriptResult)
│   ├── config.py        # Env vars: API keys, model, server settings
│   ├── llm.py           # OpenAI client (centralized, all agents use this)
│   ├── geocoder.py      # Google Maps: geocoding + nearby sensitive sites
│   ├── doc_generator.py # DOCX permit package generator
│   └── utils.py         # Helpers
├── agents/              # 7 agent modules (see table above)
├── workflows/
│   └── pipeline.py      # run_pipeline() and run_script_pipeline()
├── data/rules/          # 8 JSON rule files (40+ real LA regulations)
├── prompts/             # 6 LLM prompt templates
├── frontend.py          # Streamlit UI (FilmLA-inspired dark theme)
├── tests/
│   ├── sample_scenes.json   # 5 single-scene test cases
│   └── sample_script.txt    # 5-scene sample screenplay
└── .env                 # API keys (not committed)
```

### Rule database (`data/rules/`)

8 JSON files with 40+ real regulations:

| File | Source |
|------|--------|
| `filmla_permits.json` | FilmLA permit process, fees, insurance, hours, notifications |
| `noise_ordinance.json` | LAMC Ch. XI noise rules (generator limits, quiet hours) |
| `weapons_firearms.json` | LAMC 55.07, weapons supplemental, school buffer zones |
| `drone_faa.json` | FAA Part 107, LAANC, airspace, Remote ID, night ops |
| `fire_pyrotechnics.json` | LAFD permits, FSO requirements, smoke, Red Flag days |
| `traffic_ladot.json` | LADOT lane closures, traffic control, parking |
| `parks_beaches.json` | Rec & Parks, Beaches & Harbors, Griffith Park, Venice |
| `sensitive_locations.json` | Schools (1000ft), hospitals (500ft), government buildings |

### Frontend features

- **Two modes**: Single Scene / Full Script
- **File upload**: PDF, TXT, DOCX, FDX (Final Draft), Fountain
- **7 result tabs**: Breakdown, Environment, Exposures, Rules, Compliance, Simulation, JSON
- **Document download**: DOCX permit application package with checklist
- **Visual design**: Dark navy theme inspired by filmla.com (Nunito Sans, #009cde cyan, #97d700 lime)
- **Sample data**: 5 preset scenes + 1 sample screenplay

## What has been completed

1. ✅ Full project structure (31+ files)
2. ✅ Pydantic data models (12+ schemas)
3. ✅ 7 agents with LLM + heuristic fallback
4. ✅ Pipeline with parallel execution
5. ✅ OpenAI GPT-4o integration
6. ✅ Google Maps geocoding (jurisdiction + sensitive sites)
7. ✅ 40+ real LA filming regulations in data/rules/
8. ✅ Streamlit frontend (FilmLA-inspired theme)
9. ✅ Full script analysis (multi-scene)
10. ✅ File upload (PDF, DOCX, TXT, FDX, Fountain)
11. ✅ DOCX permit package document generation
12. ✅ FastAPI backend with /analyze_scene and /analyze_script

## What could be done next

- **User experiment** — recruit film production professionals to test the system, collect feedback for CHI paper
- **Unit tests** — pytest for each agent with the 5 sample scenes
- **More cities** — add Santa Monica, Burbank, Culver City rule databases
- **Real-time permit tracking** — integrate with FilmLA's online portal status
- **Cost estimator** — calculate estimated permit fees based on the rules data
- **Calendar view** — timeline showing permit application deadlines relative to shoot dates
- **PDF export** — add PDF generation alongside DOCX
- **Authentication** — add user login if deploying publicly
- **Docker** — containerize for deployment

## User preferences

- User communicates in Chinese, respond in Chinese
- User is not deeply technical — give step-by-step instructions for terminal operations
- User prefers being shown results visually (screenshots)
- When API keys are needed, guide through the exact steps to obtain and configure them
- User's desktop path: `/Users/wu.w4/Desktop/LA_Film/PermitAgent`
