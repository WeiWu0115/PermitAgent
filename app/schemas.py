"""
schemas.py — Core data structures for the PermitAgent pipeline.

All models use Pydantic for validation and serialization.
Every agent in the system consumes and produces these structures.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EnvironmentType(str, Enum):
    """High-level classification of a filming environment."""
    STREET = "street"
    PARK = "park"
    BEACH = "beach"
    INDOOR = "indoor"
    ROOFTOP = "rooftop"
    HIGHWAY = "highway"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    GOVERNMENT = "government"
    OTHER = "other"


class RiskLevel(str, Enum):
    """Compliance risk severity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Pipeline Input
# ---------------------------------------------------------------------------

class SceneInput(BaseModel):
    """Raw input submitted by the user to start the pipeline."""
    scene_text: str = Field(
        ...,
        description="Free-text description of the scene or script excerpt.",
        json_schema_extra={"example": "EXT. VENICE BEACH - NIGHT. A drone rises over the boardwalk as two actors sprint through the crowd."},
    )
    location: str = Field(
        default="",
        description="Intended filming location (city, address, or landmark).",
        json_schema_extra={"example": "Venice Beach, Los Angeles, CA"},
    )
    notes: str = Field(
        default="",
        description="Additional production notes.",
        json_schema_extra={"example": "Night shoot, estimated 40 extras."},
    )


# ---------------------------------------------------------------------------
# Agent 1 — Scene Breakdown
# ---------------------------------------------------------------------------

class SceneBreakdown(BaseModel):
    """Structured decomposition of a scene into production elements."""
    scene_id: str = Field(
        ...,
        description="Unique identifier for the scene.",
        json_schema_extra={"example": "scene_001"},
    )
    time_of_day: str = Field(
        ...,
        description="When the scene takes place (DAY, NIGHT, DAWN, DUSK).",
        json_schema_extra={"example": "NIGHT"},
    )
    interior_exterior: str = Field(
        ...,
        description="INT or EXT.",
        json_schema_extra={"example": "EXT"},
    )
    setting_description: str = Field(
        ...,
        description="Brief description of the physical setting.",
        json_schema_extra={"example": "Venice Beach boardwalk"},
    )
    characters: list[str] = Field(
        default_factory=list,
        description="Named or described characters present.",
        json_schema_extra={"example": ["Actor A", "Actor B"]},
    )
    props: list[str] = Field(
        default_factory=list,
        description="Notable props mentioned in the scene.",
        json_schema_extra={"example": ["drone", "backpack"]},
    )
    vehicles: list[str] = Field(
        default_factory=list,
        description="Vehicles involved in the scene.",
        json_schema_extra={"example": ["police cruiser"]},
    )
    crowd_size_estimate: int = Field(
        default=0,
        description="Estimated number of extras / background actors.",
        json_schema_extra={"example": 40},
    )
    special_effects: list[str] = Field(
        default_factory=list,
        description="SFX or VFX elements described.",
        json_schema_extra={"example": ["smoke machine"]},
    )
    summary: str = Field(
        default="",
        description="One-sentence summary of the scene.",
    )


# ---------------------------------------------------------------------------
# Agent 2 — Environment Classification
# ---------------------------------------------------------------------------

class EnvironmentClassification(BaseModel):
    """Classification of the filming environment and jurisdiction."""
    environment_type: EnvironmentType = Field(
        ...,
        description="High-level type of the environment.",
        json_schema_extra={"example": "beach"},
    )
    jurisdiction: str = Field(
        ...,
        description="Governing jurisdiction for permits.",
        json_schema_extra={"example": "City of Los Angeles — Dept. of Recreation and Parks"},
    )
    sub_zone: str = Field(
        default="",
        description="Specific sub-zone or district within the jurisdiction.",
        json_schema_extra={"example": "Venice Beach Boardwalk Zone"},
    )
    public_or_private: str = Field(
        ...,
        description="Whether the location is public or private property.",
        json_schema_extra={"example": "public"},
    )
    nearby_sensitive_sites: list[str] = Field(
        default_factory=list,
        description="Schools, hospitals, government buildings within proximity.",
        json_schema_extra={"example": ["Venice High School (0.3 mi)"]},
    )
    noise_restrictions: bool = Field(
        default=False,
        description="Whether noise ordinances apply.",
    )


# ---------------------------------------------------------------------------
# Agent 3 — Reportable Exposure
# ---------------------------------------------------------------------------

class ReportableExposure(BaseModel):
    """A single reportable element detected in the scene."""
    element: str = Field(
        ...,
        description="Name of the reportable element.",
        json_schema_extra={"example": "drone"},
    )
    category: str = Field(
        ...,
        description="Category: equipment, safety, crowd, pyrotechnics, animals, vehicles, weapons.",
        json_schema_extra={"example": "equipment"},
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Assessed risk level.",
        json_schema_extra={"example": "high"},
    )
    description: str = Field(
        default="",
        description="Brief description of why this element is reportable.",
        json_schema_extra={"example": "FAA-regulated UAS operation in public airspace."},
    )
    requires_notification: list[str] = Field(
        default_factory=list,
        description="Agencies or entities that must be notified.",
        json_schema_extra={"example": ["FAA", "LAPD Air Support"]},
    )


class ExposureReport(BaseModel):
    """Aggregated report of all reportable exposures for a scene."""
    scene_id: str
    exposures: list[ReportableExposure] = Field(default_factory=list)
    overall_risk: RiskLevel = Field(default=RiskLevel.LOW)


# ---------------------------------------------------------------------------
# Agent 4 — Rule Match
# ---------------------------------------------------------------------------

class RuleMatch(BaseModel):
    """A single matched rule or requirement."""
    rule_id: str = Field(
        ...,
        description="Identifier for the matched rule.",
        json_schema_extra={"example": "LA-DRONE-001"},
    )
    source: str = Field(
        ...,
        description="Source document or regulation.",
        json_schema_extra={"example": "LAMC Section 44.01"},
    )
    summary: str = Field(
        ...,
        description="Plain-language summary of the rule.",
        json_schema_extra={"example": "All UAS operations require a Film LA drone supplemental permit and FAA Part 107 waiver."},
    )
    applies_to: list[str] = Field(
        default_factory=list,
        description="Which exposures this rule addresses.",
        json_schema_extra={"example": ["drone"]},
    )
    mandatory: bool = Field(
        default=True,
        description="Whether compliance is mandatory (True) or advisory (False).",
    )


class RuleMatchResult(BaseModel):
    """All rules matched for a scene."""
    scene_id: str
    matched_rules: list[RuleMatch] = Field(default_factory=list)
    unmatched_exposures: list[str] = Field(
        default_factory=list,
        description="Exposures for which no rules were found.",
    )


# ---------------------------------------------------------------------------
# Agent 5 — Document Alignment (Compliance Plan)
# ---------------------------------------------------------------------------

class CompliancePlan(BaseModel):
    """Permit-ready compliance plan for a scene."""
    scene_id: str
    permit_description: str = Field(
        ...,
        description="Permit-ready narrative describing the shoot.",
        json_schema_extra={"example": "Night exterior shoot on Venice Beach boardwalk involving drone cinematography and 40 background performers."},
    )
    required_permits: list[str] = Field(
        default_factory=list,
        description="List of permits to obtain.",
        json_schema_extra={"example": ["Film LA Master Permit", "FAA Part 107 Waiver", "Drone Supplemental"]},
    )
    required_notifications: list[str] = Field(
        default_factory=list,
        description="Agencies to notify.",
    )
    insurance_requirements: list[str] = Field(
        default_factory=list,
        description="Insurance policies or endorsements needed.",
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Special conditions or restrictions.",
    )
    estimated_lead_time_days: int = Field(
        default=0,
        description="Estimated number of business days to secure all permits.",
    )


# ---------------------------------------------------------------------------
# Agent 6 — Compliance Simulation
# ---------------------------------------------------------------------------

class SimulationScenario(BaseModel):
    """A single simulated compliance scenario."""
    scenario_name: str = Field(
        ...,
        description="Name of the scenario.",
        json_schema_extra={"example": "Drone permit denied"},
    )
    probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated probability of occurrence.",
    )
    impact: RiskLevel = Field(
        ...,
        description="Impact severity if this scenario occurs.",
    )
    mitigation: str = Field(
        default="",
        description="Recommended mitigation or alternative strategy.",
    )


class ComplianceSimulation(BaseModel):
    """Full compliance simulation result."""
    scene_id: str
    scenarios: list[SimulationScenario] = Field(default_factory=list)
    overall_feasibility: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall feasibility score (1.0 = fully feasible).",
    )
    recommendation: str = Field(
        default="",
        description="Final recommendation summary.",
    )


# ---------------------------------------------------------------------------
# Full Pipeline Output
# ---------------------------------------------------------------------------

class PipelineResult(BaseModel):
    """Complete output of the PermitAgent pipeline."""
    scene_input: SceneInput
    breakdown: SceneBreakdown
    environment: EnvironmentClassification
    exposures: ExposureReport
    rules: RuleMatchResult
    compliance_plan: CompliancePlan
    simulation: ComplianceSimulation


# ---------------------------------------------------------------------------
# Script-Level Input / Output
# ---------------------------------------------------------------------------

class ScriptInput(BaseModel):
    """Full screenplay or multi-scene script input."""
    script_text: str = Field(
        ...,
        description="Full screenplay text containing multiple scenes.",
    )
    default_location: str = Field(
        default="Los Angeles, CA",
        description="Default filming location when not specified per scene.",
    )
    production_notes: str = Field(
        default="",
        description="General production notes applicable to all scenes.",
    )


class ParsedScene(BaseModel):
    """A single scene extracted from a full script."""
    scene_number: int = Field(..., description="Scene number in sequence.")
    slug_line: str = Field(..., description="Scene heading / slug line (e.g., 'EXT. VENICE BEACH - NIGHT').")
    scene_text: str = Field(..., description="Full text of this scene.")
    location_hint: str = Field(default="", description="Location extracted from slug line.")


class ScriptSummary(BaseModel):
    """High-level summary across all scenes in a script."""
    total_scenes: int = Field(default=0)
    total_exposures: int = Field(default=0)
    total_rules_matched: int = Field(default=0)
    unique_permits_required: list[str] = Field(default_factory=list)
    unique_notifications: list[str] = Field(default_factory=list)
    unique_insurance: list[str] = Field(default_factory=list)
    highest_risk: RiskLevel = Field(default=RiskLevel.LOW)
    average_feasibility: float = Field(default=1.0)
    max_lead_time_days: int = Field(default=0)
    high_risk_scenes: list[str] = Field(
        default_factory=list,
        description="Scene IDs with HIGH or CRITICAL risk.",
    )
    overall_recommendation: str = Field(default="")


class ScriptResult(BaseModel):
    """Complete output for a full script analysis."""
    script_input: ScriptInput
    parsed_scenes: list[ParsedScene] = Field(default_factory=list)
    scene_results: list[PipelineResult] = Field(default_factory=list)
    summary: ScriptSummary
