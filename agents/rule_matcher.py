"""
rule_matcher.py — Rule Matching Agent

Matches detected exposures and environment classifications against
permit rules and requirements. Loads real LA regulations from the
data/rules/ JSON files and uses LLM for additional matching.

Input:  ExposureReport, EnvironmentClassification
Output: RuleMatchResult
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.schemas import (
    EnvironmentClassification,
    EnvironmentType,
    ExposureReport,
    RuleMatch,
    RuleMatchResult,
)
from app.llm import llm_call

_SYSTEM = """You are a film permit regulation expert specializing in Los Angeles municipal code (LAMC), FilmLA guidelines, and related agency requirements.

You are given:
1. A list of reportable exposures and environment classification from a scene.
2. A database of known rules already matched by the system.

Your job: identify any ADDITIONAL rules not already in the matched list. Only return NEW rules.

Output ONLY valid JSON:
{
  "additional_rules": [
    {
      "rule_id": "unique ID",
      "source": "specific regulation or code section",
      "summary": "plain-language explanation",
      "applies_to": ["which exposures"],
      "mandatory": true
    }
  ]
}

If no additional rules are needed, return: {"additional_rules": []}"""

# ---------------------------------------------------------------------------
# Load rule database from data/rules/ JSON files
# ---------------------------------------------------------------------------
_RULES_DIR = Path(__file__).resolve().parent.parent / "data" / "rules"


def _load_all_rules() -> list[dict]:
    """Load all rules from JSON files in data/rules/."""
    all_rules = []
    if not _RULES_DIR.exists():
        return all_rules
    for filepath in sorted(_RULES_DIR.glob("*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for rule in data.get("rules", []):
                rule["_source_file"] = filepath.name
                all_rules.append(rule)
        except (json.JSONDecodeError, KeyError):
            continue
    return all_rules


# Load once at module import
_RULE_DATABASE: list[dict] = _load_all_rules()


def run_rule_matching(
    exposures: ExposureReport,
    environment: EnvironmentClassification,
) -> RuleMatchResult:
    """
    Match exposures and environment against the rule database.
    Uses the real data/rules/ JSON files, then optionally asks LLM
    for any additional rules not in the database.
    """
    # --- Step 1: Heuristic matching from database ---
    matched, matched_elements = _database_matching(exposures, environment)

    # --- Step 2: Ask LLM for additional rules ---
    matched_ids = {r.rule_id for r in matched}
    exposure_list = [
        {"element": e.element, "category": e.category, "risk_level": e.risk_level.value}
        for e in exposures.exposures
    ]
    prompt = (
        f"Exposures found:\n"
        + "\n".join(f"- {e['element']} (category: {e['category']}, risk: {e['risk_level']})" for e in exposure_list)
        + f"\n\nEnvironment:\n"
        f"- Type: {environment.environment_type.value}\n"
        f"- Jurisdiction: {environment.jurisdiction}\n"
        f"- Public/Private: {environment.public_or_private}\n"
        f"- Noise restrictions: {environment.noise_restrictions}\n"
        f"- Nearby sensitive sites: {', '.join(environment.nearby_sensitive_sites) if environment.nearby_sensitive_sites else 'none'}\n\n"
        f"Rules ALREADY matched (do not repeat these):\n"
        + "\n".join(f"- [{r.rule_id}] {r.summary}" for r in matched)
    )

    llm_result = llm_call(prompt=prompt, system=_SYSTEM)

    if llm_result and "additional_rules" in llm_result:
        for rule in llm_result["additional_rules"]:
            rid = rule.get("rule_id", "LLM-UNKNOWN")
            if rid not in matched_ids:
                matched.append(RuleMatch(
                    rule_id=rid,
                    source=rule.get("source", ""),
                    summary=rule.get("summary", ""),
                    applies_to=rule.get("applies_to", []),
                    mandatory=rule.get("mandatory", True),
                ))
                matched_ids.add(rid)

    # --- Identify unmatched exposures ---
    all_labels = {e.element.lower() for e in exposures.exposures}
    unmatched = list(all_labels - matched_elements)

    return RuleMatchResult(
        scene_id=exposures.scene_id,
        matched_rules=matched,
        unmatched_exposures=unmatched,
    )


def _database_matching(
    exposures: ExposureReport,
    environment: EnvironmentClassification,
) -> tuple[list[RuleMatch], set[str]]:
    """Match exposures against the loaded rule database."""
    matched: list[RuleMatch] = []
    matched_elements: set[str] = set()
    seen_ids: set[str] = set()

    exposure_elements = {e.element.lower() for e in exposures.exposures}
    exposure_categories = {e.category.lower() for e in exposures.exposures}
    has_crowd = "crowd" in exposure_categories

    for rule_def in _RULE_DATABASE:
        rule_id = rule_def.get("rule_id", "")
        applies_to = set(rule_def.get("applies_to", []))

        if not applies_to:
            # Environment-triggered rules — check below
            continue

        # Check if any exposure element or category matches
        overlap = set()
        for target in applies_to:
            target_lower = target.lower()
            # Match against element names
            for elem in exposure_elements:
                if target_lower in elem:
                    overlap.add(elem)
            # Match against categories
            if target_lower in exposure_categories:
                overlap.add(target_lower)

        if "crowd" in applies_to and has_crowd:
            overlap.add("crowd")

        if overlap and rule_id not in seen_ids:
            matched.append(RuleMatch(
                rule_id=rule_id,
                source=rule_def.get("source", ""),
                summary=rule_def.get("summary", ""),
                applies_to=rule_def.get("applies_to", []),
                mandatory=rule_def.get("mandatory", True),
            ))
            seen_ids.add(rule_id)
            matched_elements.update(overlap)

    # --- Environment-triggered rules ---
    env_triggers = {
        EnvironmentType.PARK: ["park_filming", "PARK-PERMIT-001"],
        EnvironmentType.BEACH: ["beach_filming", "BEACH-PERMIT-001"],
    }

    for env_type, (category, _) in env_triggers.items():
        if environment.environment_type == env_type:
            for rule_def in _RULE_DATABASE:
                rid = rule_def.get("rule_id", "")
                if category in rule_def.get("applies_to", []) and rid not in seen_ids:
                    matched.append(RuleMatch(
                        rule_id=rid,
                        source=rule_def.get("source", ""),
                        summary=rule_def.get("summary", ""),
                        applies_to=rule_def.get("applies_to", []),
                        mandatory=rule_def.get("mandatory", True),
                    ))
                    seen_ids.add(rid)

    # --- Night shoot / noise rules ---
    if environment.noise_restrictions:
        for rule_def in _RULE_DATABASE:
            rid = rule_def.get("rule_id", "")
            applies = rule_def.get("applies_to", [])
            if ("night_shoot" in applies or "amplified_sound" in applies) and rid not in seen_ids:
                matched.append(RuleMatch(
                    rule_id=rid,
                    source=rule_def.get("source", ""),
                    summary=rule_def.get("summary", ""),
                    applies_to=applies,
                    mandatory=rule_def.get("mandatory", True),
                ))
                seen_ids.add(rid)

    # --- Always include master permit and insurance ---
    for always_id in ["FILMLA-PERMIT-001", "FILMLA-INSURANCE-001", "FILMLA-NOTIFY-001"]:
        if always_id not in seen_ids:
            for rule_def in _RULE_DATABASE:
                if rule_def.get("rule_id") == always_id:
                    matched.append(RuleMatch(
                        rule_id=always_id,
                        source=rule_def.get("source", ""),
                        summary=rule_def.get("summary", ""),
                        applies_to=rule_def.get("applies_to", []),
                        mandatory=rule_def.get("mandatory", True),
                    ))
                    seen_ids.add(always_id)
                    break

    return matched, matched_elements
