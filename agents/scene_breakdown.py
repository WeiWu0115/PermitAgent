"""
scene_breakdown.py — Scene Breakdown Agent

Decomposes a free-text scene description into structured production elements
such as time of day, interior/exterior, characters, props, vehicles, crowd
estimates, and special effects.

Input:  SceneInput (scene_text, location, notes)
Output: SceneBreakdown
"""

from __future__ import annotations

import re

from app.schemas import SceneBreakdown, SceneInput
from app.utils import generate_scene_id
from app.llm import llm_call

# System prompt loaded from prompts/scene_prompt.md
_SYSTEM = """You are a film production breakdown assistant.

Given a scene description or script excerpt, extract structured production elements.
Output ONLY valid JSON with these exact fields:
{
  "time_of_day": "DAY|NIGHT|DAWN|DUSK|SUNSET|SUNRISE",
  "interior_exterior": "INT|EXT",
  "setting_description": "brief description of the physical location",
  "characters": ["list of named or described characters"],
  "props": ["notable props mentioned or implied"],
  "vehicles": ["any vehicles involved"],
  "crowd_size_estimate": 0,
  "special_effects": ["SFX, VFX, practical effects"],
  "summary": "one-sentence summary of the scene"
}

Rules:
- Extract only what is explicitly stated or strongly implied.
- Do not invent elements not present in the description.
- For crowd_size_estimate, use 0 if no crowd/extras are mentioned."""


def run_scene_breakdown(scene_input: SceneInput) -> SceneBreakdown:
    """
    Analyze a raw scene description and produce a structured SceneBreakdown.

    Tries LLM first; falls back to heuristic extraction if unavailable.
    """
    scene_id = generate_scene_id()

    # --- Try LLM ---
    prompt = f"Scene description:\n{scene_input.scene_text}"
    if scene_input.location:
        prompt += f"\n\nIntended location: {scene_input.location}"
    if scene_input.notes:
        prompt += f"\n\nProduction notes: {scene_input.notes}"

    llm_result = llm_call(prompt=prompt, system=_SYSTEM)

    if llm_result:
        return SceneBreakdown(
            scene_id=scene_id,
            time_of_day=llm_result.get("time_of_day", "DAY"),
            interior_exterior=llm_result.get("interior_exterior", "EXT"),
            setting_description=llm_result.get("setting_description", ""),
            characters=llm_result.get("characters", []),
            props=llm_result.get("props", []),
            vehicles=llm_result.get("vehicles", []),
            crowd_size_estimate=llm_result.get("crowd_size_estimate", 0),
            special_effects=llm_result.get("special_effects", []),
            summary=llm_result.get("summary", ""),
        )

    # --- Heuristic fallback ---
    return _heuristic_breakdown(scene_input, scene_id)


def _heuristic_breakdown(scene_input: SceneInput, scene_id: str) -> SceneBreakdown:
    """Fallback heuristic extraction when LLM is unavailable."""
    text = scene_input.scene_text.upper()

    # Time of day
    time_of_day = "DAY"
    for token in ("NIGHT", "DAWN", "DUSK", "SUNSET", "SUNRISE"):
        if token in text:
            time_of_day = token
            break

    # Interior / Exterior
    if text.startswith("INT"):
        interior_exterior = "INT"
    elif text.startswith("EXT"):
        interior_exterior = "EXT"
    else:
        interior_exterior = "EXT"

    # Setting description
    sentences = scene_input.scene_text.split(".")
    setting_description = sentences[0].strip() if sentences else scene_input.scene_text[:80]

    # Props
    prop_keywords = [
        "drone", "gun", "rifle", "pistol", "knife", "sword", "smoke",
        "fire", "explosion", "pyro", "helicopter", "backpack", "phone",
    ]
    detected_props = [kw for kw in prop_keywords if kw in text.lower()]

    # Vehicles
    vehicle_keywords = ["car", "truck", "motorcycle", "helicopter", "boat", "bus", "police cruiser"]
    detected_vehicles = [v for v in vehicle_keywords if v in text.lower()]

    # Crowd estimate
    crowd_match = re.search(r"(\d+)\s*(extras|people|crowd|background)", text.lower())
    crowd_size = int(crowd_match.group(1)) if crowd_match else 0

    # Special effects
    sfx_keywords = ["smoke", "fire", "explosion", "pyro", "rain", "fog", "wind"]
    detected_sfx = [s for s in sfx_keywords if s in text.lower()]

    return SceneBreakdown(
        scene_id=scene_id,
        time_of_day=time_of_day,
        interior_exterior=interior_exterior,
        setting_description=setting_description,
        characters=[],
        props=detected_props,
        vehicles=detected_vehicles,
        crowd_size_estimate=crowd_size,
        special_effects=detected_sfx,
        summary=f"{interior_exterior}. {setting_description} — {time_of_day}",
    )
