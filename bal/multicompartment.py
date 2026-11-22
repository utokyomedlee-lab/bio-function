from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import math

from .core import core_bioavailability, threshold_condition


@dataclass(frozen=True)
class BALMultiParameters:
    """Dimensionless/amount-based multi-compartment model parameters.

    Amount compartments: depot, gut, liver, plasma, tissue.
    Rates use inverse model-time units. No clinical units are implied.
    """
    initial_dose: float = 100.0
    a: float = 0.8
    alpha: float = 2.0
    beta: float = 1.0
    b0: float = 0.5
    gamma: float = 0.03
    tolerance_recovery: float = 0.02

    k_release: float = 0.5
    release_burst: float = 1.0
    burst_tau: float = 1.5
    k_absorption: float = 0.7
    k_gut_degradation: float = 0.03
    k_hepatic_metabolism: float = 0.25
    k_hepatic_to_plasma: float = 0.35
    k_plasma_to_tissue: float = 0.2
    k_tissue_to_plasma: float = 0.08
    k_systemic_clearance: float = 0.1
    k_tissue_clearance: float = 0.01
    tissue_reference: float = 15.0

    def __post_init__(self) -> None:
        values = tuple(getattr(self, name) for name in self.__dataclass_fields__)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("All parameters must be finite.")
        if self.initial_dose < 0:
            raise ValueError("initial_dose must be >= 0.")
        if not 0 <= self.a <= 1:
            raise ValueError("a must be in [0, 1].")
        if self.alpha <= 0 or self.beta <= 0 or self.b0 <= 0:
            raise ValueError("alpha, beta, and b0 must be > 0.")
        nonnegative = (
            "gamma", "tolerance_recovery", "k_release", "release_burst",
            "k_absorption", "k_gut_degradation", "k_hepatic_metabolism",
            "k_hepatic_to_plasma", "k_plasma_to_tissue",
            "k_tissue_to_plasma", "k_systemic_clearance", "k_tissue_clearance",
        )
        if any(getattr(self, n) < 0 for n in nonnegative):
            raise ValueError("Rate and feedback parameters must be >= 0.")
        if self.burst_tau <= 0 or self.tissue_reference <= 0:
            raise ValueError("burst_tau and tissue_reference must be > 0.")
        if self.k_hepatic_metabolism + self.k_hepatic_to_plasma <= 0:
            raise ValueError(
                "At least one of hepatic metabolism or hepatic-to-plasma "
                "transfer rates must be > 0."
            )

    @property
    def m_effective(self) -> float:
        """Fraction routed to first-pass metabolism under competing hazards."""
        total = self.k_hepatic_metabolism + self.k_hepatic_to_plasma
        return self.k_hepatic_metabolism / total

    @property
    def hepatic_escape_fraction(self) -> float:
        return 1.0 - self.m_effective

    @property
    def initial_total_amount(self) -> float:
        return self.initial_dose

    def release_rate(self, t: float) -> float:
        """First-order release with a decaying initial burst multiplier."""
        return self.k_release * (
            1.0 + self.release_burst * math.exp(-t / self.burst_tau)
        )


@dataclass(frozen=True)
class SimulationPoint:
    time: float
    depot: float
    gut: float
    liver: float
    plasma: float
    tissue: float
    gut_loss: float
    hepatic_metabolized: float
    systemic_eliminated: float
    tissue_eliminated: float
    tolerance: float
    core_index: float
    tissue_exposure_fraction: float
    tissue_weighted_index: float
    above_threshold: bool

    @property
    def accounted_amount(self) -> float:
        return (
            self.depot + self.gut + self.liver + self.plasma + self.tissue
            + self.gut_loss + self.hepatic_metabolized
            + self.systemic_eliminated + self.tissue_eliminated
        )


@dataclass(frozen=True)
class SimulationResult:
    points: tuple[SimulationPoint, ...]
    initial_amount: float

    @property
    def final(self) -> SimulationPoint:
        return self.points[-1]

    @property
    def max_mass_balance_error(self) -> float:
        return max(abs(p.accounted_amount - self.initial_amount) for p in self.points)

    @property
    def first_threshold_crossing_time(self) -> float | None:
        for left, right in zip(self.points, self.points[1:]):
            if left.above_threshold != right.above_threshold:
                y0, y1 = left.core_index, right.core_index
                if y1 == y0:
                    return right.time
                fraction = (1.0 - y0) / (y1 - y0)
                return left.time + fraction * (right.time - left.time)
        return None

    def rows(self) -> list[dict[str, float | bool]]:
        return [
            {
                "time": p.time,
                "depot": p.depot,
                "gut": p.gut,
                "liver": p.liver,
                "plasma": p.plasma,
                "tissue": p.tissue,
                "gut_loss": p.gut_loss,
                "hepatic_metabolized": p.hepatic_metabolized,
                "systemic_eliminated": p.systemic_eliminated,
                "tissue_eliminated": p.tissue_eliminated,
                "tolerance": p.tolerance,
                "core_index": p.core_index,
                "tissue_exposure_fraction": p.tissue_exposure_fraction,
                "tissue_weighted_index": p.tissue_weighted_index,
                "above_threshold": p.above_threshold,
                "accounted_amount": p.accounted_amount,
            }
            for p in self.points
        ]


# State vector:
# D, G, H, P, T, gut_loss, hepatic_met, systemic_elim, tissue_elim, b
def _rhs(p: BALMultiParameters, t: float, s: list[float]) -> list[float]:
    D, G, H, P, T, gut_loss, hepatic_met, systemic_elim, tissue_elim, b = s
    kr = p.release_rate(t)
    release = kr * D
    absorption = p.k_absorption * G
    gut_deg = p.k_gut_degradation * G
    hepatic_met_rate = p.k_hepatic_metabolism * H
    hepatic_to_plasma = p.k_hepatic_to_plasma * H
    plasma_to_tissue = p.k_plasma_to_tissue * P
    tissue_to_plasma = p.k_tissue_to_plasma * T
    systemic_clearance = p.k_systemic_clearance * P
    tissue_clearance = p.k_tissue_clearance * T

    m_eff = p.m_effective
    y = core_bioavailability(p.a, m_eff, b, p.alpha, p.beta)
    tissue_fraction = T / (T + p.tissue_reference)
    db = (
        p.gamma * y * tissue_fraction
        - p.tolerance_recovery * (b - p.b0)
    )

    return [
        -release,
        release - absorption - gut_deg,
        absorption - hepatic_met_rate - hepatic_to_plasma,
        hepatic_to_plasma - plasma_to_tissue + tissue_to_plasma - systemic_clearance,
        plasma_to_tissue - tissue_to_plasma - tissue_clearance,
        gut_deg,
        hepatic_met_rate,
        systemic_clearance,
        tissue_clearance,
        db,
    ]


def _add_scaled(s: list[float], k: list[float], scale: float) -> list[float]:
    return [x + scale * dx for x, dx in zip(s, k)]


def _rk4_step(p: BALMultiParameters, t: float, s: list[float], dt: float) -> list[float]:
    k1 = _rhs(p, t, s)
    k2 = _rhs(p, t + dt / 2, _add_scaled(s, k1, dt / 2))
    k3 = _rhs(p, t + dt / 2, _add_scaled(s, k2, dt / 2))
    k4 = _rhs(p, t + dt, _add_scaled(s, k3, dt))
    result = [
        x + dt * (a + 2*b + 2*c + d) / 6
        for x, a, b, c, d in zip(s, k1, k2, k3, k4)
    ]

    # RK4 is not positivity-preserving for arbitrarily large steps. Fail
    # explicitly rather than silently hiding a materially unstable step.
    amount_indices = range(9)
    if any(result[i] < -1e-9 for i in amount_indices):
        raise ArithmeticError(
            "Negative compartment amount detected. Reduce dt or use "
            "smaller kinetic rates."
        )
    for i in amount_indices:
        if result[i] < 0:
            result[i] = 0.0
    if result[9] < p.b0 - 1e-8:
        raise ArithmeticError(
            "Tolerance state fell below b0. Reduce dt or inspect parameters."
        )
    if result[9] < p.b0:
        result[9] = p.b0
    return result


def _point(p: BALMultiParameters, t: float, s: list[float]) -> SimulationPoint:
    D, G, H, P, T, gut_loss, hepatic_met, systemic_elim, tissue_elim, b = s
    y = core_bioavailability(p.a, p.m_effective, b, p.alpha, p.beta)
    frac = T / (T + p.tissue_reference)
    return SimulationPoint(
        time=t, depot=D, gut=G, liver=H, plasma=P, tissue=T,
        gut_loss=gut_loss, hepatic_metabolized=hepatic_met,
        systemic_eliminated=systemic_elim, tissue_eliminated=tissue_elim,
        tolerance=b, core_index=y, tissue_exposure_fraction=frac,
        tissue_weighted_index=y * frac,
        above_threshold=threshold_condition(
            p.a, p.m_effective, b, p.alpha, p.beta
        ),
    )


def simulate(p: BALMultiParameters, duration: float, dt: float = 0.05) -> SimulationResult:
    """Simulate the five-compartment PK-inspired model plus tolerance state."""
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("duration must be finite and >= 0.")
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and > 0.")

    state = [p.initial_dose, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, p.b0]
    points = [_point(p, 0.0, state)]
    t = 0.0
    while t < duration:
        step = min(dt, duration - t)
        state = _rk4_step(p, t, state, step)
        t += step
        if math.isclose(t, duration, rel_tol=1e-12, abs_tol=1e-12):
            t = duration
        points.append(_point(p, t, state))

    return SimulationResult(tuple(points), p.initial_total_amount)
