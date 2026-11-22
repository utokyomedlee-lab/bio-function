# BPL 0.3.0 — Biological Programming Language

BPL은 생물학적 모델을 `.bpl` 파일로 선언하고 시간에 따른 상태 변화를 계산하는 연구용 프로토타입 언어입니다.

## 핵심 기능

- 안전한 산술 표현식 평가기 (임의 Python 코드 실행 불가)
- 시간 의존 상태 방정식과 Euler / RK4 적분기
- 개체·장기·조직·세포·세포소기관·분자 계층 선언
- 반응 네트워크 엔진: 반응 flux와 stoichiometry로 상태 변화 계산
- 생물학적 모델 검증 및 상태·매개변수 범위 검사
- CSV / JSON 결과 내보내기

## 설치

Python 3.11 이상에서 PyPI 공개 후 다음 명령으로 설치합니다.

```bash
python -m pip install bpl-biosim
```

소스 코드를 내려받아 개발하려면 프로젝트 폴더에서 다음을 실행합니다.

```bash
python -m pip install -e .[dev]
```

설치 패키지에 포함된 예제 모델을 현재 폴더로 내보냅니다.

```bash
bpl examples --export ./bpl-examples
```

## 기본 모델 실행

기본 ODE 모델:

```bash
bpl validate ./bpl-examples/aging_system.bpl
bpl run ./bpl-examples/aging_system.bpl --csv aging.csv --json aging.json
```

반응 네트워크 상호작용 모델:

```bash
bpl interact validate ./bpl-examples/senescence_immune_lysosome.bpl
bpl interact run ./bpl-examples/senescence_immune_lysosome.bpl --table
bpl interact run ./bpl-examples/senescence_immune_lysosome.bpl --csv interaction.csv --json interaction.json
```

면역 제거 비율 시나리오 변경:

```bash
bpl interact run ./bpl-examples/senescence_immune_lysosome.bpl --set-parameter immune_clearance_fraction=0.5 --csv scenario.csv
```

상태 초기값 변경:

```bash
bpl interact run ./bpl-examples/senescence_immune_lysosome.bpl --set-state senescent_cells=1.4 --csv scenario.csv
```

## BPL 반응 네트워크 형식

`.bpl` 파일은 TOML 호환 문법을 사용합니다. 예를 들어:

```toml
[parameters]
clearance_rate = 0.08
immune_fraction = 0.35

[states.senescent_cells]
initial = 1.0
unit = "relative"
min = 0.0

[reactions.immune_clearance]
rate = "clearance_rate * immune_fraction * senescent_cells"
stoichiometry = { senescent_cells = -1.0 }
```

`rate`는 0 이상의 정방향 flux이며, `stoichiometry`는 각 state의 변화 계수를 나타냅니다. 역방향 반응은 별도 reaction으로 정의합니다. 반응 속도 상수와 state 단위의 차원 일관성은 모델 작성자가 확인해야 합니다. 현재 버전은 완전한 단위 대수/차원 분석기를 제공하지 않습니다.

## 노화 모델에 대한 주의

`examples/aging_system.bpl`과 `examples/senescence_immune_lysosome.bpl`의 계수와 초기값은 소프트웨어 기능 시연을 위한 가상값입니다. 인체 연령별 실측 평균이나 임상적으로 검증된 매개변수가 아닙니다.

BPL은 개발자의 원본 노화도 식과 면역 제거 비율 해석을 위한 수정 후보식을 별개로 계산합니다. 두 식의 생물학적 타당성은 실제 측정 데이터로 검증해야 합니다. 특히 면역 제거 비율 `i`는 측정 시간 구간과 실험 정의가 모델에 명시되어야 합니다.

## 현재 범위와 한계

BPL 0.3은 well-mixed population / reaction network 엔진을 제공합니다. 개별 세포 에이전트, 세포 간 공간적 거리, 2D/3D 조직, 장기 간 생리학적 피드백 및 임상 예측 기능은 아직 구현되지 않았습니다. 계층 선언은 모델 구조 메타데이터이며, 그 자체로 생물학적 과정의 자동 실행을 의미하지 않습니다.

## 개발자 명령

```bash
python -m unittest discover -s tests -v
python -m bpl --version
```

MIT License — 저작권자 표기와 라이선스 전문을 배포본에 유지하세요.
