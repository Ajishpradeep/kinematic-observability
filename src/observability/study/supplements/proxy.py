"""Test two-view supervision of a confidence policy that uses one view at inference."""

import argparse
from pathlib import Path

import numpy as np

from observability.assets import local_output, sha256

from ..analyze import OUTCOMES, SPLITS, _stack, build_rows, endpoint
from ..design import read_json, write_json
from ..measure import METHODS, measure_split
from ..metrics import decisions, distribution, fit_policy, policy_outcomes


def run(design_path, observations, main_policy, output):
    output = local_output(Path(output))
    design = read_json(design_path)
    design["sha256"] = sha256(design_path)
    config = design["policy"]
    frozen_main = read_json(main_policy)
    if frozen_main["design_sha256"] != design["sha256"]:
        raise ValueError("main policy belongs to a different design")
    development = list(measure_split(design, observations, "development"))
    policies = {}
    for view in METHODS[:2]:
        for outcome in OUTCOMES:
            rows = build_rows(development, view, outcome)
            two_view = endpoint(_stack(development, "xyz")[:, 2], outcome, vector=True)
            proxy_loss = np.linalg.norm(rows["estimate"] - two_view, axis=-1)
            tolerance = config["tolerances_mm"][outcome]
            policies[f"{view}/{outcome}"] = {
                "fit": fit_policy(
                    proxy_loss,
                    rows["score"]["confidence"],
                    rows["group"],
                    tolerance,
                    config["max_accepted_failure"],
                    config["min_coverage"],
                    config["repeat_score_quantile"],
                ),
                "proxy_loss_mm": distribution(proxy_loss[np.isfinite(proxy_loss)]),
                "scheduled": len(proxy_loss),
            }
    policy_path = output / "policy.json"
    manifest = {
        "design_sha256": design["sha256"],
        "main_policy_sha256": sha256(main_policy),
        "source_sha256": sha256(Path(__file__)),
        "policies": policies,
    }
    if policy_path.exists() and read_json(policy_path) != manifest:
        raise ValueError("existing proxy policy differs")
    write_json(policy_path, manifest)
    for split in SPLITS:
        records = (
            development
            if split == "development"
            else list(measure_split(design, observations, split))
        )
        if any(
            row["observation_config"] != frozen_main["observation_config"]
            for row in records
        ):
            raise ValueError("mixed observation provenance")
        results = {}
        for view in METHODS[:2]:
            for outcome in OUTCOMES:
                key = f"{view}/{outcome}"
                rows = build_rows(records, view, outcome)
                tolerance = config["tolerances_mm"][outcome]
                action = decisions(rows["score"]["confidence"], policies[key]["fit"])
                primary = rows["loss"]["midpoint"]
                alternative = rows["loss"]["fitted"]
                paired = np.isfinite(primary) & np.isfinite(alternative)
                results[key] = {
                    "midpoint": policy_outcomes(action, primary, tolerance),
                    "paired_midpoint": policy_outcomes(
                        action[paired], primary[paired], tolerance
                    ),
                    "paired_fitted": policy_outcomes(
                        action[paired], alternative[paired], tolerance
                    ),
                    "groups": {
                        group: {
                            "midpoint": policy_outcomes(
                                action[mask], primary[mask], tolerance
                            ),
                            "paired_midpoint": policy_outcomes(
                                action[mask & paired], primary[mask & paired], tolerance
                            ),
                            "paired_fitted": policy_outcomes(
                                action[mask & paired],
                                alternative[mask & paired],
                                tolerance,
                            ),
                        }
                        for group in np.unique(rows["group"])
                        for mask in (rows["group"] == group,)
                    },
                }
        write_json(output / f"{split}.json", results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=Path("local/study/design.json"))
    parser.add_argument(
        "--observations", type=Path, default=Path("local/study/observations")
    )
    parser.add_argument("--output", type=Path, default=Path("local/study/proxy"))
    parser.add_argument(
        "--main-policy", type=Path, default=Path("local/study/analysis/policy.json")
    )
    args = parser.parse_args()
    run(args.design, args.observations, args.main_policy, args.output)
