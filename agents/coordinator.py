"""
coordinator.py — Agent Coordinator

Orchestrates the execution of individual agents. Provides a single
entry point that the pipeline calls. Handles future concerns like
agent retries, logging, and parallel dispatch.

TODO: Add structured logging for each agent invocation.
TODO: Add retry logic with exponential backoff for LLM-backed agents.
"""

from __future__ import annotations

from agents.scene_breakdown import run_scene_breakdown
from agents.environment_classifier import run_environment_classification
from agents.exposure_detector import run_exposure_detection
from agents.rule_matcher import run_rule_matching
from agents.document_aligner import run_document_alignment
from agents.compliance_simulator import run_compliance_simulation

__all__ = [
    "run_scene_breakdown",
    "run_environment_classification",
    "run_exposure_detection",
    "run_rule_matching",
    "run_document_alignment",
    "run_compliance_simulation",
]
