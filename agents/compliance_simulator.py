"""
compliance_simulator.py — Compliance Simulation Agent

Simulates potential compliance risks and generates alternative strategies.

Input:  CompliancePlan, ExposureReport
Output: ComplianceSimulation
"""

from __future__ import annotations

from app.schemas import (
    CompliancePlan,
    ComplianceSimulation,
    ExposureReport,
    RiskLevel,
    SimulationScenario,
)
from app.llm import llm_call

_SYSTEM = """You are a film production risk analyst specializing in Los Angeles permit compliance.

Given a compliance plan and exposure report, simulate potential failure scenarios
and recommend alternative strategies.

Output ONLY valid JSON:
{
  "scenarios": [
    {
      "scenario_name": "brief description of what could go wrong",
      "probability": 0.15,
      "impact": "low|medium|high|critical",
      "mitigation": "recommended alternative strategy or contingency"
    }
  ],
  "overall_feasibility": 0.75,
  "recommendation": "summary recommendation for the production team"
}

Rules:
- Generate 3-7 realistic scenarios based on actual LA filming experience.
- Probabilities should be realistic (most between 0.05 and 0.30).
- Always suggest at least one creative alternative for high-risk scenarios.
- overall_feasibility: 1.0 = fully feasible, 0.0 = impossible.
- Be specific about mitigations — mention actual alternatives (VFX, relocation, schedule changes)."""

# Template scenarios for heuristic fallback
_SCENARIO_TEMPLATES: dict[str, list[dict]] = {
    "equipment": [
        {"scenario_name": "Drone permit denied due to airspace restrictions", "probability": 0.15,
         "impact": RiskLevel.HIGH,
         "mitigation": "Switch to crane or jib arm for elevated shots; scout locations outside restricted airspace."},
    ],
    "weapons": [
        {"scenario_name": "LAPD denies prop firearm notification — timing conflict", "probability": 0.10,
         "impact": RiskLevel.CRITICAL,
         "mitigation": "Reschedule weapon scenes; consider rubber/foam replicas that don't require notification."},
        {"scenario_name": "Nearby school triggers 1000-ft buffer zone restriction", "probability": 0.20,
         "impact": RiskLevel.HIGH,
         "mitigation": "Relocate weapon scenes to a studio lot or location outside the buffer zone."},
    ],
    "pyrotechnics": [
        {"scenario_name": "LAFD denies pyrotechnics permit during high fire-risk season", "probability": 0.25,
         "impact": RiskLevel.CRITICAL,
         "mitigation": "Use VFX for fire/explosion effects; reschedule to a lower fire-risk period."},
    ],
    "crowd": [
        {"scenario_name": "Permit imposes crowd cap below requested number", "probability": 0.20,
         "impact": RiskLevel.MEDIUM,
         "mitigation": "Split shoot across multiple days; use VFX crowd replication."},
    ],
    "vehicles": [
        {"scenario_name": "LADOT denies lane closure on requested date", "probability": 0.15,
         "impact": RiskLevel.MEDIUM,
         "mitigation": "Shift shoot to weekend/overnight; use a controlled private lot."},
    ],
}

_DEFAULT_SCENARIOS: list[dict] = [
    {"scenario_name": "Permit processing delay exceeds estimated lead time", "probability": 0.10,
     "impact": RiskLevel.MEDIUM,
     "mitigation": "Submit permits early; maintain 5+ business day buffer."},
    {"scenario_name": "Neighbor complaint triggers filming restriction", "probability": 0.10,
     "impact": RiskLevel.LOW,
     "mitigation": "Conduct advance neighbor outreach; provide production hotline number."},
]


def run_compliance_simulation(
    plan: CompliancePlan,
    exposures: ExposureReport,
) -> ComplianceSimulation:
    """
    Simulate compliance risks and generate alternative strategies.
    Tries LLM first; falls back to template-based scenarios.
    """
    # --- Try LLM ---
    exposures_text = "\n".join(
        f"- {e.element} ({e.category}, risk: {e.risk_level.value}): {e.description}"
        for e in exposures.exposures
    )
    prompt = (
        f"Compliance Plan:\n"
        f"- Description: {plan.permit_description}\n"
        f"- Required permits: {', '.join(plan.required_permits)}\n"
        f"- Notifications: {', '.join(plan.required_notifications)}\n"
        f"- Insurance: {', '.join(plan.insurance_requirements)}\n"
        f"- Conditions: {', '.join(plan.conditions) if plan.conditions else 'none'}\n"
        f"- Lead time: {plan.estimated_lead_time_days} business days\n\n"
        f"Exposures:\n{exposures_text}\n\n"
        f"Overall exposure risk: {exposures.overall_risk.value}"
    )

    llm_result = llm_call(prompt=prompt, system=_SYSTEM)

    if llm_result and "scenarios" in llm_result:
        scenarios = []
        for s in llm_result["scenarios"]:
            try:
                impact = RiskLevel(s.get("impact", "medium"))
            except ValueError:
                impact = RiskLevel.MEDIUM
            scenarios.append(SimulationScenario(
                scenario_name=s.get("scenario_name", "Unknown scenario"),
                probability=s.get("probability", 0.1),
                impact=impact,
                mitigation=s.get("mitigation", ""),
            ))
        return ComplianceSimulation(
            scene_id=plan.scene_id,
            scenarios=scenarios,
            overall_feasibility=llm_result.get("overall_feasibility", 0.5),
            recommendation=llm_result.get("recommendation", ""),
        )

    # --- Heuristic fallback ---
    return _heuristic_simulation(plan, exposures)


def _heuristic_simulation(
    plan: CompliancePlan,
    exposures: ExposureReport,
) -> ComplianceSimulation:
    """Fallback template-based simulation."""
    scenarios: list[SimulationScenario] = []
    seen: set[str] = set()

    for exposure in exposures.exposures:
        templates = _SCENARIO_TEMPLATES.get(exposure.category, [])
        for tmpl in templates:
            if tmpl["scenario_name"] not in seen:
                scenarios.append(SimulationScenario(**tmpl))
                seen.add(tmpl["scenario_name"])

    for tmpl in _DEFAULT_SCENARIOS:
        if tmpl["scenario_name"] not in seen:
            scenarios.append(SimulationScenario(**tmpl))
            seen.add(tmpl["scenario_name"])

    # Feasibility calculation
    if not scenarios:
        overall_feasibility = 1.0
    else:
        impact_weights = {RiskLevel.LOW: 0.3, RiskLevel.MEDIUM: 0.6, RiskLevel.HIGH: 0.8, RiskLevel.CRITICAL: 1.0}
        feasibility = 1.0
        for s in scenarios:
            feasibility *= (1.0 - s.probability * impact_weights.get(s.impact, 0.5))
        overall_feasibility = round(feasibility, 3)

    if overall_feasibility >= 0.8:
        recommendation = "Scene is highly feasible. Proceed with standard permit applications."
    elif overall_feasibility >= 0.5:
        recommendation = "Scene is feasible but carries moderate risk. Prepare contingency plans."
    else:
        recommendation = "Significant compliance risks. Consider simplifying elements or relocating."

    return ComplianceSimulation(
        scene_id=plan.scene_id,
        scenarios=scenarios,
        overall_feasibility=overall_feasibility,
        recommendation=recommendation,
    )
