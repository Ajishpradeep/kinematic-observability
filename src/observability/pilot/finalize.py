"""Close pilot evidence gates and persist the selected research direction."""

import json
from datetime import datetime, timezone
from pathlib import Path

from observability.assets import local_output

from .state import update_gate


def finalize_pilot(state, synthesis, output=Path("local/pilot/state.json")):
    """Complete evaluated gates; completion can record a negative branch decision."""
    update_gate(
        state,
        "manifest",
        "complete",
        evidence=[
            "local/pilot/manifest-summary.json",
            "local/pilot/input-validation-summary.json",
            "local/pilot/source-provenance.json",
        ],
        notes=[
            "344 takes form the direct nominal-alignment stratum; five are documented exclusions.",
            "Capture groups are descriptive clusters, not asserted independent participants.",
        ],
    )
    update_gate(
        state,
        "synchronization",
        "complete",
        evidence=[
            "local/pilot/alignment/score.json",
            "local/pilot/confirmation/score.json",
        ],
        notes=[
            "Frozen timing gates passed in non-overlapping discovery and confirmation takes.",
            "A minority of views preferred larger shifts; zero-shift regret remained below threshold.",
        ],
    )
    update_gate(
        state,
        "projection",
        "complete",
        evidence=[
            "local/pilot/alignment/score.json",
            "local/pilot/confirmation/score.json",
            "tests/test_pilot.py",
        ],
        notes=[
            "The documented Motive convention outperformed alternatives in both sets.",
            "Projection-to-ray oracle round-trip error is below 1e-3 mm.",
        ],
    )
    update_gate(
        state,
        "references",
        "complete",
        evidence=["local/pilot/reference-audit.json"],
        notes=[
            "All 349 body exports parsed; wrist midpoints are the primary direct endpoint.",
            "Surface markers, paired midpoints, and fitted origins remain separate strata.",
        ],
    )
    update_gate(
        state,
        "model_provenance",
        "complete",
        evidence=[
            "local/pilot/alignment/yolo26n/manifest.json",
            "local/pilot/confirmation/yolo26n/manifest.json",
            "local/pilot/sam-repeatability.json",
        ],
        notes=[
            "Stock pinned YOLO26n-pose produced every OptiTrack pilot observation.",
            "SAM evidence uses admitted pseudo rows and is not independent truth.",
        ],
    )
    update_gate(
        state,
        "geometry_identifiability",
        "complete",
        evidence=[
            "local/pilot/sam-repeatability.json",
            "local/pilot/synthesis.json",
        ],
        notes=[
            "SAM-derived proportions are internally repeatable but not independently accurate.",
            "Personalisation is retained as a secondary mechanism, not the central claim.",
        ],
    )
    update_gate(
        state,
        "view_calibration",
        "complete",
        evidence=[
            "local/pilot/input-validation-summary.json",
            "local/pilot/alignment/score.json",
            "local/pilot/confirmation/score.json",
        ],
        notes=[
            "Full calibrated two-view geometry is validated for the pilot stratum.",
            "Minimal single-view calibration is deferred because it lacks an independent endpoint here.",
        ],
    )
    update_gate(
        state,
        "change_preservation",
        "complete",
        evidence=[
            "local/pilot/triangulation.json",
            "local/pilot/confirmation/triangulation.json",
        ],
        notes=[
            "Change-vector distortion replicated; a universal magnitude attenuation slope did not.",
            "The selected estimand is reference-conditioned transfer, not pathology simulation.",
        ],
    )
    update_gate(
        state,
        "force_validation",
        "complete",
        evidence=["local/pilot/force-validation.json"],
        notes=[
            "Clock metadata pass, but unbounded physical requirements close force as a central endpoint."
        ],
    )
    update_gate(
        state,
        "statistics_claims",
        "complete",
        evidence=[
            "local/pilot/synthesis.json",
            "docs/NOVELTY_REVIEW.md",
        ],
        notes=[
            "Frames remain nested; the capture-group bootstrap is descriptive, not population inference.",
            "Closest 2024-2026 novelty collisions are recorded and strong novelty language is prohibited.",
        ],
    )
    state["selected_study"] = synthesis["selected_study"]
    state["claim_register"] = synthesis["claim_register"]
    state["updated_utc"] = datetime.now(timezone.utc).isoformat()
    output = local_output(Path(output))
    output.write_text(json.dumps(state, indent=2) + "\n")
    return state
