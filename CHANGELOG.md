# Changelog

## 0.3.0 — Biological Interaction Engine and PyPI Release Preparation

- Prepared English and Korean PyPI installation instructions and a public-release guide.
- Added `bpl.examples` as an explicit package so bundled models are consistently included in wheels.
- Added an installed-package example-export regression test.
- Strengthened the GitHub Actions release workflow with Python-version test matrix, example validation, release-tag/version checks, distribution builds, and Twine metadata checks before upload.
- Updated command-line help to distinguish source documentation from bundled example resources.
- Added a population/reaction-network interaction engine.
- Added `bpl interact validate` and `bpl interact run` commands.
- Added reaction flux expressions and stoichiometric state updates.
- Added bounded parameter overrides for model calibration and scenario analysis.
- Added the senescent-cell / immune-clearance / lysosomal-degradation example.
- Preserved the BPL 0.2 equation-based simulation commands and file format.
- Clarified that the new example uses illustrative parameters, not measured human-aging data.

## 0.2.0

- Added a TOML-compatible `.bpl` model format.
- Added a safe arithmetic expression evaluator, Euler and RK4 integrators.
- Added multi-level component declarations, CLI validation, simulation, CSV and JSON output.
