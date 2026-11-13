"""Draw the report figures and write its supplementary aggregate tables.

Inputs are the study analysis, the release tables written by ``study.report`` and the
post hoc movement summary. Outputs contain group-level and split-level aggregates only.
"""

import argparse
import csv
from pathlib import Path

import numpy as np

from observability.assets import local_output

from .design import read_json

INK, SEC, MUTE, GRID, SURF = "#1f1f1d", "#52514e", "#8b8a84", "#e7e6e1", "#ffffff"
TWO, VIEW_A, VIEW_B = "#2a78d6", "#eb6834", "#1baf7a"
RAY, CONF = "#6250d6", "#eda100"
METHODS = ("view_a", "view_b", "two_view")
COLOR = {"view_a": VIEW_A, "view_b": VIEW_B, "two_view": TWO}
LABEL = {"view_a": "One view A", "view_b": "One view B", "two_view": "Two views"}
SPLITS = ("development", "confirmation")
RULES = (
    ("absolute", "ray_gap", "Position · ray gap"),
    ("absolute", "confidence", "Position · confidence"),
    ("change", "ray_gap", "Displacement · ray gap"),
    ("change", "confidence", "Displacement · confidence"),
)
WIDTH = 6.6
# Two-link values from the public baseline aggregates in results/optitrack.
TWO_LINK_RESIDUAL_PX = (17.91, 1.36)
TWO_LINK_MEAN_MM = (78.3, 80.3)
TWO_LINK_PARTICIPANTS_MM = ((78.3, 71.7), (77.8, 92.5), (78.9, 76.8))


def _style(plt, font_dir):
    from matplotlib import font_manager

    family = "DejaVu Sans"
    if font_dir:
        for path in sorted(Path(font_dir).glob("*.ttf")):
            font_manager.fontManager.addfont(str(path))
            family = font_manager.FontProperties(fname=str(path)).get_name()
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 8.6,
            "axes.edgecolor": MUTE,
            "axes.linewidth": 0.6,
            "axes.labelcolor": SEC,
            "axes.titlesize": 9.2,
            "axes.titleweight": 600,
            "axes.titlecolor": INK,
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": SEC,
            "ytick.color": SEC,
            "xtick.major.width": 0.5,
            "ytick.major.width": 0.5,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "text.color": INK,
            "svg.fonttype": "path",
            "svg.hashsalt": "wrist-report",
            "figure.facecolor": SURF,
            "axes.facecolor": SURF,
            "legend.frameon": False,
            "legend.fontsize": 8.2,
        }
    )


def _grid(axis, which="x"):
    axis.grid(axis=which, color=GRID, lw=0.6)
    axis.set_axisbelow(True)


def group_labels(analysis):
    """Replace opaque group keys with D1..Dn and C1..Cn in sorted key order."""
    labels = {}
    for split, prefix in (("development", "D"), ("confirmation", "C")):
        for index, key in enumerate(sorted(analysis[split]["groups"]), 1):
            labels[(split, key)] = f"{prefix}{index}"
    return labels


def _loss(evidence, method, outcome):
    return evidence[f"{method}/{outcome}"]["reference_metrics"]["midpoint"]["loss_mm"]


class Figures:
    def __init__(self, analysis, movement, transfer, output, font_dir=None):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _style(plt, font_dir)
        self.plt = plt
        self.analysis = analysis
        self.movement = movement
        self.transfer = transfer
        self.output = output

    def save(self, figure, name):
        figure.savefig(
            self.output / f"{name}.svg",
            bbox_inches="tight",
            pad_inches=0.04,
            metadata={"Date": None},
        )
        self.plt.close(figure)

    def chain(self):
        from matplotlib.patches import FancyBboxPatch

        figure, axis = self.plt.subplots(figsize=(WIDTH, 2.45))
        axis.set(xlim=(0, 6), ylim=(0, 4.15))
        axis.axis("off")
        stages = (
            "Pixels",
            "Surface\nobservation",
            "Anatomical\nlandmark",
            "Body-model\ngeometry",
            "3D\nkinematics",
            "Interpretable\noutcome",
        )
        for index, stage in enumerate(stages):
            axis.add_patch(
                FancyBboxPatch(
                    (index + 0.09, 3.2),
                    0.82,
                    0.78,
                    boxstyle="round,pad=0,rounding_size=0.06",
                    fc="#f4f3ef",
                    ec=MUTE,
                    lw=0.6,
                )
            )
            axis.text(
                index + 0.5,
                3.59,
                stage,
                ha="center",
                va="center",
                fontsize=8.2,
                weight=600,
                linespacing=1.02,
            )
            if index < 5:
                axis.annotate(
                    "",
                    (index + 1.09, 3.59),
                    (index + 0.91, 3.59),
                    arrowprops=dict(
                        arrowstyle="-|>", color=SEC, lw=0.8, mutation_scale=7
                    ),
                )
        spans = (
            (
                1,
                5,
                "Two-link study",
                "constraints and image fit against 3D wrist error",
                MUTE,
            ),
            (
                1,
                4,
                "Decision pilot",
                "which anatomical references the recordings support",
                MUTE,
            ),
            (
                0,
                5,
                "This study",
                "position, short displacement and accept/withhold decisions, "
                "per wrist definition",
                TWO,
            ),
            (
                0,
                6,
                "Open questions",
                "a known change, a reference with known uncertainty, one named outcome",
                INK,
            ),
        )
        for row, (start, stop, name, text, color) in enumerate(spans):
            y = 2.65 - row * 0.72
            axis.plot(
                [start + 0.09, stop - 0.09],
                [y, y],
                color=color,
                lw=3.2,
                solid_capstyle="round",
            )
            label = axis.text(
                start + 0.09,
                y - 0.13,
                name,
                ha="left",
                va="top",
                fontsize=8.4,
                weight=600,
            )
            figure.canvas.draw()
            box = label.get_window_extent().transformed(axis.transData.inverted())
            axis.text(
                box.x1 + 0.08,
                y - 0.13,
                text,
                ha="left",
                va="top",
                fontsize=8.2,
                color=SEC,
            )
        self.save(figure, "measurement-chain")

    def two_link(self):
        figure, axes = self.plt.subplots(
            1,
            3,
            figsize=(WIDTH, 2.3),
            gridspec_kw=dict(width_ratios=[2.05, 0.95, 1.2], wspace=0.42),
        )
        axis = axes[0]
        depth = np.array([1.9, 3.95])
        axis.plot(depth, 0.1 * depth, color=SEC, lw=1)
        angle = np.linspace(0, 2 * np.pi, 200)
        axis.plot(3 + 0.5 * np.cos(angle), 0.5 * np.sin(angle), color=MUTE, lw=0.8)
        # Roots of 1.01 z^2 - 6 z + 8.75 = 0: both points lie 0.5 m from the root.
        for z, color in ((2.571, TWO), (3.369, VIEW_A)):
            axis.plot([3, z], [0, 0.1 * z], color=color, lw=2)
            axis.plot(z, 0.1 * z, "o", ms=7, color=color, mec=SURF, mew=1)
        axis.plot(3, 0, "s", ms=5, color=INK)
        axis.text(3.0, -0.08, "root", ha="center", va="top", fontsize=8, color=SEC)
        axis.text(3.95, 0.3, "camera ray", fontsize=8, color=SEC, ha="right", va="top")
        axis.text(
            2.55, 0.34, "2.571 m", ha="center", va="bottom", fontsize=8.2, weight=600
        )
        axis.text(
            3.42, 0.41, "3.369 m", ha="center", va="bottom", fontsize=8.2, weight=600
        )
        axis.text(
            3.0,
            -0.6,
            "0.5 m segment, 0 px residual at both",
            ha="center",
            va="top",
            fontsize=7.8,
            color=SEC,
        )
        axis.set(
            xlim=(1.85, 4.05),
            ylim=(-0.76, 0.72),
            aspect="equal",
            xlabel="Depth (m)",
            title="a  Same pixel, same length",
        )
        axis.spines["left"].set_visible(False)
        axis.set_yticks([])
        axis = axes[1]
        start, end = TWO_LINK_RESIDUAL_PX
        axis.plot(
            [0, 1], [start, end], color=TWO, lw=2, marker="o", ms=6, mec=SURF, mew=1
        )
        axis.text(0.08, 18.4, f"{start:.2f}", fontsize=8.4, ha="left", va="bottom")
        axis.text(0.74, 0.8, f"{end:.2f}", fontsize=8.4, ha="right", va="bottom")
        axis.set(
            xlim=(-0.3, 1.3), ylim=(0, 22), ylabel="Image residual (px)", title="b  Fit"
        )
        axis.set_xticks([0, 1], ["Initial", "Refined"])
        _grid(axis, "y")
        axis = axes[2]
        for before, after in TWO_LINK_PARTICIPANTS_MM:
            axis.plot(
                [0, 1],
                [before, after],
                color=MUTE,
                lw=1,
                marker="o",
                ms=3.8,
                mec=SURF,
                mew=0.6,
            )
        before, after = TWO_LINK_MEAN_MM
        axis.plot(
            [0, 1],
            [before, after],
            color=TWO,
            lw=2.2,
            marker="o",
            ms=6.5,
            mec=SURF,
            mew=1,
        )
        axis.text(
            1.08,
            after,
            f"mean\n{after:.1f}",
            fontsize=8.2,
            va="center",
            linespacing=1.0,
        )
        axis.text(1.08, 92.5, "92.5", fontsize=8.2, va="center", color=SEC)
        axis.text(1.08, 71.0, "71.7", fontsize=8.2, va="center", color=SEC)
        axis.set(
            xlim=(-0.3, 1.62),
            ylim=(60, 100),
            ylabel="Wrist error (mm)",
            title="c  Accuracy",
        )
        axis.set_xticks([0, 1], ["Initial", "Refined"])
        _grid(axis, "y")
        self.save(figure, "two-link")

    def setup(self):
        from matplotlib.lines import Line2D
        from matplotlib.patches import Circle

        held_out = self.analysis["confirmation"]["main"]
        transfer = held_out["two_view/absolute"]["scores"]["ray_gap"][
            "reference_transfer"
        ]
        fitted = transfer["fitted"]["reference_separation_mm"]["median"]
        marker = transfer["radial"]["reference_separation_mm"]["median"]
        two_view = _loss(held_out, "two_view", "absolute")["median"]
        one_view = sorted(_loss(held_out, m, "absolute")["median"] for m in METHODS[:2])
        figure, axes = self.plt.subplots(
            1,
            2,
            figsize=(WIDTH, 2.75),
            gridspec_kw=dict(width_ratios=[1, 1.15], wspace=0.08),
        )
        axis = axes[0]
        axis.set(xlim=(-1.75, 1.75), ylim=(-2.05, 1.72), aspect="equal")
        axis.axis("off")
        axis.text(
            -1.75,
            1.72,
            "a  Capture layout (schematic)",
            fontsize=9.2,
            weight=600,
            va="top",
        )
        axis.add_patch(Circle((0, 0), 0.5, fc="#f4f3ef", ec=MUTE, lw=0.6))
        axis.text(
            0,
            0.2,
            "capture\nvolume",
            ha="center",
            va="center",
            fontsize=7.8,
            color=SEC,
            linespacing=1.0,
        )
        for angle in np.deg2rad(np.arange(8) * 45 + 22.5):
            axis.plot(
                1.18 * np.cos(angle),
                1.18 * np.sin(angle),
                marker=(3, 0, np.rad2deg(angle) + 90),
                ms=7,
                color=MUTE,
            )
        for angle in np.deg2rad([-130, -50]):
            x, y = 1.42 * np.cos(angle), 1.42 * np.sin(angle)
            axis.plot([x, 0], [y, 0], color=TWO, lw=0.9)
            axis.plot(x, y, "s", ms=7.5, color=TWO, mec=SURF, mew=1)
        arc = np.deg2rad(np.linspace(-130, -50, 40))
        axis.plot(0.72 * np.cos(arc), 0.72 * np.sin(arc), color=TWO, lw=0.9)
        axis.text(0, -0.86, "76–86°", ha="center", va="top", fontsize=8.4, weight=600)
        axis.text(0, -1.42, "4.0–4.8 m apart", ha="center", va="top", fontsize=8.2)
        axis.legend(
            handles=[
                Line2D(
                    [],
                    [],
                    marker="s",
                    ms=6.5,
                    lw=0,
                    color=TWO,
                    label="2 calibrated RGB, 1920 × 1080",
                ),
                Line2D(
                    [],
                    [],
                    marker="^",
                    ms=6.5,
                    lw=0,
                    color=MUTE,
                    label="8 infrared, marker tracking",
                ),
            ],
            loc="lower center",
            bbox_to_anchor=(0.5, -0.03),
            ncol=2,
            handletextpad=0.1,
            columnspacing=0.8,
            fontsize=7.6,
        )
        axis = axes[1]
        limit = 118
        axis.set(
            xlim=(-limit, limit * 1.5),
            ylim=(-limit * 0.98, limit * 1.02),
            aspect="equal",
        )
        axis.axis("off")
        axis.text(
            -limit,
            limit * 1.02,
            "b  What “the wrist” can mean (median distances)",
            fontsize=9.2,
            weight=600,
            va="top",
        )
        for radius, color, width in (
            (fitted, SEC, 0.7),
            (marker, SEC, 0.7),
            (two_view, TWO, 1.2),
            (100, MUTE, 0.7),
        ):
            axis.add_patch(Circle((0, 0), radius, fc="none", ec=color, lw=width))
        backing = dict(fc=SURF, ec="none", pad=0.8)
        axis.plot(0, 0, "o", ms=5.5, color=INK, zorder=4)
        axis.text(
            0,
            -8,
            "midpoint",
            ha="center",
            va="top",
            fontsize=7.6,
            bbox=backing,
            zorder=3,
        )
        for x, name in ((-marker, "radial"), (marker, "ulnar")):
            axis.plot(x, 0, "o", ms=6, color=SURF, mec=INK, mew=1.1, zorder=4)
            axis.text(x, 8, name, ha="center", fontsize=7.6, bbox=backing, zorder=3)
        axis.plot(0, fitted, "D", ms=5.2, color=INK, zorder=4)
        axis.text(
            0,
            30,
            "fitted origin",
            ha="center",
            va="bottom",
            fontsize=7.6,
            bbox=backing,
            zorder=3,
        )
        rows = (
            ("Fitted hand origin", f"{fitted:.1f} mm", INK),
            ("Radial or ulnar marker", f"{marker:.1f} mm", INK),
            ("Two-view estimate", f"{two_view:.1f} mm", TWO),
            ("Position tolerance", "100 mm", SEC),
            ("Fixed-depth estimate", f"{one_view[0]:.0f}–{one_view[1]:.0f} mm", SEC),
        )
        for row, (name, value, color) in enumerate(rows):
            y = 58 - row * 25
            axis.text(112, y, name, fontsize=8, color=color, va="center")
            axis.text(
                112, y - 11, value, fontsize=8.4, weight=600, color=color, va="center"
            )
        self.save(figure, "setup-and-targets")

    def errors(self):
        from matplotlib.lines import Line2D

        figure, axes = self.plt.subplots(
            1, 2, figsize=(WIDTH, 2.3), gridspec_kw=dict(wspace=0.12), sharey=True
        )
        panels = (
            (axes[0], "absolute", "a  Wrist position", 660),
            (axes[1], "change", "b  Short displacement", 66),
        )
        for axis, outcome, title, limit in panels:
            for row, method in enumerate(METHODS):
                y = 2 - row
                for offset, split, filled in (
                    (0.16, "development", False),
                    (-0.16, "confirmation", True),
                ):
                    evidence = self.analysis[split]
                    values = [
                        _loss(evidence["groups"][key], method, outcome)["median"]
                        for key in sorted(evidence["groups"])
                    ]
                    pooled = _loss(evidence["main"], method, outcome)["median"]
                    axis.scatter(
                        values,
                        [y + offset] * len(values),
                        s=24,
                        facecolor=COLOR[method] if filled else SURF,
                        edgecolor=COLOR[method],
                        lw=1,
                        zorder=3,
                    )
                    axis.plot(
                        [pooled, pooled],
                        [y + offset - 0.12, y + offset + 0.12],
                        color=INK,
                        lw=1.8,
                        zorder=4,
                        solid_capstyle="butt",
                    )
                    if filled:
                        axis.text(
                            pooled,
                            y + offset - 0.17,
                            f"{pooled:.1f}",
                            ha="center",
                            va="top",
                            fontsize=8.2,
                            weight=600,
                        )
            axis.set(
                xlim=(0, limit),
                ylim=(-0.62, 2.48),
                title=title,
                xlabel="Median error (mm)",
            )
            axis.set_yticks([2, 1, 0], [LABEL[m] for m in METHODS])
            _grid(axis)
        figure.legend(
            handles=[
                Line2D(
                    [],
                    [],
                    marker="o",
                    ms=5.2,
                    lw=0,
                    mfc=SEC,
                    mec=SEC,
                    label="Held-out group",
                ),
                Line2D(
                    [],
                    [],
                    marker="o",
                    ms=5.2,
                    lw=0,
                    mfc=SURF,
                    mec=SEC,
                    label="Development group",
                ),
                Line2D(
                    [],
                    [],
                    marker="|",
                    ms=8,
                    mew=1.8,
                    lw=0,
                    color=INK,
                    label="Pooled median",
                ),
            ],
            loc="upper center",
            bbox_to_anchor=(0.5, 1.08),
            ncol=3,
            handletextpad=0.2,
            columnspacing=1.4,
            fontsize=8,
        )
        self.save(figure, "position-and-displacement")

    def movement_bins(self):
        from matplotlib.lines import Line2D

        figure, axes = self.plt.subplots(
            1, 2, figsize=(WIDTH, 2.8), sharey=True, gridspec_kw=dict(wspace=0.08)
        )
        labels = ("<10", "10–25", "25–50", "50–100", "100–200", "200+")
        x = np.arange(len(labels))
        for axis, split, title in (
            (axes[0], "development", "a  Development groups"),
            (axes[1], "confirmation", "b  Held-out groups"),
        ):
            methods = self.movement[split]["methods"]
            bins = methods["two_view"]["fine"]
            axis.plot(
                x,
                [row["median_true_mm"] for row in bins],
                color=SEC,
                lw=1.6,
                marker="s",
                ms=4.2,
                mec=SURF,
                mew=0.7,
                zorder=2,
            )
            for method in METHODS:
                emphasis = method == "two_view"
                axis.plot(
                    x,
                    [row["median_error_mm"] for row in methods[method]["fine"]],
                    color=COLOR[method],
                    lw=2.2 if emphasis else 1.5,
                    marker="o",
                    ms=5.2 if emphasis else 4.2,
                    mec=SURF,
                    mew=0.8,
                    zorder=4 if emphasis else 3,
                )
            axis.set_yscale("log")
            axis.set(ylim=(1.05, 420), title=title, xlim=(-0.3, 5.3))
            axis.set_xticks(
                x,
                [f"{label}\n{row['pairs']}" for label, row in zip(labels, bins)],
                fontsize=7.8,
                linespacing=1.15,
            )
            axis.set_xlabel("True displacement (mm), with pairs per bin")
            ticks = [2, 5, 10, 20, 50, 100, 200]
            axis.set_yticks(ticks, [str(t) for t in ticks])
            axis.minorticks_off()
            _grid(axis, "y")
        axes[0].set_ylabel("Median displacement error (mm)")
        handles = [
            Line2D(
                [],
                [],
                color=COLOR[m],
                lw=2.2 if m == "two_view" else 1.5,
                marker="o",
                ms=5 if m == "two_view" else 4.2,
                mec=SURF,
                label=LABEL[m],
            )
            for m in ("two_view", "view_a", "view_b")
        ]
        handles.append(
            Line2D(
                [],
                [],
                color=SEC,
                lw=1.6,
                marker="s",
                ms=4.2,
                mec=SURF,
                label="Zero-movement baseline",
            )
        )
        figure.legend(
            handles=handles,
            loc="upper center",
            bbox_to_anchor=(0.5, 1.05),
            ncol=4,
            handletextpad=0.4,
            columnspacing=1.4,
            fontsize=8,
        )
        self.save(figure, "displacement-by-movement")

    def risk(self):
        from matplotlib.lines import Line2D

        figure, axes = self.plt.subplots(
            1, 2, figsize=(WIDTH, 2.45), gridspec_kw=dict(wspace=0.2)
        )
        scores = {"ray_gap": RAY, "confidence": CONF}
        held_out = self.analysis["confirmation"]["main"]
        for axis, outcome, title in (
            (axes[0], "absolute", "a  Position"),
            (axes[1], "change", "b  Displacement"),
        ):
            for name, color in scores.items():
                rank = held_out[f"two_view/{outcome}"]["scores"][name]["ranking"]
                coverage = np.asarray(rank["curve"]["scheduled_coverage"])
                risk = np.asarray(rank["curve"]["risk_mm"])
                index = np.searchsorted(
                    coverage, np.arange(0.05, 1.0001, 0.05), side="right"
                )
                index = np.unique(index - 1)
                index = index[index >= 0]
                axis.plot(
                    100 * coverage[index],
                    risk[index],
                    color=color,
                    lw=2,
                    marker="o",
                    ms=3.6,
                    mec=SURF,
                    mew=0.5,
                )
            mean = rank["mean_loss"]
            axis.axhline(mean, color=SEC, lw=0.9)
            axis.text(
                99,
                mean * 1.03,
                f"mean of all scored, {mean:.0f} mm",
                fontsize=7.8,
                color=SEC,
                va="bottom",
                ha="right",
            )
            axis.set(
                xlim=(0, 100),
                ylim=(0, mean * 1.5),
                title=title,
                xlabel="Scheduled estimates retained (%)",
            )
            _grid(axis, "y")
        axes[0].set_ylabel("Mean retained error (mm)")
        axes[1].legend(
            handles=[
                Line2D(
                    [],
                    [],
                    color=RAY,
                    lw=2,
                    marker="o",
                    ms=3.6,
                    mec=SURF,
                    label="Ray gap",
                ),
                Line2D(
                    [],
                    [],
                    color=CONF,
                    lw=2,
                    marker="o",
                    ms=3.6,
                    mec=SURF,
                    label="Detector confidence",
                ),
            ],
            loc="lower right",
            handletextpad=0.4,
            labelspacing=0.2,
        )
        self.save(figure, "risk-coverage")

    def acceptance(self):
        from matplotlib.lines import Line2D

        figure, axes = self.plt.subplots(
            1,
            2,
            figsize=(WIDTH, 2.4),
            gridspec_kw=dict(width_ratios=[1.25, 1], wspace=0.32),
        )
        axis = axes[0]
        held_out = self.analysis["confirmation"]
        for row, (outcome, score, _) in enumerate(RULES):
            y = 3 - row
            color = RAY if score == "ray_gap" else CONF
            values = []
            for key in sorted(held_out["groups"]):
                policy = held_out["groups"][key][f"two_view/{outcome}"]["scores"][
                    score
                ]["primary_policy"]
                if policy.get("accepted_verified"):
                    values.append(100 * policy["accepted_failure_fraction"])
            axis.scatter(
                values,
                [y] * len(values),
                s=30,
                color=color,
                edgecolor=SURF,
                lw=0.7,
                zorder=3,
            )
            pooled = held_out["main"][f"two_view/{outcome}"]["scores"][score][
                "primary_policy"
            ]
            pooled = 100 * pooled["accepted_failure_fraction"]
            axis.plot(
                [pooled, pooled],
                [y - 0.26, y + 0.26],
                color=INK,
                lw=1.8,
                zorder=4,
                solid_capstyle="butt",
            )
        axis.axvline(20, color=INK, lw=0.9, zorder=1)
        axis.text(20.5, 3.52, "20% target", fontsize=7.8, va="center", ha="left")
        axis.set_yticks([3, 2, 1, 0], [rule[2] for rule in RULES])
        axis.set(
            xlim=(0, 36),
            ylim=(-0.5, 3.75),
            xlabel="Accepted estimates over tolerance (%)",
            title="a  Per held-out group",
        )
        _grid(axis)
        figure.legend(
            handles=[
                Line2D(
                    [],
                    [],
                    marker="o",
                    ms=5,
                    lw=0,
                    color=SEC,
                    label="One held-out group",
                ),
                Line2D(
                    [],
                    [],
                    marker="|",
                    ms=8,
                    mew=1.8,
                    lw=0,
                    color=INK,
                    label="Pooled across groups",
                ),
            ],
            loc="upper center",
            bbox_to_anchor=(0.42, 1.07),
            ncol=2,
            handletextpad=0.2,
            columnspacing=1.2,
            fontsize=8,
        )
        axis = axes[1]
        x = np.arange(3)
        for name, color in (("ray_gap", RAY), ("confidence", CONF)):
            rows = self.movement["confirmation"]["policies"][name]["coarse"]
            axis.plot(
                x,
                [100 * row["over_tolerance"] / row["accepted"] for row in rows],
                color=color,
                lw=2,
                marker="o",
                ms=5.5,
                mec=SURF,
                mew=0.8,
            )
        axis.axhline(20, color=INK, lw=0.9, zorder=1)
        axis.text(-0.18, 21, "20% target", fontsize=7.8, va="bottom")
        axis.set_xticks(x, ["<10", "10–50", "50+"])
        axis.set(
            xlim=(-0.25, 2.3),
            ylim=(0, 40),
            xlabel="True displacement (mm)",
            ylabel="Accepted over tolerance (%)",
            title="b  By movement size",
        )
        _grid(axis, "y")
        axis.legend(
            handles=[
                Line2D(
                    [],
                    [],
                    color=RAY,
                    lw=2,
                    marker="o",
                    ms=4.5,
                    mec=SURF,
                    label="Ray gap",
                ),
                Line2D(
                    [],
                    [],
                    color=CONF,
                    lw=2,
                    marker="o",
                    ms=4.5,
                    mec=SURF,
                    label="Confidence",
                ),
            ],
            loc="upper left",
            bbox_to_anchor=(0.0, 1.0),
            handletextpad=0.4,
            labelspacing=0.2,
            fontsize=7.8,
        )
        self.save(figure, "acceptance-failures")

    def references(self):
        from matplotlib.lines import Line2D

        rows = [
            row
            for row in self.transfer
            if row["split"] == "confirmation" and row["method"] == "two_view"
        ]
        marks = {"midpoint": "o", "fitted": "D", "radial": "^", "ulnar": "s"}
        figure, axis = self.plt.subplots(figsize=(WIDTH, 1.95))
        for index, (outcome, score, _) in enumerate(RULES):
            y = 3 - index
            color = RAY if score == "ray_gap" else CONF
            chosen = {
                row["alternative"]: row
                for row in rows
                if row["outcome"] == outcome and row["score"] == score
            }
            accepted = int(chosen["fitted"]["frozen_accepted"])
            values = {
                "midpoint": 100
                * int(chosen["fitted"]["frozen_midpoint_failures"])
                / accepted
            }
            for name in ("fitted", "radial", "ulnar"):
                values[name] = (
                    100 * int(chosen[name]["frozen_alternative_failures"]) / accepted
                )
            axis.plot(
                [min(values.values()), max(values.values())],
                [y, y],
                color=color,
                lw=1.2,
                zorder=2,
            )
            for name, value in values.items():
                axis.plot(
                    value,
                    y,
                    marker=marks[name],
                    ms=6.5,
                    color=color,
                    mec=SURF,
                    mew=0.8,
                    lw=0,
                    zorder=3,
                )
            axis.text(
                max(values.values()) + 0.5,
                y,
                f"n = {accepted:,}",
                fontsize=7.8,
                color=SEC,
                va="center",
            )
        axis.axvline(20, color=INK, lw=0.9, zorder=1)
        axis.text(20.15, 3.5, "20% target", fontsize=7.8, va="center")
        axis.set_yticks([3, 2, 1, 0], [rule[2] for rule in RULES])
        axis.set(
            xlim=(15, 32),
            ylim=(-0.5, 3.75),
            xlabel="Same accepted estimates: share over tolerance (%)",
        )
        _grid(axis)
        axis.legend(
            handles=[
                Line2D([], [], marker=marker, ms=5.5, lw=0, color=SEC, label=label)
                for label, marker in (
                    ("Marker midpoint", "o"),
                    ("Fitted origin", "D"),
                    ("Radial marker", "^"),
                    ("Ulnar marker", "s"),
                )
            ],
            loc="upper center",
            bbox_to_anchor=(0.5, 1.2),
            ncol=4,
            handletextpad=0.1,
            columnspacing=1.2,
            fontsize=7.8,
        )
        self.save(figure, "reference-failures")

    def all(self):
        self.chain()
        self.two_link()
        self.setup()
        self.errors()
        self.movement_bins()
        self.risk()
        self.acceptance()
        self.references()


def _round(value, digits):
    return "" if value is None else round(value, digits)


def _upper(value):
    return "" if value is None else value


def table_rows(analysis, movement):
    """Return the supplementary tables as {file stem: (header, rows)}."""
    tables = {}
    rows = []
    for split in SPLITS:
        for method in METHODS:
            for row in movement[split]["methods"][method]["fine"]:
                rows.append(
                    [
                        split,
                        method,
                        row["lower_mm"],
                        _upper(row["upper_mm"]),
                        row["pairs"],
                        _round(row["median_true_mm"], 2),
                        _round(row["median_estimated_mm"], 2),
                        _round(row["median_error_mm"], 2),
                        _round(row["p90_error_mm"], 2),
                        _round(row["median_error_over_true"], 3),
                        _round(row["median_cosine"], 3),
                    ]
                )
    tables["displacement-by-movement"] = (
        [
            "split",
            "method",
            "true_displacement_lower_mm",
            "true_displacement_upper_mm",
            "pairs",
            "median_true_displacement_mm",
            "median_estimated_displacement_mm",
            "median_error_mm",
            "p90_error_mm",
            "median_error_over_true",
            "median_cosine",
        ],
        rows,
    )
    rows = []
    for split in SPLITS:
        summary = movement[split]
        zero = summary["zero_movement"]
        rows.append(
            [
                split,
                "zero_movement",
                "",
                "",
                summary["pairs"],
                _round(zero["median_error_mm"], 2),
                zero["over_tolerance"],
                "",
            ]
        )
        for method in METHODS:
            item = summary["methods"][method]
            rows.append(
                [
                    split,
                    method,
                    "",
                    "",
                    summary["pairs"],
                    _round(item["median_error_mm"], 2),
                    item["over_tolerance"],
                    _round(item["beats_zero"], 3),
                ]
            )
            for row in item["coarse"]:
                rows.append(
                    [
                        split,
                        method,
                        row["lower_mm"],
                        _upper(row["upper_mm"]),
                        row["pairs"],
                        _round(row["median_error_mm"], 2),
                        row["over_tolerance"],
                        _round(row["beats_zero"], 3),
                    ]
                )
        for row in summary["methods"]["two_view"]["coarse"]:
            rows.append(
                [
                    split,
                    "zero_movement",
                    row["lower_mm"],
                    _upper(row["upper_mm"]),
                    row["pairs"],
                    _round(row["median_true_mm"], 2),
                    row["zero_over_tolerance"],
                    "",
                ]
            )
    tables["zero-movement-baseline"] = (
        [
            "split",
            "estimator",
            "true_displacement_lower_mm",
            "true_displacement_upper_mm",
            "pairs",
            "median_error_mm",
            "over_50mm",
            "fraction_beating_zero",
        ],
        rows,
    )
    rows = []
    for split in SPLITS:
        for name in ("ray_gap", "confidence"):
            for row in movement[split]["policies"][name]["coarse"]:
                rows.append(
                    [
                        split,
                        name,
                        row["lower_mm"],
                        _upper(row["upper_mm"]),
                        row["accepted"],
                        row["over_tolerance"],
                        round(row["over_tolerance"] / row["accepted"], 4),
                    ]
                )
    tables["acceptance-by-movement"] = (
        [
            "split",
            "score",
            "true_displacement_lower_mm",
            "true_displacement_upper_mm",
            "accepted",
            "over_50mm",
            "fraction_over_50mm",
        ],
        rows,
    )
    rows = []
    for split in SPLITS:
        for method in METHODS:
            item = movement[split]["methods"][method]
            rows.append(
                [
                    split,
                    method,
                    item["pairs"],
                    _round(item["median_shared_offset_mm"], 2),
                    _round(item["median_offset_change_mm"], 2),
                    _round(item["shared_share_of_squared_error"], 4),
                    _round(item["rank_correlation_position_change"], 3),
                    _round(item["single_detection_median_mm"], 2),
                    _round(item["multiple_detection_median_mm"], 2),
                ]
            )
    tables["error-structure"] = (
        [
            "split",
            "method",
            "pairs",
            "median_shared_offset_mm",
            "median_offset_change_mm",
            "share_of_squared_position_error_common_to_endpoints",
            "spearman_position_vs_displacement_error",
            "median_error_single_detection_mm",
            "median_error_multiple_detections_mm",
        ],
        rows,
    )
    rows = []
    for split in SPLITS:
        image = movement[split]["image"]
        rows.append(
            [
                split,
                _round(image["median_pixel_distance"], 2),
                _round(image["p90_pixel_distance"], 2),
                _round(image["median_pixel_change_error"], 2),
                _round(image["p90_pixel_change_error"], 2),
                _round(image["median_true_pixel_change"], 2),
                image["separated"],
                _round(image["nearer_opposite_fraction"], 4),
                _round(image["far_fraction"], 4),
                image["flagged_pairs"],
                _round(image["flagged_median_error_mm"], 2),
                image["unflagged_pairs"],
                _round(image["unflagged_median_error_mm"], 2),
                _round(image["share_of_tail_flagged"], 4),
            ]
        )
    tables["image-observations"] = (
        [
            "split",
            "median_pixel_distance_to_projected_midpoint",
            "p90_pixel_distance",
            "median_pixel_change_error",
            "p90_pixel_change_error",
            "median_reference_pixel_change",
            "wrists_separated_over_60px",
            "closer_to_opposite_wrist_fraction",
            "over_150px_from_both_wrists_fraction",
            "pairs_with_flagged_view",
            "flagged_median_error_mm",
            "unflagged_pairs",
            "unflagged_median_error_mm",
            "share_of_errors_over_50mm_flagged",
        ],
        rows,
    )
    labels = group_labels(analysis)
    rows = []
    for split in SPLITS:
        groups = analysis[split]["groups"]
        for key in sorted(groups):
            for method in METHODS:
                for outcome in ("absolute", "change"):
                    loss = _loss(groups[key], method, outcome)
                    rows.append(
                        [
                            labels[(split, key)],
                            split,
                            method,
                            outcome,
                            loss["n"],
                            round(loss["median"], 2),
                            round(loss["p90"], 2),
                        ]
                    )
    tables["group-summary"] = (
        [
            "group",
            "split",
            "method",
            "outcome",
            "scored",
            "median_error_mm",
            "p90_error_mm",
        ],
        rows,
    )
    return tables


def write_tables(tables, output):
    for stem, (header, rows) in tables.items():
        with (output / f"{stem}.csv").open("w", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)


def run(analysis_dir, movement_dir, release_dir, output, font_dir=None):
    output = local_output(Path(output))
    figures = output / "figures"
    tables = output / "tables"
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    analysis = {split: read_json(analysis_dir / f"{split}.json") for split in SPLITS}
    movement = {split: read_json(movement_dir / f"{split}.json") for split in SPLITS}
    with (release_dir / "reference-transfer.csv").open() as stream:
        transfer = list(csv.DictReader(stream))
    write_tables(table_rows(analysis, movement), tables)
    Figures(analysis, movement, transfer, figures, font_dir).all()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, default=Path("local/study/analysis"))
    parser.add_argument("--movement", type=Path, default=Path("local/study/movement"))
    parser.add_argument("--release", type=Path, default=Path("local/study/release"))
    parser.add_argument("--output", type=Path, default=Path("local/study/publication"))
    parser.add_argument(
        "--font-dir", type=Path, help="Optional directory of .ttf files for the figures"
    )
    args = parser.parse_args(argv)
    run(args.analysis, args.movement, args.release, args.output, args.font_dir)


if __name__ == "__main__":
    main()
