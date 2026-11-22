"""Command-line interface for BPL."""
from __future__ import annotations

import argparse
import shutil
import sys
from importlib.resources import files as package_files
from pathlib import Path
from typing import Sequence

from . import __version__
from .engine import BPLError, load_model, run_model, write_csv, write_json
from .interaction import (
    load_interaction_model,
    run_interaction_model,
    write_interaction_csv,
    write_interaction_json,
)


def _parse_overrides(items: list[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for item in items:
        if "=" not in item:
            raise BPLError(f"--set 형식은 NAME=VALUE여야 합니다: {item}")
        name, raw = item.split("=", 1)
        name = name.strip()
        if not name:
            raise BPLError(f"변수 이름이 비어 있습니다: {item}")
        try:
            value = float(raw)
        except ValueError as exc:
            raise BPLError(f"숫자가 아닌 --set 값입니다: {item}") from exc
        result[name] = value
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bpl",
        description="BPL — Biological Programming Language reference interpreter",
        epilog="상세 문서는 소스 저장소의 docs/를 참조하고, 내장 예제는 bpl examples --export ./bpl-examples 로 내보내세요.",
    )
    parser.add_argument("--version", action="version", version=f"BPL {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="모델 파일의 문법과 구조를 검사합니다")
    validate.add_argument("model", type=Path)

    run = sub.add_parser("run", help="모델을 시뮬레이션합니다")
    run.add_argument("model", type=Path)
    run.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="초기 상태값 재정의")
    run.add_argument("--csv", type=Path, help="결과 CSV 파일 저장")
    run.add_argument("--json", type=Path, help="결과 JSON 파일 저장")
    run.add_argument("--table", action="store_true", help="결과 표를 터미널에 표시")

    describe = sub.add_parser("describe", help="모델의 구성요소와 상태 변수를 표시합니다")
    describe.add_argument("model", type=Path)

    examples = sub.add_parser("examples", help="설치 패키지에 포함된 예제 모델을 표시하거나 내보냅니다")
    examples.add_argument("--export", type=Path, help="예제 .bpl 파일을 지정 폴더로 복사")

    interact = sub.add_parser("interact", help="인구집단·반응 네트워크 모델을 검사하거나 실행합니다")
    interact_sub = interact.add_subparsers(dest="interact_command", required=True)
    interact_validate = interact_sub.add_parser("validate", help="상호작용 모델을 검사합니다")
    interact_validate.add_argument("model", type=Path)
    interact_run = interact_sub.add_parser("run", help="상호작용 모델을 시뮬레이션합니다")
    interact_run.add_argument("model", type=Path)
    interact_run.add_argument("--set-state", action="append", default=[], metavar="NAME=VALUE")
    interact_run.add_argument("--set-parameter", action="append", default=[], metavar="NAME=VALUE")
    interact_run.add_argument("--csv", type=Path, help="결과 CSV 저장")
    interact_run.add_argument("--json", type=Path, help="결과 JSON 저장")
    interact_run.add_argument("--table", action="store_true", help="결과 표 표시")
    return parser


def _describe(data: dict) -> None:
    print(f"모델: {data['model'].get('name', 'Untitled')}")
    print(f"버전: {data['model'].get('version', 'unspecified')}")
    print(f"상태: {data['model'].get('status', 'unspecified')}")
    sim = data["simulation"]
    print(f"시뮬레이션: {sim.get('start', 0)} → {sim.get('end', 0)} {sim.get('time_unit', '')} | step={sim.get('step', 1)} | solver={sim.get('integrator', 'euler')}")
    print("\n구성요소:")
    for comp in data.get("components", []):
        parent = comp.get("parent") or "(root)"
        print(f"  - {comp['id']} [{comp['level']}] parent={parent}")
    print("\n상태 변수:")
    for name, spec in data["states"].items():
        print(f"  - {name}: initial={spec['initial']} {spec.get('unit', '')} | range={spec.get('min', '-∞')}..{spec.get('max', '∞')}")
    print("\n파생 방정식:")
    for name, spec in data["equations"].items():
        print(f"  - {spec.get('output', name)} = {spec['expression']}")


def _print_rows(rows: list[dict[str, float]]) -> None:
    columns = list(rows[0].keys())
    widths = {col: max(len(col), *(len(f"{row[col]:.6g}") for row in rows)) for col in columns}
    print(" | ".join(col.ljust(widths[col]) for col in columns))
    print("-+-".join("-" * widths[col] for col in columns))
    display = rows if len(rows) <= 30 else rows[:15] + rows[-15:]
    for idx, row in enumerate(display):
        print(" | ".join(f"{row[col]:.6g}".ljust(widths[col]) for col in columns))
        if len(rows) > 30 and idx == 14:
            print("... (중간 행 생략; 전체 결과는 CSV/JSON 파일 참조)")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "examples":
            example_root = package_files("bpl").joinpath("examples")
            available = sorted(item for item in example_root.iterdir() if item.name.endswith(".bpl"))
            if args.export:
                args.export.mkdir(parents=True, exist_ok=True)
                for item in available:
                    target = args.export / item.name
                    with item.open("rb") as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
                print(f"예제 {len(available)}개를 내보냈습니다: {args.export}")
            else:
                print("BPL 내장 예제 모델:")
                for item in available:
                    print(f"  - {item.name}")
                print("\n예제 파일 내보내기: bpl examples --export ./bpl-examples")
            return 0

        if args.command == "interact":
            data = load_interaction_model(args.model)
            if args.interact_command == "validate":
                print(f"유효한 BPL 상호작용 모델입니다: {args.model}")
                print(f"상태 변수 {len(data['states'])}개 · 반응 {len(data['reactions'])}개 · 방정식 {len(data['equations'])}개")
                return 0
            state_overrides = _parse_overrides(args.set_state)
            parameter_overrides = _parse_overrides(args.set_parameter)
            rows = run_interaction_model(data, state_overrides, parameter_overrides)
            if args.csv:
                write_interaction_csv(rows, args.csv)
                print(f"CSV 저장: {args.csv}")
            if args.json:
                write_interaction_json(data, rows, args.json)
                print(f"JSON 저장: {args.json}")
            if args.table or (not args.csv and not args.json):
                print(f"\nBPL {__version__} INTERACTION | {data['model'].get('name', args.model.stem)}")
                print(f"실행 완료: {len(rows)}개 시점 | solver={data['simulation'].get('integrator', 'rk4')}")
                _print_rows(rows)
            return 0

        data = load_model(args.model)
        if args.command == "validate":
            print(f"유효한 BPL 모델입니다: {args.model}")
            print(f"구성요소 {len(data.get('components', []))}개 · 상태 변수 {len(data['states'])}개 · 방정식 {len(data['equations'])}개")
            return 0
        if args.command == "describe":
            _describe(data)
            return 0
        overrides = _parse_overrides(args.set)
        rows = run_model(data, overrides)
        if args.csv:
            write_csv(rows, args.csv)
            print(f"CSV 저장: {args.csv}")
        if args.json:
            write_json(data, rows, args.json)
            print(f"JSON 저장: {args.json}")
        if args.table or (not args.csv and not args.json):
            print(f"\nBPL {__version__} | {data['model'].get('name', args.model.stem)}")
            print(f"실행 완료: {len(rows)}개 시점 | solver={data['simulation'].get('integrator', 'euler')}")
            _print_rows(rows)
        return 0
    except BPLError as exc:
        print(f"BPL 오류: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"파일 오류: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
