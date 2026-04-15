"""
document_aligner.py — Document Alignment Agent

Generates a permit-ready compliance plan by aligning the scene breakdown,
environment classification, exposure report, and matched rules.

Input:  SceneBreakdown, EnvironmentClassification, ExposureReport, RuleMatchResult
Output: CompliancePlan
"""

from __future__ import annotations

from app.schemas import (
    CompliancePlan,
    EnvironmentClassification,
    EnvironmentType,
    ExposureReport,
    RiskLevel,
    RuleMatchResult,
    SceneBreakdown,
)
from app.llm import llm_call

_SYSTEM = """You are a film permit application writer for Los Angeles productions.

Given upstream analysis (scene breakdown, environment, exposures, and matched rules),
generate a permit-ready compliance plan.

Output ONLY valid JSON:
{
  "permit_description": "professional narrative suitable for a permit application (2-4 sentences)",
  "required_permits": ["list of all permits to obtain"],
  "required_notifications": ["agencies to notify"],
  "insurance_requirements": ["policies and riders needed"],
  "conditions": ["special conditions or restrictions"],
  "estimated_lead_time_days": 10
}

Rules:
- Write the permit_description in clear, professional language suitable for FilmLA submission.
- Be specific about which permits are needed and from which agencies.
- estimated_lead_time_days should reflect realistic LA permit processing times."""

_LEAD_TIMES = {
    RiskLevel.LOW: 5,
    RiskLevel.MEDIUM: 10,
    RiskLevel.HIGH: 15,
    RiskLevel.CRITICAL: 21,
}


def run_document_alignment(
    breakdown: SceneBreakdown,
    environment: EnvironmentClassification,
    exposures: ExposureReport,
    rules: RuleMatchResult,
) -> CompliancePlan:
    """
    Produce a permit-ready compliance plan.
    Tries LLM first; falls back to template-based generation.
    """
    # --- Try LLM ---
    rules_text = "\n".join(
        f"- [{r.rule_id}] {r.summary}" for r in rules.matched_rules
    )
    exposures_text = "\n".join(
        f"- {e.element} ({e.category}, risk: {e.risk_level.value})" for e in exposures.exposures
    )

    prompt = (
        f"Scene: {breakdown.summary}\n"
        f"Setting: {breakdown.setting_description}\n"
        f"Time: {breakdown.time_of_day}, {breakdown.interior_exterior}\n"
        f"Crowd: {breakdown.crowd_size_estimate} people\n\n"
        f"Environment: {environment.environment_type.value}, {environment.public_or_private}\n"
        f"Jurisdiction: {environment.jurisdiction}\n"
        f"Noise restrictions: {environment.noise_restrictions}\n\n"
        f"Exposures:\n{exposures_text}\n\n"
        f"Matched rules:\n{rules_text}"
    )

    llm_result = llm_call(prompt=prompt, system=_SYSTEM)

    if llm_result:
        return CompliancePlan(
            scene_id=breakdown.scene_id,
            permit_description=llm_result.get("permit_description", ""),
            required_permits=llm_result.get("required_permits", []),
            required_notifications=llm_result.get("required_notifications", []),
            insurance_requirements=llm_result.get("insurance_requirements", []),
            conditions=llm_result.get("conditions", []),
            estimated_lead_time_days=llm_result.get("estimated_lead_time_days", 10),
        )

    # --- Heuristic fallback ---
    return _heuristic_alignment(breakdown, environment, exposures, rules)


def _heuristic_alignment(
    breakdown: SceneBreakdown,
    environment: EnvironmentClassification,
    exposures: ExposureReport,
    rules: RuleMatchResult,
) -> CompliancePlan:
    """Fallback template-based plan generation."""
    time_label = breakdown.time_of_day.capitalize()
    ie_label = "interior" if breakdown.interior_exterior == "INT" else "exterior"
    env_label = environment.environment_type.value

    parts = [
        f"{time_label} {ie_label} shoot at {breakdown.setting_description}",
        f"({env_label}, {environment.public_or_private} property).",
    ]
    if breakdown.crowd_size_estimate > 0:
        parts.append(f"Approximately {breakdown.crowd_size_estimate} background performers.")
    if exposures.exposures:
        elements = ", ".join(e.element for e in exposures.exposures)
        parts.append(f"Notable elements: {elements}.")

    permit_description = " ".join(parts)

    required_permits = ["FilmLA Master Permit"]
    if environment.environment_type == EnvironmentType.PARK:
        required_permits.append("Dept. of Recreation and Parks Permit")
    if environment.environment_type == EnvironmentType.BEACH:
        jurisdiction_text = environment.jurisdiction.lower()
        if "city of los angeles" in jurisdiction_text or "filmla" in jurisdiction_text:
            required_permits.append("Dept. of Recreation and Parks Permit")
        else:
            required_permits.append("Dept. of Beaches and Harbors Permit")
    for rule in rules.matched_rules:
        if "drone" in rule.summary.lower():
            required_permits.extend(["FAA Part 107 Waiver", "FilmLA Drone Supplemental"])
        if "pyrotechnic" in rule.summary.lower():
            required_permits.append("LAFD Pyrotechnics Permit")
        if "traffic" in rule.summary.lower():
            required_permits.append("LADOT Traffic Control Permit")
    required_permits = list(dict.fromkeys(required_permits))

    notification_set: set[str] = set()
    for exposure in exposures.exposures:
        notification_set.update(exposure.requires_notification)

    insurance = ["General Liability ($1M minimum)"]
    if any(e.category == "weapons" for e in exposures.exposures):
        insurance.append("Weapons / Props Rider")
    if any(e.category == "pyrotechnics" for e in exposures.exposures):
        insurance.append("Pyrotechnics Rider")
    if any(e.element.lower() == "drone" for e in exposures.exposures):
        insurance.append("Aviation / Drone Liability")

    conditions: list[str] = []
    if environment.noise_restrictions:
        conditions.append("Comply with noise ordinance — no amplified sound after 10 PM.")
    if breakdown.crowd_size_estimate >= 100:
        conditions.append("LAPD officer(s) required on site for crowd management.")
    if any(e.category == "weapons" for e in exposures.exposures):
        conditions.append("Licensed weapons handler must be present during all scenes involving prop firearms.")

    return CompliancePlan(
        scene_id=breakdown.scene_id,
        permit_description=permit_description,
        required_permits=required_permits,
        required_notifications=sorted(notification_set),
        insurance_requirements=insurance,
        conditions=conditions,
        estimated_lead_time_days=_LEAD_TIMES.get(exposures.overall_risk, 10),
    )
