import math
import unittest
from dataclasses import replace

from bal.core import core_bioavailability, core_sensitivities, threshold_condition
from bal.multicompartment import BALMultiParameters, simulate
from bal.uncertainty import monte_carlo


class TestBALCore(unittest.TestCase):
    def test_threshold_boundary_and_inequality(self):
        a, m, alpha, beta = 0.8, 0.2, 2.0, 1.0
        bcrit = alpha * a * (1 - m) / beta
        self.assertAlmostEqual(core_bioavailability(a, m, bcrit, alpha, beta), 1.0)
        self.assertFalse(threshold_condition(a, m, bcrit, alpha, beta))
        self.assertTrue(threshold_condition(a, m, bcrit * 0.99, alpha, beta))

    def test_sensitivity_signs_and_finite_difference(self):
        a, m, b, alpha, beta = 0.8, 0.2, 0.5, 2.0, 1.0
        deriv = core_sensitivities(a, m, b, alpha, beta)
        h = 1e-6
        fd_a = (
            core_bioavailability(a+h, m, b, alpha, beta)
            - core_bioavailability(a-h, m, b, alpha, beta)
        ) / (2*h)
        fd_m = (
            core_bioavailability(a, m+h, b, alpha, beta)
            - core_bioavailability(a, m-h, b, alpha, beta)
        ) / (2*h)
        fd_b = (
            core_bioavailability(a, m, b+h, alpha, beta)
            - core_bioavailability(a, m, b-h, alpha, beta)
        ) / (2*h)
        self.assertAlmostEqual(deriv["a"], fd_a, places=6)
        self.assertAlmostEqual(deriv["m"], fd_m, places=6)
        self.assertAlmostEqual(deriv["b"], fd_b, places=6)
        self.assertGreater(deriv["a"], 0)
        self.assertLess(deriv["m"], 0)
        self.assertLess(deriv["b"], 0)


class TestBALMultiCompartment(unittest.TestCase):
    def setUp(self):
        self.p = BALMultiParameters()

    def test_mass_balance(self):
        result = simulate(self.p, duration=30, dt=0.05)
        self.assertLess(result.max_mass_balance_error, 1e-8)
        self.assertAlmostEqual(result.final.accounted_amount, self.p.initial_dose, places=7)

    def test_nonnegative_compartments_and_tolerance_invariant(self):
        result = simulate(self.p, duration=30, dt=0.05)
        for point in result.points:
            for name in (
                "depot", "gut", "liver", "plasma", "tissue",
                "gut_loss", "hepatic_metabolized",
                "systemic_eliminated", "tissue_eliminated",
            ):
                self.assertGreaterEqual(getattr(point, name), 0.0)
            self.assertGreaterEqual(point.tolerance, self.p.b0 - 1e-9)

    def test_zero_dose_has_no_compartment_mass_or_tolerance_gain(self):
        p = replace(self.p, initial_dose=0.0)
        result = simulate(p, duration=10, dt=0.05)
        self.assertAlmostEqual(result.final.accounted_amount, 0.0, places=9)
        self.assertAlmostEqual(result.final.tolerance, p.b0, places=9)

    def test_zero_gamma_and_zero_recovery_tolerance_is_constant_without_exposure(self):
        p = replace(self.p, initial_dose=0.0, gamma=0.0, tolerance_recovery=0.0)
        result = simulate(p, duration=10, dt=0.1)
        self.assertTrue(all(math.isclose(x.tolerance, p.b0) for x in result.points))

    def test_h_epatic_extraction_fraction(self):
        self.assertAlmostEqual(self.p.m_effective, 0.25 / 0.60)
        self.assertAlmostEqual(self.p.m_effective + self.p.hepatic_escape_fraction, 1.0)

    def test_zero_duration(self):
        result = simulate(self.p, duration=0)
        self.assertEqual(len(result.points), 1)
        self.assertEqual(result.final.time, 0.0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            replace(self.p, a=1.2)
        with self.assertRaises(ValueError):
            simulate(self.p, duration=-1)
        with self.assertRaises(ValueError):
            simulate(self.p, duration=1, dt=0)

    def test_time_dependent_release_starts_above_baseline(self):
        self.assertGreater(self.p.release_rate(0), self.p.k_release)
        self.assertLess(self.p.release_rate(20), self.p.release_rate(0))


class TestUncertainty(unittest.TestCase):
    def setUp(self):
        self.p = BALMultiParameters()

    def test_reproducibility_and_summary(self):
        ranges = {"k_release": [0.4, 0.6], "gamma": [0.02, 0.04]}
        first = monte_carlo(self.p, ranges, samples=5, duration=3, dt=0.05, seed=11)
        second = monte_carlo(self.p, ranges, samples=5, duration=3, dt=0.05, seed=11)
        self.assertEqual(first, second)
        self.assertEqual(first["samples"], 5)
        self.assertIn("p95", first["summary"]["final_tissue"])

    def test_invalid_range_name(self):
        with self.assertRaises(ValueError):
            monte_carlo(self.p, {"not_a_parameter": [0, 1]}, samples=2, duration=1)


if __name__ == "__main__":
    unittest.main()
