# System Overview — PermitAgent

## Narrative-to-Bureaucratic Alignment

Film production exists at the intersection of creative storytelling and municipal bureaucracy. Every scene a director envisions must be translated into a set of permits, notifications, insurance requirements, and safety plans before it can be legally filmed on location.

**PermitAgent** automates this translation. It takes a creative description of a scene — written in the language of filmmakers — and produces a structured compliance plan written in the language of permit offices, city agencies, and insurance underwriters.

This process is what we call **narrative-to-bureaucratic alignment**: bridging the gap between "what the story needs" and "what the city requires."

## Multi-Agent Architecture

PermitAgent uses a pipeline of six specialized agents, each responsible for one stage of the alignment process:

| # | Agent | Responsibility |
|---|-------|---------------|
| 1 | **Scene Breakdown** | Parse free-text scene descriptions into structured production elements |
| 2 | **Environment Classifier** | Identify the filming environment type, jurisdiction, and constraints |
| 3 | **Exposure Detector** | Flag elements that require special permits or notifications |
| 4 | **Rule Matcher** | Find applicable regulations and requirements for each exposure |
| 5 | **Document Aligner** | Generate a permit-ready compliance plan |
| 6 | **Compliance Simulator** | Model risks and recommend alternatives |

Agents 2 and 3 run in parallel (they depend only on the scene breakdown, not on each other). All other agents run sequentially.

## Design Principles

- **Structured I/O**: Every agent consumes and produces Pydantic-validated data structures. No free-text chaining.
- **Deterministic fallback**: Heuristic logic runs when the LLM is unavailable, ensuring the pipeline always produces output.
- **Modular agents**: Each agent is a standalone Python function. Agents can be tested, replaced, or upgraded independently.
- **Pipeline orchestration**: A central pipeline coordinates agent execution, including parallel dispatch where possible.
