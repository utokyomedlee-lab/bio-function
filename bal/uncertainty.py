from __future__ import annotations
from dataclasses import replace
import math
import random
from typing import Mapping, Sequence

from .multicompartment import BALMultiParameters, simulate


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot compute quantile of an empty sample.")
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    weight = position - lo
    return ordered[lo] * (1 - weight) + ordered[hi] * weight


def monte_carlo(
    base: BALMultiParameters,
    ranges: Mapping[str, Sequence[float]],
    samples: int = 100,
    duration: float = 30.0,
    dt: float = 0.05,
    seed: int = 2026,
) -> dict[str, object]:
    """Uniform scenario ensemble over user-specified parameter intervals.

    Ranges are scenario bounds, not inferred biological probability
    distributions. The fixed seed makes runs reproducible.
    """
    if samples < 1:
        raise ValueError("samples must be >= 1.")
    allowed = set(base.__dataclass_fields__)
    parsed: dict[str, tuple[float, float]] = {}
    for name, bounds in ranges.items():
        if name not in allowed:
            raise ValueError(f"Unknown parameter in ranges: {name}")
        if len(bounds) != 2:
            raise ValueError(f"Range for {name} must contain [low, high].")
        low, high = float(bounds[0]), float(bounds[1])
        if not math.isfinite(low) or not math.isfinite(high) or low > high:
            raise ValueError(f"Invalid range for {name}.")
        parsed[name] = (low, high)

    rng = random.Random(seed)
    metrics = {
        "final_plasma": [],
        "final_tissue": [],
        "final_tolerance": [],
        "final_core_index": [],
        "final_tissue_weighted_index": [],
        "max_mass_balance_error": [],
    }
    for _ in range(samples):
        changes = {
            name: rng.uniform(low, high)
            for name, (low, high) in parsed.items()
        }
        params = replace(base, **changes)
        result = simulate(params, duration=duration, dt=dt)
        final = result.final
        metrics["final_plasma"].append(final.plasma)
        metrics["final_tissue"].append(final.tissue)
        metrics["final_tolerance"].append(final.tolerance)
        metrics["final_core_index"].append(final.core_index)
        metrics["final_tissue_weighted_index"].append(final.tissue_weighted_index)
        metrics["max_mass_balance_error"].append(result.max_mass_balance_error)

    summary = {}
    for name, values in metrics.items():
        summary[name] = {
            "mean": sum(values) / len(values),
            "p05": _quantile(values, 0.05),
            "p50": _quantile(values, 0.50),
            "p95": _quantile(values, 0.95),
        }
    return {
        "samples": samples,
        "seed": seed,
        "distribution": "uniform within user-specified scenario bounds",
        "ranges": {k: list(v) for k, v in parsed.items()},
        "summary": summary,
    }
