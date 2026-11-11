"""Descriptive change, risk and policy metrics for reference-specific validity."""

import numpy as np


def _ranks(values):
    _, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    return (np.cumsum(counts) - (counts + 1) / 2)[inverse]


def rank_correlation(first, second):
    if len(first) < 3 or np.ptp(first) == 0 or np.ptp(second) == 0:
        return None
    return float(np.corrcoef(_ranks(first), _ranks(second))[0, 1])


def distribution(values):
    if not len(values):
        return {"n": 0}
    return {
        "n": len(values),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p90": float(np.percentile(values, 90)),
    }


def change_metrics(reference, estimate, motion_floor):
    reference_size = np.linalg.norm(reference, axis=-1)
    estimate_size = np.linalg.norm(estimate, axis=-1)
    moved = reference_size >= motion_floor
    directional = moved & (estimate_size > 1e-8)
    dot = np.einsum("ij,ij->i", reference, estimate)
    direction = np.clip(
        dot[directional] / (reference_size[directional] * estimate_size[directional]),
        -1,
        1,
    )
    metrics = {
        "moved_reference_n": int(moved.sum()),
        "direction_cosine": distribution(direction),
        "magnitude_bias_mm": distribution(estimate_size - reference_size),
        "magnitude_order_spearman": rank_correlation(reference_size, estimate_size),
        "projection_positive_fraction": (
            float(np.mean(dot[moved] > 0)) if moved.any() else None
        ),
        "vector_gain": (
            float(dot[moved].sum() / np.square(reference_size[moved]).sum())
            if moved.any()
            else None
        ),
        "slope": None,
        "intercept_mm": None,
    }
    if len(reference_size) >= 3 and np.ptp(reference_size) > 1e-8:
        design = np.column_stack((reference_size, np.ones(len(reference_size))))
        slope, intercept = np.linalg.lstsq(design, estimate_size, rcond=None)[0]
        metrics.update(slope=float(slope), intercept_mm=float(intercept))
    return metrics


def risk_curve(loss, score, tolerance, opportunities):
    """Evaluate attainable score thresholds; score ties enter as a block."""
    if not len(loss):
        return {"n": 0, "schedule": opportunities}
    order = np.argsort(score)
    ends = np.r_[np.flatnonzero(np.diff(score[order])), len(order) - 1]
    counts = ends + 1
    risk = np.cumsum(loss[order])[ends] / counts
    failure = np.cumsum(loss[order] > tolerance)[ends] / counts
    coverage = counts / len(loss)
    mean_loss = float(np.mean(loss))
    area = float(np.sum(np.diff(np.r_[0, coverage]) * risk))
    return {
        "n": len(loss),
        "schedule": opportunities,
        "mean_loss": mean_loss,
        "aurc_over_mean": area / mean_loss if mean_loss else None,
        "spearman": rank_correlation(score, loss),
        "curve": {
            "conditional_coverage": coverage.tolist(),
            "scheduled_coverage": (counts / opportunities).tolist(),
            "risk_mm": risk.tolist(),
            "failure_fraction": failure.tolist(),
        },
    }


def fit_policy(
    loss, score, groups, tolerance, max_failure, min_coverage, repeat_quantile
):
    """Choose cutoffs from development only; risk is averaged over accepting groups."""
    eligible_groups = np.unique(groups[np.isfinite(loss)])
    schedule = np.isin(groups, eligible_groups)
    valid = np.isfinite(loss) & np.isfinite(score)
    thresholds = np.unique(score[valid])
    if not len(thresholds):
        return {
            "accept": None,
            "repeat": None,
            "development_coverage": 0.0,
            "development_failure": None,
            "development_eligible_groups": len(eligible_groups),
        }
    counts, failures = [], []
    for group in eligible_groups:
        mask = valid & (groups == group)
        group_score = score[mask]
        order = np.argsort(group_score)
        n = np.searchsorted(group_score[order], thresholds, side="right")
        counts.append(n)
        failures.append(np.r_[0, np.cumsum(loss[mask][order] > tolerance)][n])
    counts = np.asarray(counts)
    failures = np.asarray(failures)
    rates = np.divide(
        failures, counts, out=np.zeros_like(failures, dtype=float), where=counts > 0
    )
    represented = (counts > 0).sum(axis=0)
    risk = rates.sum(axis=0) / represented
    coverage = counts.sum(axis=0) / schedule.sum()
    feasible = np.flatnonzero((coverage >= min_coverage) & (risk <= max_failure))
    accept = int(feasible[-1]) if len(feasible) else None
    return {
        "accept": float(thresholds[accept]) if accept is not None else None,
        "repeat": float(np.quantile(score[valid], repeat_quantile)),
        "development_coverage": float(coverage[accept]) if accept is not None else 0.0,
        "development_failure": float(risk[accept]) if accept is not None else None,
        "development_eligible_groups": len(eligible_groups),
    }


def decisions(score, policy):
    """Return 0 for withhold, 1 for repeat, and 2 for accept."""
    result = np.zeros(len(score), dtype=np.int8)
    valid = np.isfinite(score)
    if policy["repeat"] is not None:
        result[valid & (score <= policy["repeat"])] = 1
    if policy["accept"] is not None:
        result[valid & (score <= policy["accept"])] = 2
    return result


def policy_outcomes(action, loss, tolerance):
    accept = action == 2
    verified = np.isfinite(loss)
    accepted_verified = accept & verified
    failures = int((accepted_verified & (loss > tolerance)).sum())
    n = int(accepted_verified.sum())
    return {
        "scheduled": len(action),
        "accepted": int(accept.sum()),
        "repeat": int((action == 1).sum()),
        "withheld": int((action == 0).sum()),
        "verified": int(verified.sum()),
        "accepted_verified": n,
        "accepted_failure": failures,
        "accepted_failure_fraction": failures / n if n else None,
    }
