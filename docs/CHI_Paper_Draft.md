# PermitAgent: A Multi-Agent System for Narrative-to-Bureaucratic Alignment in Film Production

---

## Abstract

Film production in urban environments requires navigating complex bureaucratic permit systems that are misaligned with the creative language of screenplays. Production teams must manually translate narrative scene descriptions into regulatory compliance documents — a time-consuming, error-prone, and expertise-dependent process. We present **PermitAgent**, a multi-agent AI system that automates the alignment between narrative film descriptions and municipal permit requirements. The system employs seven specialized agents arranged in a structured pipeline: script parsing, scene breakdown, environment classification (augmented by geocoding), exposure detection, rule matching against 40+ real Los Angeles regulations, compliance plan generation, and risk simulation. We demonstrate the system through a functional prototype integrated with GPT-4o and Google Maps APIs, featuring a web-based interface for both single-scene and full-screenplay analysis, with one-click generation of permit-ready application documents. Our work contributes (1) the concept of narrative-to-bureaucratic alignment as a design challenge, (2) a multi-agent architecture for structured regulatory translation, and (3) a working system evaluated against real LA filming regulations.

**Keywords:** multi-agent systems, film production, permit compliance, regulatory alignment, structured AI pipelines, creative industries

---

## 1. Introduction

### 1.1 The Problem

Every scene a filmmaker envisions must be translated into a set of permits, notifications, insurance requirements, and safety plans before it can be legally filmed on location. In the City of Los Angeles alone — the world's largest filming jurisdiction — productions must navigate requirements from at least seven agencies: FilmLA, LAPD, LAFD, LADOT, the Department of Recreation and Parks, the Department of Beaches and Harbors, and the FAA.

This translation process suffers from three fundamental challenges:

1. **Language mismatch.** Screenplays are written in cinematic language ("EXT. VENICE BEACH - NIGHT. A drone rises over the boardwalk as actors sprint through a crowd"). Permit applications require bureaucratic specificity ("Request for FilmLA Master Permit with Drone Supplemental, FAA Part 107 waiver, LAANC airspace authorization, and crowd management plan for 50+ background performers at a public beach location under the jurisdiction of the Department of Beaches and Harbors").

2. **Regulatory fragmentation.** Requirements are spread across municipal codes (LAMC), agency guidelines (FilmLA), federal regulations (FAA Part 107), and department-specific rules (LAFD Film Unit). No single document contains all applicable rules for a given scene.

3. **Contextual complexity.** The same scene element carries different regulatory weight depending on location, time, proximity to sensitive sites, and combination with other elements. A prop firearm 1,001 feet from a school has different requirements than one 999 feet from a school.

Currently, this translation is performed manually by production coordinators and location managers — experienced professionals who accumulate regulatory knowledge over years of practice. This creates barriers for independent filmmakers, student productions, and out-of-state crews unfamiliar with local regulations.

### 1.2 Our Approach

We introduce the concept of **narrative-to-bureaucratic alignment** — the structured translation of creative production descriptions into regulatory compliance documents — and present **PermitAgent**, a multi-agent AI system that automates this process.

PermitAgent decomposes the alignment problem into a pipeline of seven specialized agents, each responsible for one stage of the translation. The agents operate on structured data (Pydantic-validated schemas), not free text, ensuring that each handoff between agents is typed, validated, and auditable.

### 1.3 Contributions

This paper makes three contributions:

1. **Conceptual:** We define narrative-to-bureaucratic alignment as a design challenge at the intersection of HCI, AI, and regulatory compliance, with implications beyond film production.

2. **Architectural:** We present a multi-agent pipeline architecture that decomposes regulatory translation into discrete, testable, and independently upgradable stages — an alternative to monolithic LLM approaches.

3. **System:** We contribute a working prototype evaluated against 40+ real Los Angeles filming regulations, demonstrating that structured multi-agent systems can produce permit-ready compliance documents from screenplay input.

---

## 2. Related Work

### 2.1 AI in Creative Industries

Recent work has explored AI assistance for various stages of creative production, including scriptwriting [1], storyboarding [2], and pre-visualization [3]. However, the administrative and regulatory aspects of production — the "bureaucratic layer" that enables creative work to happen in physical spaces — has received comparatively little attention. Our work addresses this gap by focusing on the post-creative, pre-production compliance process.

### 2.2 Multi-Agent Systems

Multi-agent architectures have gained traction for complex reasoning tasks. Systems like AutoGen [4], CrewAI [5], and LangGraph [6] demonstrate that decomposing problems into specialized agents can outperform monolithic approaches. PermitAgent extends this paradigm to regulatory compliance, where the decomposition maps naturally onto distinct stages of bureaucratic analysis: identification, classification, matching, and document generation.

### 2.3 Regulatory Technology (RegTech)

The RegTech domain has explored automated compliance checking in finance [7], construction [8], and healthcare [9]. Building code compliance checking (e.g., [10]) is particularly relevant, as it involves matching physical design elements against codified rules. PermitAgent adapts this approach to a domain where the "design elements" are narrative descriptions rather than architectural specifications, requiring an additional natural language understanding step.

### 2.4 Document Generation and Alignment

Prior work on document generation from structured data [11] and cross-domain alignment (e.g., medical records to insurance claims [12]) informs our approach. PermitAgent's document alignment agent extends these techniques to the film-permit domain, where the source language (cinematic) and target language (bureaucratic) have distinct vocabularies, structures, and purposes.

---

## 3. System Design

### 3.1 Design Rationale

We adopted a structured pipeline architecture rather than a monolithic LLM approach for three reasons:

1. **Auditability.** Each agent produces a typed, inspectable intermediate result. Production coordinators can verify the system's reasoning at every stage — critical in a domain where errors have legal and financial consequences.

2. **Modularity.** Individual agents can be upgraded, replaced, or fine-tuned independently. As regulations change, the rule database can be updated without retraining the entire system.

3. **Graceful degradation.** Each agent includes heuristic fallback logic that runs when the LLM is unavailable, ensuring the pipeline always produces output — even if reduced in quality.

### 3.2 Pipeline Architecture

PermitAgent processes input through seven sequential stages, with stages 2 and 3 executing in parallel:

```
SceneInput (or full screenplay)
    │
    ▼
[Agent 0] Script Parser — splits screenplay into individual scenes
    │
    ▼
[Agent 1] Scene Breakdown — extracts structured production elements
    │
    ├── parallel ──┐
    ▼               ▼
[Agent 2]       [Agent 3]
Environment     Exposure
Classifier      Detector
(+ geocoding)
    │               │
    └───────┬───────┘
            ▼
[Agent 4] Rule Matcher — matches against regulation database
            ▼
[Agent 5] Document Aligner — generates permit-ready compliance plan
            ▼
[Agent 6] Compliance Simulator — models risks and alternatives
            ▼
        PipelineResult + DOCX Export
```

### 3.3 Data Schemas

All inter-agent communication uses Pydantic-validated data models. The core schemas include:

| Schema | Purpose | Key Fields |
|--------|---------|------------|
| SceneInput | Pipeline input | scene_text, location, notes |
| SceneBreakdown | Structured scene elements | time_of_day, INT/EXT, props, vehicles, crowd_size, SFX |
| EnvironmentClassification | Location intelligence | environment_type, jurisdiction, nearby_sensitive_sites |
| ExposureReport | Reportable elements | list of exposures with category, risk_level, notifications |
| RuleMatchResult | Applicable regulations | matched rules with code citations, unmatched exposures |
| CompliancePlan | Permit application package | permits, notifications, insurance, conditions, lead_time |
| ComplianceSimulation | Risk assessment | scenarios with probability, impact, mitigation, feasibility |

### 3.4 Agent Design

Each agent follows a consistent pattern:

```python
def run_agent(input: TypedInput) -> TypedOutput:
    # 1. Try LLM with structured prompt
    llm_result = llm_call(prompt, system_prompt)
    if llm_result:
        return parse_and_validate(llm_result)

    # 2. Fall back to heuristic logic
    return heuristic_fallback(input)
```

This dual-path design ensures reliability while leveraging LLM capabilities when available.

---

## 4. Implementation

### 4.1 Technology Stack

- **Backend:** Python 3.9, FastAPI
- **Frontend:** Streamlit with custom CSS (FilmLA-inspired design)
- **LLM:** OpenAI GPT-4o via structured JSON prompting
- **Geocoding:** Google Maps Geocoding API + Places API
- **Document Generation:** python-docx for DOCX permit packages
- **Data Validation:** Pydantic v2

### 4.2 Regulation Database

We compiled 40+ real Los Angeles filming regulations from eight source categories into structured JSON files:

| Source | Regulations | Examples |
|--------|------------|----------|
| FilmLA | 6 rules | Master permit ($625/day), insurance ($1M GL), notification (500ft, 24hrs) |
| LAMC Noise | 5 rules | Generator limits (75 dBA at 50ft), quiet hours (10PM-7AM) |
| Weapons | 4 rules | LAPD notification, armorer required, 1000ft school buffer |
| FAA/Drone | 7 rules | Part 107, LAANC, Remote ID, $5M aircraft insurance |
| LAFD/Fire | 5 rules | Pyro permit, FSO ($80-110/hr), Red Flag restrictions |
| LADOT | 3 rules | Lane closure (no rush hour), traffic control plan, parking |
| Parks/Beaches | 7 rules | Rec & Parks permit, beach vehicle restrictions, Griffith Park |
| Sensitive Sites | 4 rules | School 1000ft buffer, hospital 500ft, government buildings |

### 4.3 Geocoding Integration

The environment classification agent integrates Google Maps APIs to provide:

1. **Jurisdiction resolution** — automatically determines which city's film office governs a location (supports 10 LA-area jurisdictions)
2. **Sensitive site detection** — searches for schools, hospitals, fire stations, police stations, churches, and government offices within 1,000 feet of the filming location
3. **Distance calculation** — reports exact distance to each sensitive site, enabling precise buffer zone compliance checks

### 4.4 Document Generation

The system generates professional DOCX permit application packages containing eight sections:

1. Production Information (template fields for company details)
2. Location Details (environment, jurisdiction, sensitive sites)
3. Activity Description (permit-ready narrative)
4. Reportable Elements (exposure table with risk levels)
5. Applicable Regulations (all matched rules with code citations)
6. Required Permits & Notifications (checklist with checkboxes)
7. Compliance Risk Assessment (scenarios and mitigations)
8. Submission Checklist (complete filing requirements)

### 4.5 Frontend Interface

The Streamlit-based interface supports two analysis modes:

- **Single Scene Mode** — analyze individual scene descriptions with sample presets
- **Full Script Mode** — upload complete screenplays (PDF, DOCX, TXT, FDX/Final Draft, Fountain) for multi-scene analysis with aggregated compliance reporting

Results are displayed across seven tabbed views: Scene Breakdown, Environment, Exposures, Rules, Compliance Plan, Risk Simulation, and Raw JSON. A download button generates the DOCX permit package.

---

## 5. Evaluation

### 5.1 Technical Validation

We validated the system against five representative filming scenarios spanning the risk spectrum:

| Scenario | Exposures Detected | Rules Matched | Feasibility |
|----------|-------------------|---------------|-------------|
| Street night shoot (rain, police cruiser, 20 extras) | 3 | 8 | 72% |
| Park dialogue (simple, 2 actors) | 0 | 4 | 95% |
| Drone beach shot (50 extras, sunset) | 3 | 5 | 75% |
| Prop weapon scene (pistol, rifle, smoke) | 3 | 12 | 68% |
| Small indoor shoot (coffee shop, 6 crew) | 0 | 3 | 98% |

The system correctly identified all expected reportable elements and matched them to the appropriate regulations in each case.

### 5.2 Full Script Analysis

A 5-scene sample screenplay was processed end-to-end:

- **5 scenes** automatically parsed from slug lines
- **10 total exposures** detected across all scenes
- **45 rules** matched from the regulation database
- **9 unique permits** identified as required
- **Overall feasibility: 75%** with 1 high-risk scene flagged
- Processing time: ~30 seconds (including 5 LLM calls per scene)

### 5.3 User Study

> [TODO: Conduct user study with 5-10 film production professionals]
>
> **Planned study design:**
> - **Participants:** Production coordinators, location managers, independent filmmakers
> - **Task:** Analyze 3 scenes using PermitAgent vs. manual research
> - **Measures:** Time to complete, accuracy of identified permits, subjective workload (NASA-TLX), perceived usefulness (SUS)
> - **Qualitative:** Semi-structured interviews on trust, utility, and workflow integration

---

## 6. Discussion

### 6.1 Design Implications

**DI-1: Structured pipelines over monolithic prompts for regulatory domains.** Decomposing regulatory analysis into typed, validated stages provides auditability and error isolation that monolithic LLM approaches cannot. When a rule match is incorrect, users can identify exactly which agent produced the error without re-examining the entire analysis.

**DI-2: Graceful degradation preserves utility under failure.** The dual-path design (LLM + heuristic fallback) ensures the system remains functional even when API services are unavailable — a practical necessity for production environments with unreliable connectivity.

**DI-3: Geographic context transforms regulatory analysis.** Integrating geocoding elevated the system's output from "generically plausible" to "location-specific and actionable." The difference between identifying "a school might be nearby" and "Westminster Avenue Elementary School is 627 feet from this location" is the difference between advisory and operational intelligence.

**DI-4: Document generation as a trust mechanism.** Producing a familiar artifact — a structured permit application document — made the system's output legible to domain experts. The document format serves as both a deliverable and a verification surface.

### 6.2 Narrative-to-Bureaucratic Alignment as a General Pattern

While PermitAgent targets film production, narrative-to-bureaucratic alignment appears in many domains:

- **Event planning** → municipal event permits
- **Construction** → building permits from architectural narratives
- **Medical procedures** → insurance pre-authorization from clinical descriptions
- **Academic research** → IRB applications from study descriptions

The multi-agent pipeline architecture could generalize to any domain where creative or professional descriptions must be translated into regulatory compliance documents.

### 6.3 Limitations

1. **Regulation coverage.** The current database covers City of Los Angeles regulations. Other jurisdictions (Santa Monica, Burbank, Culver City) have separate requirements not yet included.

2. **LLM reliability.** While structured prompting and validation catch many errors, the LLM can still hallucinate regulation details. The heuristic fallback provides a safety net but with reduced analytical depth.

3. **No feedback loop.** The system does not learn from actual permit outcomes. A production that is denied a permit does not inform future analyses.

4. **Static rules.** Regulations change. The JSON rule database requires manual updates, though the modular structure makes this straightforward.

### 6.4 Future Work

- **Longitudinal deployment** with a production company to evaluate real-world impact on permit approval rates and preparation time
- **Expansion** to additional jurisdictions and regulatory domains
- **Feedback integration** using permit outcomes to refine risk models
- **Collaborative features** enabling production teams to annotate and override agent outputs

---

## 7. Conclusion

We presented PermitAgent, a multi-agent system for narrative-to-bureaucratic alignment in film production. The system demonstrates that structured AI pipelines — with typed data flows, domain-specific regulation databases, and geographic intelligence — can automate the translation of creative scene descriptions into permit-ready compliance documents. Our prototype, evaluated against 40+ real Los Angeles filming regulations, correctly identifies reportable elements, matches applicable rules, and generates actionable permit application packages. By introducing narrative-to-bureaucratic alignment as a design challenge, we open a research direction with applications across creative industries, event management, and regulatory compliance at large.

---

## References

[1] Mirowski, P., et al. "Co-Writing Screenplays and Theatre Scripts with Language Models." CHI 2023.

[2] Huang, Y., et al. "StoryDALL-E: Adapting Pretrained Text-to-Image Transformers for Story Continuation." ECCV 2022.

[3] Zhu, W., et al. "Automated Pre-visualization with AI-driven Storyboarding." ACM MM 2023.

[4] Wu, Q., et al. "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation." arXiv 2023.

[5] Moura, J. "CrewAI: Framework for Orchestrating Role-Playing Autonomous AI Agents." GitHub 2024.

[6] LangChain. "LangGraph: Building Stateful Multi-Agent Applications." 2024.

[7] Arner, D., et al. "FinTech and RegTech in a Nutshell." Journal of Banking and Finance Law 2017.

[8] Eastman, C., et al. "Automatic Rule-Based Checking of Building Designs." Automation in Construction 2009.

[9] Becker, M., et al. "Automated Compliance Checking in Healthcare." JMIR 2021.

[10] Solihin, W., et al. "A Framework for Fully Integrated Building Information Models in Regulatory Compliance Checking." BIM 2015.

[11] Wiseman, S., et al. "Challenges in Data-to-Document Generation." EMNLP 2017.

[12] Shi, H., et al. "Cross-domain Clinical Document Alignment for Insurance Claims." AMIA 2020.

---

> **Note:** References [1]-[12] are representative placeholders. Replace with actual citations during final preparation. Conduct a thorough literature review to identify the most relevant and recent works in each area.

---

## Appendix A: System Screenshots

> [TODO: Add screenshots of the PermitAgent interface showing:]
> 1. Landing page with pipeline visualization
> 2. Single scene analysis — Scene Breakdown tab
> 3. Single scene analysis — Exposures tab with risk badges
> 4. Single scene analysis — Rules tab with regulation citations
> 5. Single scene analysis — Compliance Plan tab
> 6. Single scene analysis — Risk Simulation with feasibility gauge
> 7. Full script mode — Summary dashboard
> 8. Full script mode — Scene-by-scene view
> 9. Generated DOCX permit application document

## Appendix B: Sample Pipeline Output

> [TODO: Include a complete JSON output for one representative scene to demonstrate the structured data flow between agents]
