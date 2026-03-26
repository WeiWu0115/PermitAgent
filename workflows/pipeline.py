"""
pipeline.py — Main PermitAgent Pipeline

Supports two modes:
1. Single scene:  run_pipeline(SceneInput) → PipelineResult
2. Full script:   run_script_pipeline(ScriptInput) → ScriptResult

Full script mode parses the screenplay into scenes, runs each through
the pipeline, and produces an aggregated compliance summary.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.schemas import (
    PipelineResult,
    RiskLevel,
    SceneInput,
    ScriptInput,
    ScriptResult,
    ScriptSummary,
)
from agents.scene_breakdown import run_scene_breakdown
from agents.environment_classifier import run_environment_classification
from agents.exposure_detector import run_exposure_detection
from agents.rule_matcher import run_rule_matching
from agents.document_aligner import run_document_alignment
from agents.compliance_simulator import run_compliance_simulation
from agents.script_parser import run_script_parser


_RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}


def run_pipeline(scene_input: SceneInput) -> PipelineResult:
    """
    Execute the full PermitAgent pipeline on a single scene.
    """
    # Step 1: Scene Breakdown
    breakdown = run_scene_breakdown(scene_input)

    # Step 2: Parallel — Environment Classification & Exposure Detection
    with ThreadPoolExecutor(max_workers=2) as executor:
        env_future = executor.submit(
            run_environment_classification,
            breakdown,
            scene_input.location,
        )
        exposure_future = executor.submit(
            run_exposure_detection,
            breakdown,
        )
        environment = env_future.result()
        exposures = exposure_future.result()

    # Step 3: Rule Matching
    rules = run_rule_matching(exposures, environment)

    # Step 4: Document Alignment
    compliance_plan = run_document_alignment(
        breakdown, environment, exposures, rules,
    )

    # Step 5: Compliance Simulation
    simulation = run_compliance_simulation(compliance_plan, exposures)

    return PipelineResult(
        scene_input=scene_input,
        breakdown=breakdown,
        environment=environment,
        exposures=exposures,
        rules=rules,
        compliance_plan=compliance_plan,
        simulation=simulation,
    )


def run_script_pipeline(
    script_input: ScriptInput,
    progress_callback=None,
) -> ScriptResult:
    """
    Analyze a full screenplay.

    1. Parse script into individual scenes.
    2. Run each scene through the single-scene pipeline.
    3. Aggregate results into a ScriptSummary.

    Args:
        script_input: Full screenplay text and metadata.
        progress_callback: Optional callable(current, total) for progress updates.
    """
    # Step 1: Parse script into scenes
    parsed_scenes = run_script_parser(script_input)

    # Step 2: Run pipeline for each scene
    scene_results: list[PipelineResult] = []
    total = len(parsed_scenes)

    for i, parsed in enumerate(parsed_scenes):
        # Build SceneInput for this scene
        scene_input = SceneInput(
            scene_text=parsed.scene_text,
            location=parsed.location_hint or script_input.default_location,
            notes=script_input.production_notes,
        )

        result = run_pipeline(scene_input)
        scene_results.append(result)

        if progress_callback:
            progress_callback(i + 1, total)

    # Step 3: Aggregate summary
    summary = _build_summary(scene_results)

    return ScriptResult(
        script_input=script_input,
        parsed_scenes=parsed_scenes,
        scene_results=scene_results,
        summary=summary,
    )


def _build_summary(results: list[PipelineResult]) -> ScriptSummary:
    """Aggregate individual scene results into a script-level summary."""
    if not results:
        return ScriptSummary(total_scenes=0, overall_recommendation="No scenes to analyze.")

    all_permits: set[str] = set()
    all_notifications: set[str] = set()
    all_insurance: set[str] = set()
    total_exposures = 0
    total_rules = 0
    highest_risk = RiskLevel.LOW
    feasibility_scores: list[float] = []
    max_lead_time = 0
    high_risk_scenes: list[str] = []

    for r in results:
        # Permits
        all_permits.update(r.compliance_plan.required_permits)
        all_notifications.update(r.compliance_plan.required_notifications)
        all_insurance.update(r.compliance_plan.insurance_requirements)

        # Exposures
        total_exposures += len(r.exposures.exposures)
        total_rules += len(r.rules.matched_rules)

        # Risk
        scene_risk = r.exposures.overall_risk
        if _RISK_ORDER[scene_risk] > _RISK_ORDER[highest_risk]:
            highest_risk = scene_risk
        if scene_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            high_risk_scenes.append(f"Scene {r.breakdown.scene_id}: {r.breakdown.summary[:60]}")

        # Feasibility
        feasibility_scores.append(r.simulation.overall_feasibility)

        # Lead time
        if r.compliance_plan.estimated_lead_time_days > max_lead_time:
            max_lead_time = r.compliance_plan.estimated_lead_time_days

    avg_feasibility = sum(feasibility_scores) / len(feasibility_scores) if feasibility_scores else 1.0

    # Overall recommendation
    if avg_feasibility >= 0.8 and highest_risk in (RiskLevel.LOW, RiskLevel.MEDIUM):
        recommendation = (
            f"Script is highly feasible. {len(results)} scenes analyzed with an average feasibility of {avg_feasibility:.0%}. "
            f"Proceed with permit applications. Estimated lead time: {max_lead_time} business days."
        )
    elif avg_feasibility >= 0.5:
        recommendation = (
            f"Script is feasible but {len(high_risk_scenes)} scene(s) carry elevated risk. "
            f"Prioritize securing permits for high-risk scenes. Average feasibility: {avg_feasibility:.0%}. "
            f"Estimated lead time: {max_lead_time} business days."
        )
    else:
        recommendation = (
            f"Script has significant compliance challenges across {len(high_risk_scenes)} scene(s). "
            f"Average feasibility: {avg_feasibility:.0%}. Consider revising high-risk scenes or consulting with FilmLA before proceeding."
        )

    return ScriptSummary(
        total_scenes=len(results),
        total_exposures=total_exposures,
        total_rules_matched=total_rules,
        unique_permits_required=sorted(all_permits),
        unique_notifications=sorted(all_notifications),
        unique_insurance=sorted(all_insurance),
        highest_risk=highest_risk,
        average_feasibility=round(avg_feasibility, 3),
        max_lead_time_days=max_lead_time,
        high_risk_scenes=high_risk_scenes,
        overall_recommendation=recommendation,
    )
