"""Synthesize progressive pilot evidence without promoting frames to participants."""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from observability.assets import local_output


def _finite(rows, key):
    return np.asarray(
        [row[key] for row in rows if row.get(key) is not None], dtype=float
    )


def _descriptive(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return {
        "n": int(len(values)),
        "median": float(np.median(values)),
        "p25": float(np.percentile(values, 25)),
        "p75": float(np.percentile(values, 75)),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
    }


def _cluster_bootstrap_median(rows, iterations=10000, seed=20261109):
    by_session = defaultdict(list)
    for row in rows:
        if row.get("median_error_mm") is not None:
            by_session[row["session_id"]].append(row["median_error_mm"])
    sessions = sorted(by_session)
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(iterations):
        sampled = rng.choice(sessions, size=len(sessions), replace=True)
        values = [value for session in sampled for value in by_session[session]]
        estimates.append(np.median(values))
    return {
        "capture_groups": len(sessions),
        "iterations": iterations,
        "median": float(np.median(estimates)),
        "descriptive_interval_95": [
            float(np.percentile(estimates, 2.5)),
            float(np.percentile(estimates, 97.5)),
        ],
        "not_population_inference": True,
    }


def synthesize_pilot(
    discovery,
    confirmation,
    references,
    sam,
    force,
    output=Path("local/pilot/synthesis.json"),
):
    """Rank candidate studies from replicated pilot evidence and explicit limitations."""
    takes = discovery["per_take"] + confirmation["per_take"]
    trust_gap = _finite(takes, "ray_gap_error_rank_correlation")
    trust_confidence = _finite(takes, "low_confidence_error_rank_correlation")
    gains = _finite(takes, "change_vector_gain")
    directions = _finite(takes, "change_direction_cosine_median")
    candidates = [
        {
            "rank": 1,
            "code": "C+E+F",
            "direction": "reference-aware trust and signal preservation",
            "status": "selected",
            "reason": (
                "Replicated calibrated-view errors, useful but imperfect trust signals, "
                "change-vector distortion, and large reference-definition offsets are all "
                "directly measurable with independent marker wrist endpoints."
            ),
        },
        {
            "rank": 2,
            "code": "A",
            "direction": "identifiability-aware personalisation",
            "status": "secondary mechanism",
            "reason": (
                "SAM pseudo-shape ratios are internally repeatable, but pseudo labels do "
                "not establish anatomical accuracy and the OptiTrack cohort is too small "
                "for population personalisation claims."
            ),
        },
        {
            "rank": 3,
            "code": "B",
            "direction": "minimal single-view calibration",
            "status": "future extension",
            "reason": (
                "Full two-view calibration is validated; independent single-view 3D and "
                "actual home captures are absent from the current empirical endpoint."
            ),
        },
        {
            "rank": 4,
            "code": "D",
            "direction": "longitudinal detectability",
            "status": "future clinical design",
            "reason": "No verified multi-visit longitudinal or neurological cohort is present.",
        },
        {
            "rank": 5,
            "code": "G",
            "direction": "synthetic adequacy",
            "status": "deferred",
            "reason": "The target clinical generator is unavailable for a direct coverage audit.",
        },
        {
            "rank": 6,
            "code": "H",
            "direction": "force-based physical falsification",
            "status": "closed as central",
            "reason": force["decision"],
        },
        {
            "rank": 7,
            "code": "I",
            "direction": "privacy and outcome sufficiency",
            "status": "deferred",
            "reason": "No frozen threat model or patient acceptability evidence is available.",
        },
    ]
    selected = {
        "working_title": (
            "Reference-conditioned transfer validity in few-camera kinematics: when "
            "does a reconstruction preserve anatomical change?"
        ),
        "central_question": (
            "Does a limited-camera measurement preserve the direction and magnitude of "
            "simultaneous anatomical change, and does its accept/repeat/withhold rule "
            "remain valid when the target landmark definition changes?"
        ),
        "primary_endpoint": "marker-wrist 3D error and change-vector transfer",
        "secondary_endpoints": [
            "risk-coverage from detector confidence and multi-view ray disagreement",
            "sensitivity to marker midpoint versus fitted-origin correspondence",
            "internal repeatability of SAM-derived body proportions",
        ],
        "explicit_nonclaims": [
            "No neurological, home-monitoring, clinical, or longitudinal validity claim.",
            "No claim that SAM pseudo-label repeatability establishes anatomical accuracy.",
            "No claim that calibrated two-view triangulation is a deployable monocular method.",
            "No universal attenuation claim; magnitude response differed across pilot sets.",
        ],
    }
    result = {
        "schema": "expansion-decision-pilot-synthesis-v1",
        "selected_study": selected,
        "candidate_ranking": candidates,
        "replication": {
            "discovery": {
                "takes": discovery["takes"],
                "median_error_mm": discovery["median_error_mm"],
                "p90_error_mm": discovery["p90_error_mm"],
                "vector_gain": discovery["change_vector_gain"],
                "direction_cosine": discovery["change_direction_cosine_median"],
            },
            "confirmation": {
                "takes": confirmation["takes"],
                "median_error_mm": confirmation["median_error_mm"],
                "p90_error_mm": confirmation["p90_error_mm"],
                "vector_gain": confirmation["change_vector_gain"],
                "direction_cosine": confirmation["change_direction_cosine_median"],
            },
        },
        "take_level_descriptives": {
            "median_error_mm": _descriptive(_finite(takes, "median_error_mm")),
            "ray_gap_error_rank_correlation": _descriptive(trust_gap),
            "low_confidence_error_rank_correlation": _descriptive(trust_confidence),
            "change_vector_gain": _descriptive(gains),
            "change_direction_cosine": _descriptive(directions),
        },
        "capture_group_bootstrap": _cluster_bootstrap_median(takes),
        "reference_evidence": {
            name: {
                "schema_fraction": row["schema_fraction"],
                "frame_coverage_median": row["take_frame_coverage"]["median"],
                "fitted_disagreement_median_mm": row[
                    "take_median_marker_vs_fitted_disagreement_mm"
                ]["median"],
                "primary_eligible": row["eligible_as_primary_marker_endpoint"],
            }
            for name, row in references["joints"].items()
        },
        "sam_personalisation_evidence": {
            "stable_enough_internally": sam["stable_enough_for_personalisation_pilot"],
            "repeatability": sam["repeatability"],
            "truth_status": "pseudo labels; not independent anatomical validation",
        },
        "claim_register": [
            {
                "claim": "The documented projection convention and nominal alignment pass the frozen pilot gates.",
                "status": "supported in discovery and confirmation",
                "boundary": "Two sampled takes per capture group were not used; one per set was used.",
            },
            {
                "claim": "Calibrated two-view detector triangulation can remain substantially wrong in 3D.",
                "status": "supported against marker wrist midpoints in two non-overlapping sets",
                "boundary": "Six marker-capable capture groups; sport-lab movements only.",
            },
            {
                "claim": "Confidence and ray disagreement provide useful but incomplete risk ordering.",
                "status": "supported as an association, not a calibrated deployment guarantee",
                "boundary": "Nested observations and no home or neurological domain validation.",
            },
            {
                "claim": "Change is distorted, but not uniformly attenuated.",
                "status": "supported; simple magnitude slope did not replicate",
                "boundary": "Short high-motion windows, not clinical change over visits.",
            },
            {
                "claim": "Landmark correspondence is part of the error budget.",
                "status": "supported by marker/fitted and MHR surface-offset audits",
                "boundary": "All compared references remain imperfect constructions or models.",
            },
        ],
    }
    output = local_output(Path(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
