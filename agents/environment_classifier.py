"""
environment_classifier.py — Environment Classification Agent

Classifies the filming environment and identifies the governing jurisdiction,
sub-zones, public/private status, nearby sensitive sites, and noise restrictions.

Uses Google Maps Geocoding API when available for accurate jurisdiction
resolution and nearby sensitive site detection.

Input:  SceneBreakdown, location string
Output: EnvironmentClassification
"""

from __future__ import annotations

from app.schemas import EnvironmentClassification, EnvironmentType, SceneBreakdown
from app.llm import llm_call
from app.geocoder import geocode_location

_SYSTEM = """You are a film location and jurisdiction expert specializing in Los Angeles.

Given a scene setting and filming location, classify the environment.
Output ONLY valid JSON with these exact fields:
{
  "environment_type": "street|park|beach|indoor|rooftop|highway|residential|commercial|government|other",
  "jurisdiction": "governing body for permits (e.g. 'City of Los Angeles — FilmLA')",
  "sub_zone": "specific district or neighborhood",
  "public_or_private": "public|private",
  "nearby_sensitive_sites": ["schools, hospitals, government buildings within 1000 feet"],
  "noise_restrictions": true/false
}

Rules:
- Default to City of Los Angeles / FilmLA jurisdiction unless in a different city.
- Flag residential areas with night shoots for noise restrictions.
- For nearby_sensitive_sites, include realistic locations based on the area."""

# Keyword-to-environment mapping for heuristic fallback
_ENVIRONMENT_KEYWORDS: dict[str, EnvironmentType] = {
    "beach": EnvironmentType.BEACH,
    "park": EnvironmentType.PARK,
    "street": EnvironmentType.STREET,
    "highway": EnvironmentType.HIGHWAY,
    "freeway": EnvironmentType.HIGHWAY,
    "rooftop": EnvironmentType.ROOFTOP,
    "apartment": EnvironmentType.RESIDENTIAL,
    "house": EnvironmentType.RESIDENTIAL,
    "office": EnvironmentType.COMMERCIAL,
    "studio": EnvironmentType.INDOOR,
    "warehouse": EnvironmentType.INDOOR,
    "city hall": EnvironmentType.GOVERNMENT,
    "courthouse": EnvironmentType.GOVERNMENT,
}


def run_environment_classification(
    breakdown: SceneBreakdown,
    location: str,
) -> EnvironmentClassification:
    """
    Classify the filming environment based on the scene breakdown and location.

    Strategy:
    1. Geocode the location (if Google Maps API available) for jurisdiction
       and nearby sensitive sites.
    2. Use LLM for environment classification.
    3. Fall back to heuristics if both are unavailable.
    """
    # --- Step 1: Geocode for real-world data ---
    geo = geocode_location(location) if location else None

    # --- Step 2: Try LLM ---
    geo_context = ""
    if geo:
        geo_context = (
            f"\n\nGeocoding data (verified):\n"
            f"- Coordinates: {geo.latitude}, {geo.longitude}\n"
            f"- City: {geo.city}\n"
            f"- Neighborhood: {geo.neighborhood}\n"
            f"- Jurisdiction: {geo.jurisdiction}\n"
            f"- Nearby sensitive sites: {', '.join(geo.nearby_sensitive_sites) if geo.nearby_sensitive_sites else 'none found within 1000 ft'}"
        )

    prompt = (
        f"Scene setting: {breakdown.setting_description}\n"
        f"Time of day: {breakdown.time_of_day}\n"
        f"Interior/Exterior: {breakdown.interior_exterior}\n"
        f"Filming location: {location}\n"
        f"Props on set: {', '.join(breakdown.props) if breakdown.props else 'none'}\n"
        f"Crowd size: {breakdown.crowd_size_estimate}"
        f"{geo_context}"
    )

    llm_result = llm_call(prompt=prompt, system=_SYSTEM)

    if llm_result:
        env_str = llm_result.get("environment_type", "other")
        try:
            env_type = EnvironmentType(env_str)
        except ValueError:
            env_type = EnvironmentType.OTHER

        # Prefer geocoded data for jurisdiction and sensitive sites
        jurisdiction = llm_result.get("jurisdiction", "City of Los Angeles — FilmLA")
        nearby = llm_result.get("nearby_sensitive_sites", [])
        if geo:
            jurisdiction = geo.jurisdiction or jurisdiction
            if geo.nearby_sensitive_sites:
                nearby = geo.nearby_sensitive_sites

        return EnvironmentClassification(
            environment_type=env_type,
            jurisdiction=jurisdiction,
            sub_zone=llm_result.get("sub_zone", geo.neighborhood if geo else ""),
            public_or_private=llm_result.get("public_or_private", "public"),
            nearby_sensitive_sites=nearby,
            noise_restrictions=llm_result.get("noise_restrictions", False),
        )

    # --- Step 3: Heuristic fallback (enhanced with geocoding) ---
    return _heuristic_classification(breakdown, location, geo)


def _heuristic_classification(
    breakdown: SceneBreakdown,
    location: str,
    geo=None,
) -> EnvironmentClassification:
    """Fallback heuristic classification, enhanced with geocoding data."""
    combined_text = f"{breakdown.setting_description} {location}".lower()

    env_type = EnvironmentType.OTHER
    for keyword, etype in _ENVIRONMENT_KEYWORDS.items():
        if keyword in combined_text:
            env_type = etype
            break

    if breakdown.interior_exterior == "INT":
        env_type = EnvironmentType.INDOOR

    # Jurisdiction — prefer geocoded result
    if geo and geo.jurisdiction:
        jurisdiction = geo.jurisdiction
    else:
        jurisdiction = "City of Los Angeles — FilmLA"
        if "santa monica" in combined_text:
            jurisdiction = "City of Santa Monica — Film Permit Office"
        elif "burbank" in combined_text:
            jurisdiction = "City of Burbank — Media District Film Office"
        elif "culver city" in combined_text:
            jurisdiction = "City of Culver City — Film Office"
        elif "west hollywood" in combined_text:
            jurisdiction = "City of West Hollywood — Film Permit Office"
        elif "long beach" in combined_text:
            jurisdiction = "City of Long Beach — Film Office"
        elif "beverly hills" in combined_text:
            jurisdiction = "City of Beverly Hills — Film Liaison"
        elif "pasadena" in combined_text:
            jurisdiction = "City of Pasadena — Film Office"
        elif "glendale" in combined_text:
            jurisdiction = "City of Glendale — Film Permit Office"

    # Sub-zone — prefer geocoded neighborhood
    sub_zone = geo.neighborhood if geo else ""

    # Public / Private
    public_types = {
        EnvironmentType.STREET, EnvironmentType.PARK,
        EnvironmentType.BEACH, EnvironmentType.HIGHWAY,
    }
    public_or_private = "public" if env_type in public_types else "private"

    # Noise restrictions
    noise_restricted = (
        breakdown.time_of_day in ("NIGHT", "DAWN")
        and env_type in (EnvironmentType.RESIDENTIAL, EnvironmentType.STREET)
    )

    # Nearby sensitive sites — from geocoding
    nearby = geo.nearby_sensitive_sites if geo else []

    return EnvironmentClassification(
        environment_type=env_type,
        jurisdiction=jurisdiction,
        sub_zone=sub_zone,
        public_or_private=public_or_private,
        nearby_sensitive_sites=nearby,
        noise_restrictions=noise_restricted,
    )
