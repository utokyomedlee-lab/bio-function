from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

from .multicompartment import BALMultiParameters, simulate
from .uncertainty import monte_carlo


def main() -> None:
    parser = argparse.ArgumentParser(description="BAL v0.3 multi-compartment simulator")
    parser.add_argument("--config", default="examples/bal_multicompartment.json")
    parser.add_argument("--output", default="bal_v03_results.csv")
    parser.add_argument("--uncertainty-output", default="bal_v03_uncertainty.json")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    p = BALMultiParameters(**config["parameters"])
    sim = config.get("simulation", {})
    duration = float(sim.get("duration", 30.0))
    dt = float(sim.get("dt", 0.05))
    result = simulate(p, duration=duration, dt=dt)

    rows = result.rows()
    with Path(args.output).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "version": "0.3.0",
        "parameters": config["parameters"],
        "m_effective": p.m_effective,
        "hepatic_escape_fraction": p.hepatic_escape_fraction,
        "first_threshold_crossing_time": result.first_threshold_crossing_time,
        "max_mass_balance_error": result.max_mass_balance_error,
        "final": rows[-1],
        "csv": args.output,
    }

    if "uncertainty" in config:
        u = config["uncertainty"]
        ensemble = monte_carlo(
            p, ranges=u.get("ranges", {}),
            samples=int(u.get("samples", 100)),
            duration=duration, dt=dt, seed=int(u.get("seed", 2026)),
        )
        Path(args.uncertainty_output).write_text(
            json.dumps(ensemble, indent=2), encoding="utf-8"
        )
        report["uncertainty"] = args.uncertainty_output

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
