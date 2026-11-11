"""Create the first private, outcome-neutral state for the decision pilot."""

import json
from pathlib import Path

from observability.assets import local_output

from .inventory import scan_optitrack
from .manifest import build_manifest
from .state import new_state, update_gate
from .validate_inputs import validate_inputs


def bootstrap(optitrack_root, output_dir=Path("local/pilot")):
    """Census the admitted OptiTrack root and initialize evidence gates.

    This does not pair takes, select a study, or make a scientific claim.
    """
    output_dir = local_output(Path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = local_output(output_dir / "optitrack-census.json")
    state_path = local_output(output_dir / "state.json")

    inventory = scan_optitrack(optitrack_root)
    manifest = build_manifest(optitrack_root, output_dir)
    input_validation = validate_inputs(manifest["private"], output_dir)
    state = new_state()
    update_gate(
        state,
        "scope",
        "complete",
        evidence=["docs/LOCAL_RESOURCES.md", "AGENTS.md"],
        notes=[
            "Only admitted OptiTrack and SAM-derived assets are in scope.",
            "The census is descriptive and does not select a study outcome.",
        ],
    )
    update_gate(
        state,
        "manifest",
        "in_progress" if inventory["complete"] else "blocked",
        evidence=[
            "local/pilot/optitrack-census.json",
            "local/pilot/manifest-summary.json",
            "local/pilot/input-validation-summary.json",
        ],
        notes=[
            (
                "Session-level census complete; take-level pairing remains unverified."
                if inventory["complete"]
                else "Census errors must be resolved before take-level pairing."
            )
        ],
    )

    inventory_path.write_text(json.dumps(inventory, indent=2) + "\n")
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    return {
        "inventory": inventory,
        "manifest": manifest,
        "input_validation": input_validation,
        "state": state,
        "inventory_path": inventory_path,
        "state_path": state_path,
    }
