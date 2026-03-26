"""
script_parser.py — Script Parser Agent

Takes a full screenplay and splits it into individual scenes.
Uses LLM to intelligently parse scene boundaries when available,
with a regex-based fallback for standard screenplay formatting.

Input:  ScriptInput (full script text)
Output: list[ParsedScene]
"""

from __future__ import annotations

import re

from app.schemas import ParsedScene, ScriptInput
from app.llm import llm_call

_SYSTEM = """You are a professional script supervisor and screenplay parser.

Given a full screenplay or script excerpt, split it into individual scenes.

Each scene typically starts with a slug line (scene heading) like:
- EXT. LOCATION - TIME OF DAY
- INT. LOCATION - TIME OF DAY
- INT./EXT. LOCATION - TIME OF DAY

Output ONLY valid JSON:
{
  "scenes": [
    {
      "scene_number": 1,
      "slug_line": "EXT. VENICE BEACH - NIGHT",
      "scene_text": "full text of this scene including the slug line",
      "location_hint": "Venice Beach"
    }
  ]
}

Rules:
- Preserve ALL text within each scene (dialogue, action, parentheticals).
- Scene boundaries are marked by the NEXT slug line or end of script.
- Extract the location from the slug line as location_hint.
- If the script has no clear slug lines, treat the entire text as one scene.
- Number scenes sequentially starting from 1."""

# Regex pattern for standard screenplay slug lines
_SLUG_PATTERN = re.compile(
    r"^((?:INT|EXT|INT\./EXT|I/E)[\.\s]+.+?[\s\-–—]+(?:DAY|NIGHT|DAWN|DUSK|SUNSET|SUNRISE|MORNING|EVENING|CONTINUOUS|LATER|SAME))\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def run_script_parser(script_input: ScriptInput) -> list[ParsedScene]:
    """
    Parse a full script into individual scenes.
    Tries LLM first; falls back to regex parsing.
    """
    text = script_input.script_text.strip()
    if not text:
        return []

    # --- Try LLM ---
    prompt = f"Parse the following screenplay into individual scenes:\n\n{text}"
    llm_result = llm_call(prompt=prompt, system=_SYSTEM, max_tokens=8192)

    if llm_result and "scenes" in llm_result:
        scenes = []
        for s in llm_result["scenes"]:
            scenes.append(ParsedScene(
                scene_number=s.get("scene_number", len(scenes) + 1),
                slug_line=s.get("slug_line", "UNKNOWN"),
                scene_text=s.get("scene_text", ""),
                location_hint=s.get("location_hint", ""),
            ))
        if scenes:
            return scenes

    # --- Regex fallback ---
    return _regex_parse(text)


def _regex_parse(text: str) -> list[ParsedScene]:
    """Parse screenplay using regex to find slug lines."""
    # Find all slug line positions
    matches = list(_SLUG_PATTERN.finditer(text))

    if not matches:
        # No slug lines found — treat entire text as one scene
        # Try a simpler pattern
        simple_matches = list(re.finditer(
            r"^((?:INT|EXT)[\.\s]+.+)$",
            text,
            re.IGNORECASE | re.MULTILINE,
        ))
        if simple_matches:
            matches = simple_matches
        else:
            return [ParsedScene(
                scene_number=1,
                slug_line="SCENE 1",
                scene_text=text,
                location_hint="",
            )]

    scenes: list[ParsedScene] = []
    for i, match in enumerate(matches):
        slug_line = match.group(1).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        scene_text = text[start:end].strip()
        location_hint = _extract_location(slug_line)

        scenes.append(ParsedScene(
            scene_number=i + 1,
            slug_line=slug_line,
            scene_text=scene_text,
            location_hint=location_hint,
        ))

    return scenes


def _extract_location(slug_line: str) -> str:
    """Extract location from a slug line like 'EXT. VENICE BEACH - NIGHT'."""
    # Remove INT./EXT. prefix
    cleaned = re.sub(r"^(?:INT\./EXT|INT|EXT|I/E)[\.\s]+", "", slug_line, flags=re.IGNORECASE)
    # Remove time of day suffix
    cleaned = re.sub(r"\s*[\-–—]\s*(?:DAY|NIGHT|DAWN|DUSK|SUNSET|SUNRISE|MORNING|EVENING|CONTINUOUS|LATER|SAME)\s*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()
