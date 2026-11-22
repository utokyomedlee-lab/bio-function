"""BPL 0.3 population/reaction interaction engine.

This engine models well-mixed populations and biochemical pools using
mass-action / user-defined flux expressions. It is not an individual-cell,
spatial, or clinically validated whole-organism simulator.
"""
from __future__ import annotations

import csv
import json
import math
import tomllib
from pathlib import Path
from typing import Any

from .engine import BPLError, FUNCTIONS, compile_expression, evaluate

MAX_STEPS = 2_000_000


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BPLError(f"{label}은 숫자여야 합니다.")
    result = float(value)
    if not math.isfinite(result):
        raise BPLError(f"{label}은 유한한 숫자여야 합니다.")
    return result


def load_interaction_model(path: Path) -> dict[str, Any]:
    """Load and validate a BPL reaction/interactions model (.bpl TOML subset)."""
    path = Path(path)
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise BPLError(f"모델 파일을 찾을 수 없습니다: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise BPLError(f"BPL 상호작용 모델 문법 오류: {exc}") from exc

    for section in ("model", "simulation", "parameters", "states", "reactions", "equations"):
        if section not in data:
            raise BPLError(f"상호작용 모델에 필수 섹션이 없습니다: [{section}]")
    if not isinstance(data["model"], dict) or not isinstance(data["simulation"], dict):
        raise BPLError("[model]과 [simulation]은 테이블이어야 합니다.")

    sim = data["simulation"]
    start = _finite_number(sim.get("start", 0.0), "simulation.start")
    end = _finite_number(sim.get("end", 0.0), "simulation.end")
    step = _finite_number(sim.get("step", 1.0), "simulation.step")
    if step <= 0 or end < start:
        raise BPLError("simulation.step은 양수이고 end는 start 이상이어야 합니다.")
    integrator = str(sim.get("integrator", "rk4")).lower()
    if integrator not in {"euler", "forward_euler", "rk4"}:
        raise BPLError("integrator는 euler 또는 rk4여야 합니다.")
    if end > start and math.ceil((end - start) / step) > MAX_STEPS:
        raise BPLError(f"시뮬레이션 단계가 {MAX_STEPS:,}회를 초과합니다.")

    parameters = data["parameters"]
    states = data["states"]
    reactions = data["reactions"]
    equations = data["equations"]
    if not isinstance(parameters, dict) or not isinstance(states, dict) or not states:
        raise BPLError("[parameters]와 [states.*] 형식이 올바르지 않습니다.")
    if not isinstance(reactions, dict) or not reactions:
        raise BPLError("[reactions.*]에 최소 하나의 반응이 필요합니다.")
    if not isinstance(equations, dict):
        raise BPLError("[equations.*] 형식이 올바르지 않습니다.")

    reserved_names = set(FUNCTIONS) | {"t", "time"}
    if set(states) & set(parameters):
        raise BPLError("state와 parameter 이름이 중복됩니다.")
    for name, value in parameters.items():
        if not isinstance(name, str) or not name.isidentifier() or name in reserved_names:
            raise BPLError(f"유효하지 않거나 예약된 parameter 이름: {name!r}")
        _finite_number(value, f"parameters.{name}")
    parameter_bounds = data.get("parameter_bounds", {})
    if not isinstance(parameter_bounds, dict):
        raise BPLError("[parameter_bounds.*] 형식이 올바르지 않습니다.")
    for name, bounds in parameter_bounds.items():
        if name not in parameters or not isinstance(bounds, dict):
            raise BPLError(f"parameter_bounds.{name}는 기존 parameter의 범위여야 합니다.")
        lower = _finite_number(bounds["min"], f"parameter_bounds.{name}.min") if "min" in bounds else None
        upper = _finite_number(bounds["max"], f"parameter_bounds.{name}.max") if "max" in bounds else None
        if lower is not None and upper is not None and lower > upper:
            raise BPLError(f"parameter_bounds.{name}: min이 max보다 클 수 없습니다.")
        value = float(parameters[name])
        if lower is not None and value < lower:
            raise BPLError(f"parameters.{name}이 최소값 {lower}보다 작습니다.")
        if upper is not None and value > upper:
            raise BPLError(f"parameters.{name}이 최대값 {upper}보다 큽니다.")

    allowed_ids = set(states) | set(parameters) | {"t"}
    for name, spec in states.items():
        if not isinstance(name, str) or not name.isidentifier() or name in reserved_names:
            raise BPLError(f"유효하지 않거나 예약된 state 이름: {name!r}")
        if not isinstance(spec, dict) or "initial" not in spec:
            raise BPLError(f"states.{name}에는 initial 값이 필요합니다.")
        initial = _finite_number(spec["initial"], f"states.{name}.initial")
        lower = _finite_number(spec["min"], f"states.{name}.min") if "min" in spec else None
        upper = _finite_number(spec["max"], f"states.{name}.max") if "max" in spec else None
        if lower is not None and upper is not None and lower > upper:
            raise BPLError(f"states.{name}: min이 max보다 클 수 없습니다.")
        if lower is not None and initial < lower:
            raise BPLError(f"states.{name}.initial이 min보다 작습니다.")
        if upper is not None and initial > upper:
            raise BPLError(f"states.{name}.initial이 max보다 큽니다.")
        if not isinstance(spec.get("unit", "unspecified"), str):
            raise BPLError(f"states.{name}.unit은 문자열이어야 합니다.")

    for reaction_name, reaction in reactions.items():
        if not isinstance(reaction, dict) or "rate" not in reaction or "stoichiometry" not in reaction:
            raise BPLError(f"reactions.{reaction_name}에는 rate와 stoichiometry가 필요합니다.")
        compile_expression(str(reaction["rate"]), allowed_ids)
        stoich = reaction["stoichiometry"]
        if not isinstance(stoich, dict) or not stoich:
            raise BPLError(f"reactions.{reaction_name}.stoichiometry는 비어 있지 않은 테이블이어야 합니다.")
        for state_name, coefficient in stoich.items():
            if state_name not in states:
                raise BPLError(f"reactions.{reaction_name}: 알 수 없는 state {state_name!r}")
            _finite_number(coefficient, f"reactions.{reaction_name}.stoichiometry.{state_name}")

    used_outputs = set(states) | {"time"}
    for equation_name, equation in equations.items():
        if not isinstance(equation, dict) or "expression" not in equation:
            raise BPLError(f"equations.{equation_name}에 expression이 필요합니다.")
        output_name = equation.get("output", equation_name)
        if (not isinstance(output_name, str) or not output_name.isidentifier()
                or output_name in used_outputs or output_name in reserved_names):
            raise BPLError(f"equations.{equation_name}.output이 잘못되었거나 중복됩니다: {output_name!r}")
        if output_name in parameters:
            raise BPLError(f"equation output이 parameter와 충돌합니다: {output_name}")
        used_outputs.add(output_name)
        compile_expression(str(equation["expression"]), allowed_ids)

    return data


def _check_state_bounds(states: dict[str, Any], values: dict[str, float], where: str) -> None:
    for name, value in values.items():
        if not math.isfinite(value):
            raise BPLError(f"{where}: {name} 값이 유한하지 않습니다.")
        spec = states[name]
        if "min" in spec and value < float(spec["min"]) - 1e-10:
            raise BPLError(f"{where}: {name}={value:.8g}이 최소값 {spec['min']}보다 작습니다.")
        if "max" in spec and value > float(spec["max"]) + 1e-10:
            raise BPLError(f"{where}: {name}={value:.8g}이 최대값 {spec['max']}보다 큽니다.")


def run_interaction_model(
    data: dict[str, Any],
    state_overrides: dict[str, float] | None = None,
    parameter_overrides: dict[str, float] | None = None,
) -> list[dict[str, float]]:
    """Integrate a well-mixed reaction network and calculate derived outputs."""
    sim = data["simulation"]
    start = float(sim.get("start", 0.0))
    end = float(sim.get("end", 0.0))
    step = float(sim.get("step", 1.0))
    integrator = str(sim.get("integrator", "rk4")).lower()
    if integrator == "forward_euler":
        integrator = "euler"

    states_spec = data["states"]
    parameters = {key: _finite_number(value, f"parameters.{key}") for key, value in data["parameters"].items()}
    values = {key: float(spec["initial"]) for key, spec in states_spec.items()}

    for key, raw in (state_overrides or {}).items():
        if key not in values:
            raise BPLError(f"변경할 수 없는 state입니다: {key}")
        values[key] = _finite_number(raw, f"state override {key}")
    for key, raw in (parameter_overrides or {}).items():
        if key not in parameters:
            raise BPLError(f"변경할 수 없는 parameter입니다: {key}")
        parameters[key] = _finite_number(raw, f"parameter override {key}")
    for key, bounds in data.get("parameter_bounds", {}).items():
        value = parameters[key]
        if "min" in bounds and value < float(bounds["min"]):
            raise BPLError(f"parameter {key}={value}가 최소값 {bounds['min']}보다 작습니다.")
        if "max" in bounds and value > float(bounds["max"]):
            raise BPLError(f"parameter {key}={value}가 최대값 {bounds['max']}보다 큽니다.")
    _check_state_bounds(states_spec, values, "초기값")

    allowed = set(values) | set(parameters) | {"t"}
    rate_trees = {
        name: compile_expression(str(reaction["rate"]), allowed)
        for name, reaction in data["reactions"].items()
    }
    equation_trees = {
        name: compile_expression(str(equation["expression"]), allowed)
        for name, equation in data["equations"].items()
    }

    def fluxes(current: dict[str, float], current_t: float) -> dict[str, float]:
        scope = {**parameters, **current, "t": current_t}
        results: dict[str, float] = {}
        for reaction_name, tree in rate_trees.items():
            flux = evaluate(tree, scope)
            if flux < -1e-12:
                raise BPLError(
                    f"반응 {reaction_name}의 flux가 음수({flux:.8g})입니다. "
                    "정방향 반응은 0 이상의 속도를 사용하고 역반응은 별도 반응으로 정의하세요."
                )
            results[reaction_name] = max(0.0, flux)
        return results

    def derivatives(current: dict[str, float], current_t: float) -> dict[str, float]:
        current_fluxes = fluxes(current, current_t)
        deriv = {state_name: 0.0 for state_name in current}
        for reaction_name, flux in current_fluxes.items():
            for state_name, coefficient in data["reactions"][reaction_name]["stoichiometry"].items():
                deriv[state_name] += float(coefficient) * flux
        return deriv

    def add_scaled(base: dict[str, float], slope: dict[str, float], scale: float) -> dict[str, float]:
        return {name: base[name] + scale * slope[name] for name in base}

    def take_step(current: dict[str, float], current_t: float, dt: float) -> dict[str, float]:
        k1 = derivatives(current, current_t)
        if integrator == "euler":
            nxt = add_scaled(current, k1, dt)
        else:
            k2 = derivatives(add_scaled(current, k1, dt / 2), current_t + dt / 2)
            k3 = derivatives(add_scaled(current, k2, dt / 2), current_t + dt / 2)
            k4 = derivatives(add_scaled(current, k3, dt), current_t + dt)
            nxt = {
                name: current[name] + dt * (k1[name] + 2*k2[name] + 2*k3[name] + k4[name]) / 6
                for name in current
            }
        _check_state_bounds(states_spec, nxt, f"t={current_t + dt:g}")
        return nxt

    rows: list[dict[str, float]] = []
    t = start
    current = dict(values)
    epsilon = max(1.0, abs(start), abs(end)) * 1e-12
    while True:
        scope = {**parameters, **current, "t": t}
        row: dict[str, float] = {"time": t, **current}
        for equation_name, tree in equation_trees.items():
            output_name = data["equations"][equation_name].get("output", equation_name)
            row[output_name] = evaluate(tree, scope)
        rows.append(row)
        if t >= end - epsilon:
            break
        dt = min(step, end - t)
        current = take_step(current, t, dt)
        t += dt
        if len(rows) > MAX_STEPS:
            raise BPLError(f"시뮬레이션 행 수가 {MAX_STEPS:,}회를 초과합니다.")
    return rows


def write_interaction_csv(rows: list[dict[str, float]], path: Path) -> None:
    if not rows:
        raise BPLError("저장할 결과가 없습니다.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_interaction_json(data: dict[str, Any], rows: list[dict[str, float]], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": data["model"],
        "simulation": data["simulation"],
        "parameters": data["parameters"],
        "rows": rows,
        "interpretation": "illustrative computational model; not a clinically validated prediction",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
