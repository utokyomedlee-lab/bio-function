from __future__ import annotations
import math


def _validate_core(a: float, m: float, b: float, alpha: float, beta: float) -> None:
    values = (a, m, b, alpha, beta)
    if not all(math.isfinite(x) for x in values):
        raise ValueError("All BAL core inputs must be finite.")
    if not 0.0 <= a <= 1.0:
        raise ValueError("a must be in [0, 1].")
    if not 0.0 <= m < 1.0:
        raise ValueError("m must be in [0, 1).")
    if b <= 0.0:
        raise ValueError("b must be > 0.")
    if alpha <= 0.0 or beta <= 0.0:
        raise ValueError("alpha and beta must be > 0.")


def core_bioavailability(a: float, m: float, b: float,
                         alpha: float, beta: float) -> float:
    """Normalized BAL core: ln(1 + alpha*a*(1-m)) / ln(1 + beta*b)."""
    _validate_core(a, m, b, alpha, beta)
    numerator = math.log1p(alpha * a * (1.0 - m))
    denominator = math.log1p(beta * b)
    return numerator / denominator


def core_sensitivities(a: float, m: float, b: float,
                       alpha: float, beta: float) -> dict[str, float]:
    """Analytic partial derivatives of the BAL core index."""
    y = core_bioavailability(a, m, b, alpha, beta)
    A = alpha * a * (1.0 - m)
    den = math.log1p(beta * b)
    common = (1.0 + A) * den
    return {
        "a": alpha * (1.0 - m) / common,
        "m": -alpha * a / common,
        "b": -y * beta / ((1.0 + beta * b) * den),
    }


def threshold_condition(a: float, m: float, b: float,
                        alpha: float, beta: float) -> bool:
    """True exactly when y > 1; equality is the threshold boundary."""
    _validate_core(a, m, b, alpha, beta)
    return alpha * a * (1.0 - m) > beta * b
