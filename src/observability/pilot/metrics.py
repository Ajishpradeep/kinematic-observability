"""Metrics that keep average accuracy separate from change and trustworthiness."""

import numpy as np

_trapezoid = getattr(np, "trapezoid", None) or np.trapz


def _paired(reference, estimate):
    reference = np.asarray(reference, dtype=float).reshape(-1)
    estimate = np.asarray(estimate, dtype=float).reshape(-1)
    if reference.shape != estimate.shape:
        raise ValueError("reference and estimate must have identical shapes")
    valid = np.isfinite(reference) & np.isfinite(estimate)
    if valid.sum() < 3:
        raise ValueError("at least three finite paired values are required")
    return reference[valid], estimate[valid]


def response_curve(reference_delta, estimated_delta):
    """Summarize a known change without treating frames as inference units."""
    reference, estimate = _paired(reference_delta, estimated_delta)
    design = np.column_stack((np.ones(len(reference)), reference))
    intercept, slope = np.linalg.lstsq(design, estimate, rcond=None)[0]
    fitted = intercept + slope * reference
    residual = estimate - fitted
    total = estimate - estimate.mean()
    total_ss = float(np.dot(total, total))
    r2 = 1.0 - float(np.dot(residual, residual)) / total_ss if total_ss else 0.0
    nonzero = reference != 0
    sign = float(np.mean(np.sign(reference[nonzero]) == np.sign(estimate[nonzero])))
    return {
        "n": int(len(reference)),
        "intercept": float(intercept),
        "slope": float(slope),
        "r2": r2,
        "rmse": float(np.sqrt(np.mean((estimate - reference) ** 2))),
        "sign_agreement": sign,
    }


def risk_coverage(error, uncertainty):
    """Return risk as estimates are retained from low to high uncertainty."""
    error = np.asarray(error, dtype=float).reshape(-1)
    uncertainty = np.asarray(uncertainty, dtype=float).reshape(-1)
    if error.shape != uncertainty.shape:
        raise ValueError("error and uncertainty must have identical shapes")
    valid = np.isfinite(error) & np.isfinite(uncertainty) & (error >= 0)
    if not valid.any():
        raise ValueError("at least one finite nonnegative error is required")
    order = np.argsort(uncertainty[valid], kind="stable")
    ordered_error = error[valid][order]
    risk = np.cumsum(ordered_error) / np.arange(1, len(ordered_error) + 1)
    coverage = np.arange(1, len(risk) + 1) / len(risk)
    return {
        "coverage": coverage,
        "risk": risk,
        "aurc": float(_trapezoid(risk, coverage)) if len(risk) > 1 else float(risk[0]),
    }


def observability_spectrum(jacobian, tolerance=None):
    """Describe local sensitivity without declaring calibrated uncertainty."""
    jacobian = np.asarray(jacobian, dtype=float)
    if jacobian.ndim != 2 or not np.isfinite(jacobian).all():
        raise ValueError("jacobian must be a finite matrix")
    singular = np.linalg.svd(jacobian, compute_uv=False)
    threshold = (
        float(tolerance)
        if tolerance is not None
        else np.finfo(float).eps
        * max(jacobian.shape)
        * (singular[0] if len(singular) else 0)
    )
    rank = int(np.sum(singular > threshold))
    condition = (
        float(singular[0] / singular[-1])
        if len(singular) and singular[-1] > 0
        else float("inf")
    )
    return {"singular_values": singular, "rank": rank, "condition": condition}
