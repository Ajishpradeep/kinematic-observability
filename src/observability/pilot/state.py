"""Machine-readable evidence gates for the expansion decision pilot."""

from datetime import datetime, timezone

GATES = (
    ("scope", ()),
    ("manifest", ("scope",)),
    ("synchronization", ("manifest",)),
    ("projection", ("manifest", "synchronization")),
    ("references", ("manifest",)),
    ("model_provenance", ("scope",)),
    ("geometry_identifiability", ("projection", "references", "model_provenance")),
    ("view_calibration", ("projection", "references", "model_provenance")),
    ("change_preservation", ("references", "view_calibration")),
    ("force_validation", ("synchronization", "projection")),
    ("statistics_claims", ("manifest", "references")),
)


def new_state():
    return {
        "schema": "expansion-decision-pilot-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "selected_study": None,
        "gates": {
            name: {
                "status": "pending",
                "depends_on": list(dependencies),
                "evidence": [],
                "notes": [],
            }
            for name, dependencies in GATES
        },
        "claim_register": [],
    }


def update_gate(state, name, status, evidence=(), notes=()):
    """Update a gate while preventing unsupported completion."""
    allowed = {"pending", "in_progress", "complete", "blocked"}
    if name not in state["gates"]:
        raise KeyError("unknown evidence gate: {}".format(name))
    if status not in allowed:
        raise ValueError("invalid gate status: {}".format(status))
    gate = state["gates"][name]
    merged_evidence = list(dict.fromkeys(gate["evidence"] + list(evidence)))
    if status == "complete":
        incomplete = [
            dependency
            for dependency in gate["depends_on"]
            if state["gates"][dependency]["status"] != "complete"
        ]
        if incomplete:
            raise ValueError(
                "cannot complete {} before {}".format(name, ", ".join(incomplete))
            )
        if not merged_evidence:
            raise ValueError("a completed gate must cite evidence")
    gate["status"] = status
    gate["evidence"] = merged_evidence
    gate["notes"] = list(dict.fromkeys(gate["notes"] + list(notes)))
    return state
