# Post-pilot controls

The original protocol and its hash are retained. After observing the corrected real-data results, two diagnostics were run without selecting a new checkpoint or tuning weights:

1. Repeat the entire real-data matrix with 400 rather than 200 optimization steps (`results/optitrack_400/`).
2. At 400 steps, replace detector observations with exact reference-skeleton pixel projections (`oracle_control.py`, `results/oracle_pixels/`). This uses privileged information to diagnose observation dependence; it does not isolate detector localization from landmark-definition mismatch.

The primary tables remain the 200-step analysis. These controls are exploratory and explicitly post-pilot. The source cache's 2D model had training exposure to some development participants; their rows are not used to claim generalization. The three evaluation participants are reported separately from the four development participants.
