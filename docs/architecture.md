# Architecture — PermitAgent

## Pipeline Flow

```
SceneInput (free text + location + notes)
        │
        ▼
┌─────────────────┐
│ Scene Breakdown  │  → SceneBreakdown
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────────┐
│ Env.   │ │ Exposure   │  (parallel)
│ Class. │ │ Detector   │
└───┬────┘ └─────┬──────┘
    │            │
    ▼            ▼
  EnvironmentClassification  ExposureReport
         │            │
         └─────┬──────┘
               ▼
       ┌──────────────┐
       │ Rule Matcher  │  → RuleMatchResult
       └──────┬───────┘
              ▼
       ┌──────────────┐
       │ Doc. Aligner  │  → CompliancePlan
       └──────┬───────┘
              ▼
       ┌──────────────┐
       │ Compliance   │  → ComplianceSimulation
       │ Simulator    │
       └──────────────┘
              │
              ▼
        PipelineResult
```

## Agent Details

### 1. Scene Breakdown Agent (`agents/scene_breakdown.py`)

**Input**: `SceneInput` — raw scene text, location, production notes.

**Output**: `SceneBreakdown` — time of day, INT/EXT, setting, characters, props, vehicles, crowd estimate, SFX, summary.

**Logic**: Regex and keyword extraction with a placeholder LLM call for future enrichment.

---

### 2. Environment Classification Agent (`agents/environment_classifier.py`)

**Input**: `SceneBreakdown` + location string.

**Output**: `EnvironmentClassification` — environment type, jurisdiction, sub-zone, public/private, nearby sensitive sites, noise restrictions.

**Logic**: Keyword-to-enum mapping. Jurisdiction defaults to FilmLA with overrides for Santa Monica, Burbank, Long Beach.

---

### 3. Reportable Exposure Detector (`agents/exposure_detector.py`)

**Input**: `SceneBreakdown`.

**Output**: `ExposureReport` — list of reportable exposures with categories, risk levels, and notification requirements.

**Logic**: Scans props, vehicles, SFX, and crowd size against a static exposure rules table.

---

### 4. Rule Matcher (`agents/rule_matcher.py`)

**Input**: `ExposureReport` + `EnvironmentClassification`.

**Output**: `RuleMatchResult` — matched rules with sources and summaries, plus unmatched exposures.

**Logic**: Cross-references exposures against a static rule database. Environment-triggered rules (park, beach, night) are matched separately.

---

### 5. Document Aligner (`agents/document_aligner.py`)

**Input**: `SceneBreakdown` + `EnvironmentClassification` + `ExposureReport` + `RuleMatchResult`.

**Output**: `CompliancePlan` — permit description, required permits, notifications, insurance, conditions, lead time.

**Logic**: Aggregates upstream data into a coherent permit application package.

---

### 6. Compliance Simulator (`agents/compliance_simulator.py`)

**Input**: `CompliancePlan` + `ExposureReport`.

**Output**: `ComplianceSimulation` — scenarios with probabilities and mitigations, overall feasibility score, recommendation.

**Logic**: Template-based scenario generation keyed by exposure category. Feasibility computed as a product of weighted probabilities.

## Data Flow

All inter-agent communication uses Pydantic models defined in `app/schemas.py`. There is no free-text passing between agents — every handoff is typed and validated.

## API Layer

FastAPI serves a single endpoint (`POST /analyze_scene`) that accepts a `SceneInput` and returns a `PipelineResult`. The API is defined in `app/main.py`.
