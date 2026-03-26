"""
exposure_detector.py — Reportable Exposure Detection Agent

Scans the scene breakdown for elements that require special permits,
notifications, or insurance — such as drones, weapons, pyrotechnics,
large crowds, animals, and stunts.

Input:  SceneBreakdown
Output: ExposureReport
"""

from __future__ import annotations

from app.schemas import (
    ExposureReport,
    ReportableExposure,
    RiskLevel,
    SceneBreakdown,
)
from app.llm import llm_call

_SYSTEM = """You are a film production safety and compliance expert for Los Angeles.

Given a structured scene breakdown, identify ALL elements that require special
permits, agency notifications, additional insurance, or on-set safety personnel.

Output ONLY valid JSON:
{
  "exposures": [
    {
      "element": "name of the reportable element",
      "category": "equipment|weapons|pyrotechnics|crowd|vehicles|animals|stunts|safety",
      "risk_level": "low|medium|high|critical",
      "description": "why this element is reportable",
      "requires_notification": ["list of agencies to notify"]
    }
  ],
  "overall_risk": "low|medium|high|critical"
}

Rules:
- Be conservative: when in doubt, flag it.
- Distinguish between real and prop weapons but flag both.
- Flag crowds of 25+ people.
- Include wet-down/rain effects, animals, stunts, lane closures.
- For requires_notification, use real agency names (LAPD, LAFD, FilmLA, FAA, LADOT, etc.)."""

# Static exposure rules for heuristic fallback
_EXPOSURE_RULES: dict[str, dict] = {
    "drone": {
        "category": "equipment", "risk": RiskLevel.HIGH,
        "description": "FAA-regulated UAS operation; requires Part 107 waiver and drone supplemental permit.",
        "notifications": ["FAA", "LAPD Air Support", "FilmLA"],
    },
    "gun": {
        "category": "weapons", "risk": RiskLevel.CRITICAL,
        "description": "Prop firearm on set; requires weapons handler, LAPD notification, and safety briefing.",
        "notifications": ["LAPD", "FilmLA", "On-set Safety Coordinator"],
    },
    "rifle": {
        "category": "weapons", "risk": RiskLevel.CRITICAL,
        "description": "Prop rifle on set; same requirements as prop firearms.",
        "notifications": ["LAPD", "FilmLA"],
    },
    "pistol": {
        "category": "weapons", "risk": RiskLevel.CRITICAL,
        "description": "Prop pistol on set.",
        "notifications": ["LAPD", "FilmLA"],
    },
    "knife": {
        "category": "weapons", "risk": RiskLevel.MEDIUM,
        "description": "Prop edged weapon; safety coordinator recommended.",
        "notifications": ["FilmLA"],
    },
    "explosion": {
        "category": "pyrotechnics", "risk": RiskLevel.CRITICAL,
        "description": "Pyrotechnic effect; requires licensed pyrotechnician and fire department standby.",
        "notifications": ["LAFD", "LAPD", "FilmLA"],
    },
    "pyro": {
        "category": "pyrotechnics", "risk": RiskLevel.CRITICAL,
        "description": "Pyrotechnic effect.",
        "notifications": ["LAFD", "LAPD", "FilmLA"],
    },
    "fire": {
        "category": "pyrotechnics", "risk": RiskLevel.HIGH,
        "description": "Open flame on set; fire safety officer and LAFD notification required.",
        "notifications": ["LAFD", "FilmLA"],
    },
    "smoke": {
        "category": "pyrotechnics", "risk": RiskLevel.MEDIUM,
        "description": "Smoke effects may trigger public safety concerns.",
        "notifications": ["LAFD", "FilmLA"],
    },
    "helicopter": {
        "category": "equipment", "risk": RiskLevel.HIGH,
        "description": "Aerial filming with manned aircraft; FAA coordination required.",
        "notifications": ["FAA", "FilmLA"],
    },
    "car": {
        "category": "vehicles", "risk": RiskLevel.MEDIUM,
        "description": "Vehicle action may require lane closures and traffic control.",
        "notifications": ["LADOT", "FilmLA"],
    },
    "motorcycle": {
        "category": "vehicles", "risk": RiskLevel.MEDIUM,
        "description": "Motorcycle action on public roads.",
        "notifications": ["LADOT", "FilmLA"],
    },
}

_CROWD_THRESHOLDS = [
    (100, RiskLevel.HIGH, "Large crowd (100+); requires crowd management plan."),
    (25, RiskLevel.MEDIUM, "Moderate crowd (25-99); additional safety measures recommended."),
]

_RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    return a if _RISK_ORDER[a] >= _RISK_ORDER[b] else b


def run_exposure_detection(breakdown: SceneBreakdown) -> ExposureReport:
    """
    Detect reportable exposures from the scene breakdown.
    Tries LLM first; falls back to heuristic keyword matching.
    """
    # --- Try LLM ---
    prompt = (
        f"Scene breakdown:\n"
        f"- Setting: {breakdown.setting_description}\n"
        f"- Time: {breakdown.time_of_day}\n"
        f"- INT/EXT: {breakdown.interior_exterior}\n"
        f"- Characters: {', '.join(breakdown.characters) if breakdown.characters else 'none listed'}\n"
        f"- Props: {', '.join(breakdown.props) if breakdown.props else 'none'}\n"
        f"- Vehicles: {', '.join(breakdown.vehicles) if breakdown.vehicles else 'none'}\n"
        f"- Crowd size: {breakdown.crowd_size_estimate}\n"
        f"- Special effects: {', '.join(breakdown.special_effects) if breakdown.special_effects else 'none'}\n"
        f"- Summary: {breakdown.summary}"
    )

    llm_result = llm_call(prompt=prompt, system=_SYSTEM)

    if llm_result and "exposures" in llm_result:
        exposures = []
        for exp in llm_result["exposures"]:
            try:
                risk = RiskLevel(exp.get("risk_level", "medium"))
            except ValueError:
                risk = RiskLevel.MEDIUM
            exposures.append(ReportableExposure(
                element=exp.get("element", "unknown"),
                category=exp.get("category", "safety"),
                risk_level=risk,
                description=exp.get("description", ""),
                requires_notification=exp.get("requires_notification", []),
            ))

        try:
            overall = RiskLevel(llm_result.get("overall_risk", "medium"))
        except ValueError:
            overall = RiskLevel.MEDIUM

        return ExposureReport(
            scene_id=breakdown.scene_id,
            exposures=exposures,
            overall_risk=overall,
        )

    # --- Heuristic fallback ---
    return _heuristic_detection(breakdown)


def _heuristic_detection(breakdown: SceneBreakdown) -> ExposureReport:
    """Fallback heuristic detection."""
    exposures: list[ReportableExposure] = []
    max_risk = RiskLevel.LOW

    for source_list in [breakdown.props, breakdown.vehicles, breakdown.special_effects]:
        for item in source_list:
            item_lower = item.lower()
            if item_lower in _EXPOSURE_RULES:
                rule = _EXPOSURE_RULES[item_lower]
                exposures.append(ReportableExposure(
                    element=item,
                    category=rule["category"],
                    risk_level=rule["risk"],
                    description=rule["description"],
                    requires_notification=rule["notifications"],
                ))
                max_risk = _max_risk(max_risk, rule["risk"])

    if breakdown.crowd_size_estimate > 0:
        for threshold, risk, desc in _CROWD_THRESHOLDS:
            if breakdown.crowd_size_estimate >= threshold:
                exposures.append(ReportableExposure(
                    element=f"crowd ({breakdown.crowd_size_estimate} people)",
                    category="crowd",
                    risk_level=risk,
                    description=desc,
                    requires_notification=["FilmLA", "LAPD"],
                ))
                max_risk = _max_risk(max_risk, risk)
                break

    return ExposureReport(
        scene_id=breakdown.scene_id,
        exposures=exposures,
        overall_risk=max_risk,
    )
