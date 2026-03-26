"""
geocoder.py — Google Maps Geocoding and Places integration.

Provides location intelligence for the Environment Classification Agent:
- Address → coordinates (geocoding)
- Coordinates → city/jurisdiction (reverse geocoding)
- Nearby sensitive sites search (schools, hospitals, government buildings)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import googlemaps

from app.config import GOOGLE_MAPS_API_KEY

logger = logging.getLogger(__name__)

_client: Optional[googlemaps.Client] = None

# Sensitive site types to search for (Google Places API types)
_SENSITIVE_PLACE_TYPES = [
    "school",
    "hospital",
    "fire_station",
    "police",
    "courthouse",
    "city_hall",
    "local_government_office",
    "church",
    "synagogue",
    "mosque",
]

# 1000 feet in meters
_BUFFER_RADIUS_METERS = 305


@dataclass
class GeoResult:
    """Result of geocoding and nearby search."""
    latitude: float = 0.0
    longitude: float = 0.0
    formatted_address: str = ""
    city: str = ""
    county: str = ""
    state: str = ""
    neighborhood: str = ""
    nearby_sensitive_sites: list[str] = field(default_factory=list)
    jurisdiction: str = ""


def _get_client() -> Optional[googlemaps.Client]:
    """Get or create the Google Maps client."""
    global _client
    if _client is not None:
        return _client
    if not GOOGLE_MAPS_API_KEY or GOOGLE_MAPS_API_KEY == "your-key-here":
        return None
    try:
        _client = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        return _client
    except Exception as e:
        logger.error("Failed to create Google Maps client: %s", e)
        return None


def geocode_location(address: str) -> Optional[GeoResult]:
    """
    Geocode an address and search for nearby sensitive sites.

    Returns a GeoResult with coordinates, jurisdiction info, and
    nearby sensitive sites. Returns None if geocoding is unavailable.
    """
    client = _get_client()
    if client is None:
        logger.warning("No Google Maps API key — skipping geocoding.")
        return None

    try:
        # --- Step 1: Geocode the address ---
        geocode_results = client.geocode(address)
        if not geocode_results:
            logger.warning("Geocoding returned no results for: %s", address)
            return None

        result = geocode_results[0]
        location = result["geometry"]["location"]
        lat, lng = location["lat"], location["lng"]

        # --- Step 2: Extract address components ---
        geo = GeoResult(
            latitude=lat,
            longitude=lng,
            formatted_address=result.get("formatted_address", ""),
        )

        for component in result.get("address_components", []):
            types = component.get("types", [])
            name = component.get("long_name", "")

            if "locality" in types:
                geo.city = name
            elif "administrative_area_level_2" in types:
                geo.county = name
            elif "administrative_area_level_1" in types:
                geo.state = name
            elif "neighborhood" in types:
                geo.neighborhood = name
            elif "sublocality" in types and not geo.neighborhood:
                geo.neighborhood = name

        # --- Step 3: Determine jurisdiction ---
        geo.jurisdiction = _resolve_jurisdiction(geo.city, geo.county)

        # --- Step 4: Search for nearby sensitive sites ---
        geo.nearby_sensitive_sites = _find_nearby_sensitive_sites(
            client, lat, lng
        )

        return geo

    except googlemaps.exceptions.ApiError as e:
        logger.error("Google Maps API error: %s", e)
        return None
    except Exception as e:
        logger.error("Geocoding error: %s", e)
        return None


def _resolve_jurisdiction(city: str, county: str) -> str:
    """Determine the film permit jurisdiction based on city."""
    city_lower = city.lower()

    # Known LA-area jurisdictions
    jurisdictions = {
        "los angeles": "City of Los Angeles — FilmLA",
        "santa monica": "City of Santa Monica — Film Permit Office",
        "burbank": "City of Burbank — Media District Film Office",
        "culver city": "City of Culver City — Film Office",
        "west hollywood": "City of West Hollywood — Film Permit Office",
        "pasadena": "City of Pasadena — Film Office",
        "long beach": "City of Long Beach — Film Office",
        "glendale": "City of Glendale — Film Permit Office",
        "beverly hills": "City of Beverly Hills — Film Liaison",
        "malibu": "City of Malibu — Planning Dept (Film Permits)",
    }

    for key, jurisdiction in jurisdictions.items():
        if key in city_lower:
            return jurisdiction

    # LA County unincorporated areas
    if "los angeles" in county.lower():
        return "LA County Unincorporated — FilmLA"

    return f"{city} — Contact local film office"


def _find_nearby_sensitive_sites(
    client: googlemaps.Client,
    lat: float,
    lng: float,
) -> list[str]:
    """Search for schools, hospitals, and government buildings within 1000 feet."""
    sites: list[str] = []

    for place_type in _SENSITIVE_PLACE_TYPES:
        try:
            results = client.places_nearby(
                location=(lat, lng),
                radius=_BUFFER_RADIUS_METERS,
                type=place_type,
            )
            for place in results.get("results", []):
                name = place.get("name", "Unknown")
                # Calculate approximate distance in feet
                place_loc = place.get("geometry", {}).get("location", {})
                if place_loc:
                    dist_m = _haversine(lat, lng, place_loc["lat"], place_loc["lng"])
                    dist_ft = int(dist_m * 3.28084)
                    sites.append(f"{name} ({place_type}, {dist_ft} ft)")
                else:
                    sites.append(f"{name} ({place_type})")
        except Exception as e:
            logger.debug("Places search for %s failed: %s", place_type, e)
            continue

    # Deduplicate by name
    seen = set()
    unique = []
    for site in sites:
        name_part = site.split(" (")[0]
        if name_part not in seen:
            seen.add(name_part)
            unique.append(site)

    return unique


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lng points."""
    import math
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
