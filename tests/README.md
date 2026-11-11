# Tests

The tests check geometry, metrics, privacy rules and command behaviour on synthetic inputs.
None needs recordings, model weights or a network connection.

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
```

| File | Tests | What it checks |
|---|---:|---|
| `test_geometry.py` | 5 | Two-link state round trip and segment lengths, the analytic Jacobian, the exact two-depth ambiguity, the refinement objective and the hard bend bound. |
| `test_workflow.py` | 4 | A run records its source hashes and denominators, `prepare` refuses public output paths, invalid run budgets fail early, and every subcommand has help. |
| `test_expansion.py` | 6 | The `audit` and `infer` commands: inventories record no file names, outputs stay under `local/`, only public checkpoints and a clean public Fast SAM checkout are accepted, and native outputs keep their own joint sets. |
| `test_pilot.py` | 15 | Motion-capture CSV parsing with frame gaps, video naming, projection and ray triangulation, private manifests with stable opaque identifiers, name-free inventories, marker-reference provenance, response and risk metrics, and the evidence gates. |
| `test_study.py` | 10 | Wrist-study windows and displacement pairs, the depth-plane and two-ray estimates, the projected-pixel control, signed gain against magnitude, risk and policy rules under a changed reference, the movement analysis and the shared-offset identity, and anonymous group labels. |

CI runs the same suite on Python 3.12 with CPU PyTorch, together with `ruff`, `black`,
`python -m observability verify`, the repository path check over history, a synthetic smoke
run and a regeneration of `results/tables.md` compared against the committed copy.
