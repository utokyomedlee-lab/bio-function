import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bpl.engine import BPLError, compile_expression, evaluate, load_model, run_model
from bpl.interaction import load_interaction_model, run_interaction_model

ROOT = Path(__file__).resolve().parents[1]


class BPLTests(unittest.TestCase):
    def test_installed_example_export_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_dir = Path(tmp) / "bpl-examples"
            completed = subprocess.run(
                [sys.executable, "-m", "bpl", "examples", "--export", str(export_dir)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            for filename in (
                "aging_system.bpl",
                "senescence_immune_lysosome.bpl",
                "tissue_repair.bpl",
            ):
                self.assertTrue((export_dir / filename).is_file(), filename)

    def test_aging_example_runs(self):
        model = load_model(ROOT / "examples" / "aging_system.bpl")
        rows = run_model(model)
        self.assertEqual(len(rows), 41)
        self.assertAlmostEqual(rows[0]["x"], 1.0)
        self.assertAlmostEqual(rows[0]["L"], 1.0)
        self.assertAlmostEqual(rows[0]["y_original"], rows[0]["y_candidate"])
        self.assertGreater(rows[-1]["x"], rows[0]["x"])

    def test_tissue_model_runs_and_final_time_is_exact(self):
        model = load_model(ROOT / "examples" / "tissue_repair.bpl")
        rows = run_model(model)
        self.assertAlmostEqual(rows[-1]["time"], 20.0)
        self.assertGreater(rows[-1]["integrity_proxy"], rows[0]["integrity_proxy"])

    def test_rk4_exponential_accuracy(self):
        expression = compile_expression("x", {"x"})
        self.assertAlmostEqual(evaluate(expression, {"x": 2.0}), 2.0)
        text = '''
[model]\nname="exp"\nversion="0.1"\n[simulation]\nstart=0\nend=1\nstep=0.1\nintegrator="rk4"\n[states.x]\ninitial=1\nrate="x"\n[equations.out]\nexpression="x"\n'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "exp.bpl"
            path.write_text(text, encoding="utf-8")
            rows = run_model(load_model(path))
        self.assertAlmostEqual(rows[-1]["x"], math.e, places=5)

    def test_unsafe_expression_rejected(self):
        with self.assertRaises(BPLError):
            compile_expression("__import__('os').system('echo unsafe')", {"x"})

    def test_attribute_access_rejected(self):
        with self.assertRaises(BPLError):
            compile_expression("x.real", {"x"})

    def test_unknown_variable_rejected(self):
        with self.assertRaises(BPLError):
            compile_expression("x + mystery", {"x"})

    def test_bounds_checked_for_overrides(self):
        model = load_model(ROOT / "examples" / "aging_system.bpl")
        with self.assertRaises(BPLError):
            run_model(model, {"i": 1.2})

    def test_log_domain_errors_are_readable(self):
        tree = compile_expression("ln(x)", {"x"})
        with self.assertRaises(BPLError):
            evaluate(tree, {"x": -1.0})

    def test_unsafe_large_exponent_rejected(self):
        tree = compile_expression("2 ** n", {"n"})
        with self.assertRaises(BPLError):
            evaluate(tree, {"n": 2000.0})

    def test_equation_output_collision_rejected(self):
        text = '''
[model]
name="collision"
version="0.1"
[simulation]
start=0
end=0
step=1
[states.x]
initial=1
[equations.bad]
output="x"
expression="x+1"
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "collision.bpl"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(BPLError):
                load_model(path)

    def test_non_finite_literal_rejected(self):
        with self.assertRaises(BPLError):
            compile_expression("1e999 + x", {"x"})

    def test_interaction_model_runs_and_outputs_aging_indices(self):
        model = load_interaction_model(ROOT / "examples" / "senescence_immune_lysosome.bpl")
        rows = run_interaction_model(model)
        self.assertEqual(len(rows), 201)
        self.assertAlmostEqual(rows[0]["x"], 1.0)
        self.assertAlmostEqual(rows[0]["i"], 0.35)
        self.assertAlmostEqual(rows[0]["L"], 1.0)
        self.assertTrue(math.isfinite(rows[-1]["y_candidate"]))
        self.assertGreater(rows[-1]["senescent_cells"], rows[0]["senescent_cells"])
        self.assertLess(rows[-1]["lysosomal_capacity"], rows[0]["lysosomal_capacity"])

    def test_interaction_parameter_fraction_is_bounded(self):
        model = load_interaction_model(ROOT / "examples" / "senescence_immune_lysosome.bpl")
        with self.assertRaises(BPLError):
            run_interaction_model(model, parameter_overrides={"immune_clearance_fraction": 1.2})

    def test_interaction_rejects_negative_flux(self):
        model = load_interaction_model(ROOT / "examples" / "senescence_immune_lysosome.bpl")
        model["parameters"]["senescence_input_rate"] = -1.0
        with self.assertRaises(BPLError):
            run_interaction_model(model)

    def test_interaction_unknown_stoichiometry_state_rejected(self):
        model_path = ROOT / "examples" / "senescence_immune_lysosome.bpl"
        text = model_path.read_text(encoding="utf-8").replace(
            'stoichiometry = { senescent_cells = -1.0 }',
            'stoichiometry = { senescent_cells = -1.0, unknown = -1.0 }'
        )
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bad.bpl"
            target.write_text(text, encoding="utf-8")
            with self.assertRaises(BPLError):
                load_interaction_model(target)


if __name__ == "__main__":
    unittest.main()
