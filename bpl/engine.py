"""BPL 0.3 ODE model interpreter.

BPL models are TOML-compatible text files using the .bpl extension.
The expression evaluator accepts a deliberately small arithmetic language;
model files cannot execute arbitrary Python, access files, or use the network.
"""
from __future__ import annotations

import ast
import csv
import json
import math
import re
import tomllib
from pathlib import Path
from typing import Any, Callable


class BPLError(Exception):
    """A model, validation, or simulation error suitable for end users."""


FUNCTIONS: dict[str, Callable[..., float]] = {
    "ln": math.log,
    "log": math.log,
    "exp": math.exp,
    "sqrt": math.sqrt,
    "abs": abs,
    "min": min,
    "max": max,
    "clip": lambda x, lo, hi: min(max(x, lo), hi),
}
BINOPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a**b,
    ast.Mod: lambda a, b: a % b,
}
UNARYOPS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}
LEVELS = ("organism", "organ", "tissue", "cell", "organelle", "molecule")
SUPPORTED_INTEGRATORS = ("euler", "forward_euler", "rk4")
MAX_STEPS = 2_000_000


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BPLError(f"{label}은 숫자여야 합니다.")
    result = float(value)
    if not math.isfinite(result):
        raise BPLError(f"{label}은 유한한 숫자여야 합니다.")
    return result


def _validate_expr(node: ast.AST, allowed_names: set[str]) -> None:
    if isinstance(node, ast.Expression):
        _validate_expr(node.body, allowed_names)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise BPLError("수식에는 숫자 상수만 사용할 수 있습니다.")
        if not math.isfinite(float(node.value)):
            raise BPLError("수식의 숫자 상수는 유한한 값이어야 합니다.")
    elif isinstance(node, ast.Name):
        if node.id not in allowed_names and node.id not in FUNCTIONS:
            raise BPLError(f"정의되지 않은 변수 또는 함수: {node.id}")
    elif isinstance(node, ast.BinOp):
        if type(node.op) not in BINOPS:
            raise BPLError("지원하지 않는 산술 연산자입니다.")
        _validate_expr(node.left, allowed_names)
        _validate_expr(node.right, allowed_names)
    elif isinstance(node, ast.UnaryOp):
        if type(node.op) not in UNARYOPS:
            raise BPLError("지원하지 않는 단항 연산자입니다.")
        _validate_expr(node.operand, allowed_names)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
            raise BPLError("허용되지 않은 함수 호출입니다.")
        if node.keywords:
            raise BPLError("함수의 키워드 인수는 지원하지 않습니다.")
        fn_name = node.func.id
        if fn_name in {"ln", "log", "exp", "sqrt", "abs"} and len(node.args) != 1:
            raise BPLError(f"{fn_name}() 함수는 인수 1개가 필요합니다.")
        if fn_name == "clip" and len(node.args) != 3:
            raise BPLError("clip() 함수는 인수 3개가 필요합니다.")
        if fn_name in {"min", "max"} and len(node.args) < 1:
            raise BPLError(f"{fn_name}() 함수는 인수가 1개 이상 필요합니다.")
        for arg in node.args:
            _validate_expr(arg, allowed_names)
    else:
        raise BPLError(f"지원하지 않는 수식 요소입니다: {type(node).__name__}")


def compile_expression(expression: str, allowed_names: set[str]) -> ast.Expression:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise BPLError(f"수식 문법 오류: {expression!r}") from exc
    _validate_expr(tree, allowed_names)
    return tree


def evaluate(node: ast.AST, scope: dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return evaluate(node.body, scope)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id in scope:
            return float(scope[node.id])
        raise BPLError(f"실행 시 변수를 찾을 수 없습니다: {node.id}")
    if isinstance(node, ast.BinOp):
        left = evaluate(node.left, scope)
        right = evaluate(node.right, scope)
        try:
            if isinstance(node.op, ast.Pow) and abs(right) > 1024:
                raise BPLError("거듭제곱 지수가 안전 허용 범위(-1024~1024)를 벗어났습니다.")
            result = BINOPS[type(node.op)](left, right)
            if isinstance(result, complex) or not math.isfinite(float(result)):
                raise BPLError("수식 결과가 유한한 실수(real number)가 아닙니다.")
            return float(result)
        except BPLError:
            raise
        except (ZeroDivisionError, OverflowError, ValueError, TypeError) as exc:
            raise BPLError(f"수식 계산 실패: {exc}") from exc
    if isinstance(node, ast.UnaryOp):
        return float(UNARYOPS[type(node.op)](evaluate(node.operand, scope)))
    if isinstance(node, ast.Call):
        fn = FUNCTIONS[node.func.id]
        args = [evaluate(arg, scope) for arg in node.args]
        try:
            result = fn(*args)
        except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
            raise BPLError(f"{node.func.id}() 계산 실패: {exc}") from exc
        if not math.isfinite(float(result)):
            raise BPLError(f"{node.func.id}() 결과가 유한한 숫자가 아닙니다.")
        return float(result)
    raise BPLError("지원하지 않는 수식 노드입니다.")


def _validate_components(components: list[dict[str, Any]]) -> None:
    if not components:
        return
    by_id: dict[str, dict[str, Any]] = {}
    for comp in components:
        cid = comp.get("id")
        level = comp.get("level")
        if not isinstance(cid, str) or not cid.strip() or cid in by_id:
            raise BPLError(f"component id가 없거나 중복되었습니다: {cid}")
        if level not in LEVELS:
            raise BPLError(f"지원하지 않는 component level: {level}")
        by_id[cid] = comp

    roots = [c for c in components if not c.get("parent")]
    if len(roots) != 1 or roots[0].get("level") != "organism":
        raise BPLError("components를 사용할 때 organism 최상위 구성요소는 정확히 하나여야 합니다.")

    for comp in components:
        parent = comp.get("parent", "")
        if not parent:
            continue
        if parent not in by_id:
            raise BPLError(f"{comp['id']}의 parent를 찾을 수 없습니다: {parent}")
        parent_level = LEVELS.index(by_id[parent]["level"])
        child_level = LEVELS.index(comp["level"])
        if parent_level >= child_level:
            raise BPLError(f"계층 순서 오류: {parent} -> {comp['id']}")


def load_model(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise BPLError(f"모델 파일을 찾을 수 없습니다: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise BPLError(f"BPL 파일 문법 오류: {exc}") from exc

    for section in ("model", "simulation", "states", "equations"):
        if section not in data:
            raise BPLError(f"필수 섹션이 없습니다: [{section}]")
    if not isinstance(data["model"], dict) or not isinstance(data["simulation"], dict):
        raise BPLError("[model]과 [simulation]은 테이블이어야 합니다.")

    sim = data["simulation"]
    start = _number(sim.get("start", 0.0), "simulation.start")
    end = _number(sim.get("end", 0.0), "simulation.end")
    step = _number(sim.get("step", 1.0), "simulation.step")
    if step <= 0 or end < start:
        raise BPLError("simulation.step은 양수이고 end는 start 이상이어야 합니다.")
    integrator = str(sim.get("integrator", "euler")).lower()
    if integrator not in SUPPORTED_INTEGRATORS:
        raise BPLError(f"지원하지 않는 적분기: {integrator}. 선택: {', '.join(SUPPORTED_INTEGRATORS)}")
    if end > start and math.ceil((end - start) / step) > MAX_STEPS:
        raise BPLError(f"시뮬레이션 단계가 {MAX_STEPS:,}회를 초과합니다.")

    states = data["states"]
    equations = data["equations"]
    constants = data.get("constants", {})
    if not isinstance(states, dict) or not states:
        raise BPLError("[states.*]에 최소 하나의 상태 변수가 필요합니다.")
    if not isinstance(equations, dict):
        raise BPLError("[equations.*] 형식이 올바르지 않습니다.")
    if not isinstance(constants, dict):
        raise BPLError("[constants]는 테이블이어야 합니다.")

    identifiers = set(states) | set(constants)
    overlap = set(states) & set(constants)
    invalid_names = {name for name in identifiers if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)}
    reserved_names = identifiers & (set(FUNCTIONS) | {"t", "time"})
    if overlap or invalid_names or reserved_names:
        raise BPLError(
            "상태·상수 이름 충돌 또는 잘못된 식별자입니다: "
            f"중복={sorted(overlap)}, 형식오류={sorted(invalid_names)}, 예약어={sorted(reserved_names)}"
        )
    for name, value in constants.items():
        _number(value, f"constants.{name}")

    for name, spec in states.items():
        if not isinstance(spec, dict) or "initial" not in spec:
            raise BPLError(f"states.{name}에는 initial 값이 필요합니다.")
        initial = _number(spec["initial"], f"states.{name}.initial")
        minimum = _number(spec["min"], f"states.{name}.min") if "min" in spec else None
        maximum = _number(spec["max"], f"states.{name}.max") if "max" in spec else None
        if minimum is not None and maximum is not None and minimum > maximum:
            raise BPLError(f"states.{name}: min이 max보다 클 수 없습니다.")
        if minimum is not None and initial < minimum:
            raise BPLError(f"초깃값 {name}={initial}이 최소값 {minimum}보다 작습니다.")
        if maximum is not None and initial > maximum:
            raise BPLError(f"초깃값 {name}={initial}이 최대값 {maximum}보다 큽니다.")
        if not isinstance(spec.get("unit", "unspecified"), str):
            raise BPLError(f"states.{name}.unit은 문자열이어야 합니다.")

    components = data.get("components", [])
    if not isinstance(components, list):
        raise BPLError("[[components]]는 배열 테이블이어야 합니다.")
    _validate_components(components)
    allowed = set(states) | set(constants) | {"t"}
    for name, spec in states.items():
        compile_expression(str(spec.get("rate", "0")), allowed)
    used_outputs = set(states) | {"time"}
    for name, spec in equations.items():
        if not isinstance(spec, dict) or "expression" not in spec:
            raise BPLError(f"equations.{name}에 expression이 필요합니다.")
        output_name = spec.get("output", name)
        if not isinstance(output_name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", output_name):
            raise BPLError(f"equations.{name}.output은 유효한 변수 이름이어야 합니다.")
        if output_name in used_outputs or output_name in constants or output_name in (set(FUNCTIONS) | {"t"}):
            raise BPLError(f"equations.{name}.output 이름이 다른 열 또는 예약어와 충돌합니다: {output_name}")
        used_outputs.add(output_name)
        compile_expression(str(spec["expression"]), allowed)
    return data


def _check_bounds(states: dict[str, dict[str, Any]], values: dict[str, float], context: str) -> None:
    for name, value in values.items():
        if not math.isfinite(value):
            raise BPLError(f"state {name}이 유한한 숫자가 아닙니다 ({context}).")
        spec = states[name]
        if "min" in spec and value < float(spec["min"]) - 1e-10:
            raise BPLError(f"state {name}이 최소 허용값을 벗어났습니다 ({context}): {value}")
        if "max" in spec and value > float(spec["max"]) + 1e-10:
            raise BPLError(f"state {name}이 최대 허용값을 벗어났습니다 ({context}): {value}")


def run_model(data: dict[str, Any], overrides: dict[str, float] | None = None) -> list[dict[str, float]]:
    sim = data["simulation"]
    start = float(sim.get("start", 0.0))
    end = float(sim.get("end", 0.0))
    step = float(sim.get("step", 1.0))
    integrator = str(sim.get("integrator", "euler")).lower()
    if integrator == "forward_euler":
        integrator = "euler"

    states = data["states"]
    constants = {k: float(v) for k, v in data.get("constants", {}).items()}
    values = {name: float(spec["initial"]) for name, spec in states.items()}
    for key, raw_value in (overrides or {}).items():
        if key not in values:
            raise BPLError(f"--set으로 변경할 수 없는 state입니다: {key}")
        values[key] = _number(raw_value, f"--set {key}")
    _check_bounds(states, values, "초기값")

    allowed = set(values) | set(constants) | {"t"}
    rate_trees = {name: compile_expression(str(spec.get("rate", "0")), allowed)
                  for name, spec in states.items()}
    equation_trees = {name: compile_expression(str(spec["expression"]), allowed)
                      for name, spec in data["equations"].items()}

    def calc_rates(current: dict[str, float], current_t: float) -> dict[str, float]:
        scope = {**constants, **current, "t": current_t}
        return {name: evaluate(tree, scope) for name, tree in rate_trees.items()}

    def add_scaled(base: dict[str, float], slope: dict[str, float], scale: float) -> dict[str, float]:
        return {name: base[name] + scale * slope[name] for name in base}

    def take_step(current: dict[str, float], current_t: float, dt: float) -> dict[str, float]:
        k1 = calc_rates(current, current_t)
        if integrator == "euler":
            next_state = add_scaled(current, k1, dt)
        else:
            k2_state = add_scaled(current, k1, dt / 2.0)
            k2 = calc_rates(k2_state, current_t + dt / 2.0)
            k3_state = add_scaled(current, k2, dt / 2.0)
            k3 = calc_rates(k3_state, current_t + dt / 2.0)
            k4_state = add_scaled(current, k3, dt)
            k4 = calc_rates(k4_state, current_t + dt)
            next_state = {
                name: current[name] + dt * (k1[name] + 2*k2[name] + 2*k3[name] + k4[name]) / 6.0
                for name in current
            }
        _check_bounds(states, next_state, f"t={current_t + dt:g}")
        return next_state

    rows: list[dict[str, float]] = []
    t = start
    current = dict(values)
    epsilon = max(1.0, abs(end), abs(start)) * 1e-12
    while True:
        scope = {**constants, **current, "t": t}
        row: dict[str, float] = {"time": t, **current}
        for eq_name, tree in equation_trees.items():
            result = evaluate(tree, scope)
            output_name = data["equations"][eq_name].get("output", eq_name)
            row[output_name] = result
        rows.append(row)
        if t >= end - epsilon:
            break
        dt = min(step, end - t)
        current = take_step(current, t, dt)
        t += dt
        if len(rows) > MAX_STEPS:
            raise BPLError(f"시뮬레이션 행 수가 {MAX_STEPS:,}회를 초과합니다.")
    return rows


def write_csv(rows: list[dict[str, float]], path: Path) -> None:
    if not rows:
        raise BPLError("저장할 시뮬레이션 결과가 없습니다.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(data: dict[str, Any], rows: list[dict[str, float]], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": data["model"], "simulation": data["simulation"], "rows": rows}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
