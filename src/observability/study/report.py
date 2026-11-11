"""Export disclosure-limited aggregate tables and publication-resolution figures."""

import argparse
import csv
from pathlib import Path

import numpy as np

from observability.assets import local_output

from .design import read_json

METHOD_LABELS = {
    "view_a": "One view A",
    "view_b": "One view B",
    "two_view": "Two views",
}
COLORS = {"confidence": "#255a89", "ray_gap": "#b44d32"}


def export_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def group_summary(values):
    values = np.array([value for value in values if value is not None], dtype=float)
    loo = (
        [np.median(np.delete(values, i)) for i in range(len(values))]
        if len(values) > 1
        else []
    )
    return {
        "groups": len(values),
        "group_median": float(np.median(values)) if len(values) else None,
        "group_minimum": float(values.min()) if len(values) else None,
        "group_maximum": float(values.max()) if len(values) else None,
        "loo_median_minimum": float(min(loo)) if loo else None,
        "loo_median_maximum": float(max(loo)) if loo else None,
    }


def reference_rows(splits):
    for split, evidence in splits.items():
        for key, main in evidence["main"].items():
            method, outcome = key.split("/")
            for reference in ("midpoint", "fitted", "radial", "ulnar"):
                item = main["reference_metrics"][reference]
                loss = item["loss_mm"]
                transfer = item.get("transfer", {})
                direction = transfer.get("direction_cosine", {})
                groups = [
                    group[key]["reference_metrics"][reference]
                    for group in evidence["groups"].values()
                ]
                yield {
                    "split": split,
                    "method": method,
                    "outcome": outcome,
                    "reference": reference,
                    "scheduled": item["scheduled"],
                    "reference_available": item["reference_available"],
                    "estimate_available": item["estimate_available"],
                    "scored": loss["n"],
                    "scored_takes": item["scored_takes"],
                    "median_loss_mm": loss.get("median"),
                    "p90_loss_mm": loss.get("p90"),
                    "failures": item["failures"],
                    "moved_reference": item.get("reference_moved"),
                    "moved_scored": transfer.get("moved_reference_n"),
                    "direction_scored": direction.get("n"),
                    "median_cosine": direction.get("median"),
                    "projection_positive": transfer.get("projection_positive_fraction"),
                    "vector_gain": transfer.get("vector_gain"),
                    "magnitude_slope": transfer.get("slope"),
                    "magnitude_intercept_mm": transfer.get("intercept_mm"),
                    "mean_magnitude_bias_mm": transfer.get("magnitude_bias_mm", {}).get(
                        "mean"
                    ),
                    "magnitude_spearman": transfer.get("magnitude_order_spearman"),
                    **group_summary(
                        [group["loss_mm"].get("median") for group in groups]
                    ),
                }


def risk_rows(splits, policies):
    for split, evidence in splits.items():
        for key, main in evidence["main"].items():
            method, outcome = key.split("/")
            for name, score in main["scores"].items():
                rank = score["ranking"]
                fitted = policies[f"{key}/{name}"]["primary"]["midpoint"]
                group_ratios = [
                    row[key]["scores"][name]["ranking"].get("aurc_over_mean")
                    for row in evidence["groups"].values()
                ]
                group_rates = [
                    row[key]["scores"][name]["primary_policy"][
                        "accepted_failure_fraction"
                    ]
                    for row in evidence["groups"].values()
                ]
                yield {
                    "split": split,
                    "method": method,
                    "outcome": outcome,
                    "score": name,
                    "scored": rank["n"],
                    "spearman": rank.get("spearman"),
                    "aurc_over_mean": rank.get("aurc_over_mean"),
                    "groups_with_aurc_below_mean": sum(
                        x is not None and x < 1 for x in group_ratios
                    ),
                    "accept_cutoff": fitted["accept"],
                    "repeat_cutoff": fitted["repeat"],
                    **score["primary_policy"],
                    "max_group_accepted_failure": max(
                        (x for x in group_rates if x is not None), default=None
                    ),
                    **group_summary(group_ratios),
                }


def transfer_rows(splits):
    for split, evidence in splits.items():
        for key, main in evidence["main"].items():
            method, outcome = key.split("/")
            for name, score in main["scores"].items():
                for alternative, comparison in score["reference_transfer"].items():
                    if not comparison["paired"]:
                        continue
                    frozen_a = comparison["frozen_on_midpoint"]
                    frozen_b = comparison["frozen_on_alternative"]
                    yield {
                        "split": split,
                        "method": method,
                        "outcome": outcome,
                        "score": name,
                        "alternative": alternative,
                        "paired": comparison["paired"],
                        "median_reference_separation_mm": comparison[
                            "reference_separation_mm"
                        ]["median"],
                        "midpoint_median_loss_mm": comparison["loss_midpoint_mm"][
                            "median"
                        ],
                        "alternative_median_loss_mm": comparison["loss_alternative_mm"][
                            "median"
                        ],
                        "label_switches": comparison["label_switches"],
                        "became_failure": comparison["became_failure"],
                        "became_pass": comparison["became_pass"],
                        "matched_fit_policy_switches": comparison[
                            "paired_policy_switches"
                        ],
                        "frozen_accepted": frozen_a["accepted"],
                        "frozen_accepted_label_switches": comparison[
                            "accepted_label_switches"
                        ],
                        "frozen_midpoint_failures": frozen_a["accepted_failure"],
                        "frozen_alternative_failures": frozen_b["accepted_failure"],
                    }


def sensitivity_rows(splits):
    for split, evidence in splits.items():
        for key, variants in evidence["sensitivity"].items():
            method, outcome = key.split("/")
            for variant, values in variants.items():
                if "midpoint" not in values:
                    continue
                main = values["midpoint"]
                transfer = main.get("transfer", {})
                yield {
                    "split": split,
                    "method": method,
                    "outcome": outcome,
                    "sensitivity": variant,
                    "scheduled": main["scheduled"],
                    "reference_available": main["reference_available"],
                    "estimate_available": main["estimate_available"],
                    "scored": main["loss_mm"]["n"],
                    "median_loss_mm": main["loss_mm"].get("median"),
                    "vector_gain": transfer.get("vector_gain"),
                    "median_cosine": transfer.get("direction_cosine", {}).get("median"),
                    "magnitude_slope": transfer.get("slope"),
                    "magnitude_intercept_mm": transfer.get("intercept_mm"),
                    "common_support_n": values.get("primary_on_common_support", {})
                    .get("loss_mm", {})
                    .get("n"),
                    "main_median_on_common_support_mm": values.get(
                        "primary_on_common_support", {}
                    )
                    .get("loss_mm", {})
                    .get("median"),
                    "variant_median_on_common_support_mm": values.get(
                        "sensitivity_on_common_support", {}
                    )
                    .get("loss_mm", {})
                    .get("median"),
                }


def denominator_rows(splits):
    for split, evidence in splits.items():
        totals = evidence["denominators"]
        for key, value in totals.items():
            if isinstance(value, int):
                yield {"split": split, "unit": key, "view_or_side": "", "count": value}
        for view, counts in enumerate(totals["by_view"], start=1):
            for key, value in counts.items():
                yield {
                    "split": split,
                    "unit": key,
                    "view_or_side": view,
                    "count": value,
                }
        for target, counts in totals["reference_schema_takes_by_left_right"].items():
            for side, count in zip(("left", "right"), counts):
                yield {
                    "split": split,
                    "unit": target + "_schema_takes",
                    "view_or_side": side,
                    "count": count,
                }


def proxy_rows(proxy):
    policy = read_json(proxy / "policy.json")["policies"]
    for split in ("development", "confirmation"):
        for key, result in read_json(proxy / f"{split}.json").items():
            method, outcome = key.split("/")
            fitted = policy[key]["fit"]
            for target in ("midpoint", "paired_midpoint", "paired_fitted"):
                group_rates = [
                    group[target]["accepted_failure_fraction"]
                    for group in result["groups"].values()
                ]
                yield {
                    "split": split,
                    "method": method,
                    "outcome": outcome,
                    "reference_support": target,
                    "accept_cutoff": fitted["accept"],
                    "repeat_cutoff": fitted["repeat"],
                    **result[target],
                    "max_group_accepted_failure": max(
                        (x for x in group_rates if x is not None), default=None
                    ),
                }


def geometry_rows(splits):
    for split, evidence in splits.items():
        for key, main in evidence["main"].items():
            method, outcome = key.split("/")
            item = main["reference_metrics"]
            oracle = item["oracle_midpoint_loss_mm"]
            matched = evidence["matched_methods"][outcome][method]["loss_mm"]
            yield {
                "split": split,
                "method": method,
                "outcome": outcome,
                "detector_on_all_method_common_support_n": matched["n"],
                "detector_on_all_method_common_support_median_mm": matched.get(
                    "median"
                ),
                "oracle_paired_n": oracle["n"],
                "oracle_paired_median_mm": oracle.get("median"),
                "detector_paired_with_oracle_median_mm": item[
                    "detector_matched_oracle_loss_mm"
                ].get("median"),
            }


def save(figure, output, name):
    for suffix in ("png", "svg"):
        figure.savefig(
            output / f"{name}.{suffix}",
            dpi=240,
            bbox_inches="tight",
            metadata={"Date": None} if suffix == "svg" else None,
        )


def plot(splits, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "wrist-transfer-v1",
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.3), layout="constrained")
    for column, (split, evidence) in enumerate(splits.items()):
        for row, outcome in enumerate(("absolute", "change")):
            axis = axes[row, column]
            key = f"two_view/{outcome}"
            for name, score in evidence["main"][key]["scores"].items():
                rank = score["ranking"]
                curve = rank["curve"]
                coverage = np.asarray(curve["scheduled_coverage"])
                risk = np.asarray(curve["risk_mm"])
                targets = np.arange(0.05, 1.01, 0.05)
                indices = np.unique(
                    np.searchsorted(coverage, targets, side="right") - 1
                )
                indices = indices[indices >= 0]
                axis.plot(
                    100 * coverage[indices],
                    risk[indices],
                    marker=".",
                    markersize=3,
                    color=COLORS[name],
                    label={"confidence": "Detector confidence", "ray_gap": "Ray gap"}[
                        name
                    ],
                )
                axis.axhline(rank["mean_loss"], color="#6c7275", ls="--", lw=0.8)
            axis.set(
                xlim=(0, 100),
                title=f"{split.title()} · {outcome.title()}",
                ylabel="Mean retained error (mm)",
                xlabel=(
                    "Scheduled wrist positions retained (%)"
                    if outcome == "absolute"
                    else "Scheduled wrist changes retained (%)"
                ),
            )
            axis.grid(axis="y", alpha=0.17)
            if row == 0 and column == 0:
                axis.legend(frameon=False)
    save(fig, output, "risk-coverage")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1), layout="constrained")
    for axis, (split, evidence) in zip(axes, splits.items()):
        x = np.arange(len(METHOD_LABELS))
        for offset, (outcome, marker, color) in enumerate(
            (("absolute", "o", "#255a89"), ("change", "s", "#b44d32"))
        ):
            shift = (offset - 0.5) * 0.18
            groups = evidence["groups"].values()
            for i, method in enumerate(METHOD_LABELS):
                group_values = [
                    group[f"{method}/{outcome}"]["reference_metrics"]["midpoint"][
                        "loss_mm"
                    ].get("median")
                    for group in groups
                ]
                valid = [value for value in group_values if value is not None]
                axis.scatter(
                    np.full(len(valid), i + shift),
                    valid,
                    marker=marker,
                    color=color,
                    alpha=0.65,
                    label=outcome.title() if i == 0 else None,
                )
                axis.scatter(
                    i + shift, np.median(valid), marker="_", s=280, color=color
                )
        axis.set(
            xticks=x,
            xticklabels=list(METHOD_LABELS.values()),
            title=split.title(),
            ylabel="Within-group median wrist error (mm)",
            ylim=(0, None),
        )
        axis.grid(axis="y", alpha=0.17)
    axes[0].legend(frameon=False)
    save(fig, output, "group-errors")
    plt.close(fig)


def plot_reference_failures(evidence, output):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.0), layout="constrained", sharey=True)
    for axis, outcome in zip(axes, ("absolute", "change")):
        scores = evidence["main"][f"two_view/{outcome}"]["scores"]
        labels = ("Midpoint", "Fitted origin", "Radial marker", "Ulnar marker")
        positions = np.arange(len(labels))
        for index, (name, score) in enumerate(scores.items()):
            matched = score["reference_transfer"]
            base = matched["fitted"]["frozen_on_midpoint"]
            values = [base] + [
                matched[ref]["frozen_on_alternative"]
                for ref in ("fitted", "radial", "ulnar")
            ]
            rates = [
                (
                    100 * row["accepted_failure_fraction"]
                    if row["accepted_failure_fraction"] is not None
                    else np.nan
                )
                for row in values
            ]
            legend = "Detector confidence" if name == "confidence" else "Ray gap"
            axis.bar(
                positions + (index - 0.5) * 0.33,
                rates,
                width=0.31,
                color=COLORS[name],
                label=legend,
            )
        axis.axhline(20, color="#6c7275", ls="--", lw=1)
        axis.set(
            xticks=positions, xticklabels=labels, title=outcome.title(), ylim=(0, 35)
        )
        axis.tick_params(axis="x", labelrotation=20)
        axis.grid(axis="y", alpha=0.17)
    axes[0].set_ylabel("Verified accepted estimates above tolerance (%)")
    axes[0].legend(frameon=False, loc="upper left", fontsize=8)
    save(fig, output, "reference-failures")
    plt.close(fig)


def run(analysis, proxy, output):
    output = local_output(Path(output))
    output.mkdir(parents=True, exist_ok=True)
    splits = {
        split: read_json(analysis / f"{split}.json")
        for split in ("development", "confirmation")
    }
    policy = read_json(analysis / "policy.json")
    export_csv(output / "reference-metrics.csv", list(reference_rows(splits)))
    export_csv(
        output / "risk-and-policy.csv", list(risk_rows(splits, policy["policy"]))
    )
    export_csv(output / "reference-transfer.csv", list(transfer_rows(splits)))
    export_csv(output / "sensitivity.csv", list(sensitivity_rows(splits)))
    export_csv(output / "denominators.csv", list(denominator_rows(splits)))
    export_csv(output / "geometry-control.csv", list(geometry_rows(splits)))
    export_csv(output / "proxy-policy.csv", list(proxy_rows(proxy)))
    plot(splits, output)
    plot_reference_failures(splits["confirmation"], output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, default=Path("local/study/analysis"))
    parser.add_argument("--output", type=Path, default=Path("local/study/release"))
    parser.add_argument("--proxy", type=Path, default=Path("local/study/proxy"))
    args = parser.parse_args()
    run(args.analysis, args.proxy, args.output)
