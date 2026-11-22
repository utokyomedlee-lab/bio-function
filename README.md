# BPL — Biological Programming Language

BPL is an experimental domain-specific language and reference interpreter for declaring and simulating biological models. This repository contains the BPL 0.3.0 source release.

## Install

Python 3.11 or newer is required.

```bash
python -m pip install bpl-biosim
```

The package is not published to PyPI yet. Until the first public release, clone this repository and install locally:

```bash
git clone https://github.com/utokyomedlee-lab/bio-function.git
cd bio-function
python -m pip install .
```

## Quick start

```bash
bpl --version
bpl examples --export ./bpl-examples
bpl validate ./bpl-examples/aging_system.bpl
bpl run ./bpl-examples/aging_system.bpl --csv aging.csv
bpl interact validate ./bpl-examples/senescence_immune_lysosome.bpl
bpl interact run ./bpl-examples/senescence_immune_lysosome.bpl --csv interaction.csv
```

## Scope and scientific status

BPL 0.3 provides an ODE model runner and a well-mixed population/reaction-network engine. It is not yet a validated whole-organism simulator. Spatial cell agents, 2D/3D tissue modeling, organ-level physiology, and clinical prediction are not implemented.

All parameters in bundled examples are illustrative software-test values, not measured human data, clinical reference values, or validated biological constants. The aging-index equations are candidate research models that require calibration and validation against independent experimental data.

See [Korean documentation](README_KO.md), [language reference](docs/LANGUAGE_REFERENCE_KO.md), and [public release guide](PUBLIC_RELEASE_GUIDE_KO.md).

MIT License. See [LICENSE](LICENSE).
