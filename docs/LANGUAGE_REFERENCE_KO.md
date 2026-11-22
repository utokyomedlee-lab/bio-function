# BPL 0.3 언어 명세서 (초기 참조 구현)

BPL 0.3은 Python 3.11+ 표준 라이브러리의 TOML 파서와 안전한 산술식 평가기를 사용하는 연구용 프로토타입입니다. 파일 확장자는 `.bpl`이며, 파일 내용은 TOML 호환 문법입니다.

## 모델 기본 구조

기본 ODE 모델은 다음 섹션을 사용합니다.

- `[model]`: 모델 이름, 버전 및 상태 설명
- `[simulation]`: 시작/종료 시간, 시간 간격, 적분기, 시간 단위
- `[constants]`: 시간에 따라 변하지 않는 숫자 매개변수
- `[states.NAME]`: 동적 상태 변수
- `[equations.NAME]`: 출력용 파생 수식
- `[[components]]`: 생물학적 계층을 설명하는 메타데이터

## 계층 메타데이터

지원 계층: `organism`, `organ`, `tissue`, `cell`, `organelle`, `molecule`.

각 구성요소는 고유한 `id`, `level`, 선택적 `parent`, 설명을 가집니다. 계층은 구조를 선언하고 검사하는 메타데이터이며, 부모가 자식의 상태를 자동 소유하거나 개별 세포 인스턴스를 생성하지는 않습니다.

## 상태 변수

```toml
[states.cell_damage]
initial = 0.2
unit = "fraction"
min = 0.0
max = 1.0
rate = "damage_input - repair_rate * cell_damage"
description = "손상 부하"
```

- `initial`: 필수 숫자
- `unit`: 현재는 설명 라벨이며 자동 단위 변환을 하지 않음
- `min`, `max`: 선택적 허용 범위
- `rate`: 상태와 상수, `t`를 사용하는 시간 변화율
- `description`: 생물학적 의미 설명

변화식은 `d(state)/dt = rate`로 해석합니다.

## 수식 문법

허용 연산자: `+`, `-`, `*`, `/`, `**`, `%`, 단항 `+`, 단항 `-`, 괄호.

허용 함수:

| 함수 | 의미 |
|---|---|
| `ln(x)`, `log(x)` | 자연로그 |
| `exp(x)` | 자연 지수함수 |
| `sqrt(x)` | 제곱근 |
| `abs(x)` | 절댓값 |
| `min(x, ...)`, `max(x, ...)` | 최솟값·최댓값 |
| `clip(x, lo, hi)` | 값 제한 |

Python 속성 접근, 인덱싱, import, 반복문, 함수 정의, 파일 및 네트워크 작업은 지원하지 않습니다.

## 수치 적분

- `euler`: 명시적 전진 오일러법
- `rk4`: 고전적 4차 Runge–Kutta법

강성, 불연속, 확률성, 지연 효과에 대해 자동으로 적합성을 보장하지 않습니다. 시간 간격을 바꾸어 수렴성과 민감도를 확인해야 합니다.

## 반응 네트워크 모델

BPL 0.3은 다음 명령을 추가합니다.

```bash
bpl interact validate model.bpl
bpl interact run model.bpl --csv result.csv
```

필수 섹션:

- `[model]`
- `[simulation]`
- `[parameters]`
- `[states.*]`
- `[reactions.*]`
- `[equations.*]`

각 반응은 0 이상의 flux 식 `rate`와 상태 변화 계수 `stoichiometry`를 가집니다. 상태 변화율은 각 반응의 계수와 flux의 곱을 합산해 계산합니다. 역방향 반응은 별도 반응으로 작성합니다.

## 과학적 범위

현재 반응 네트워크는 well-mixed 집단 모델입니다. 개별 세포 행위자, 공간 확산, 2D/3D 조직, 장기 생리학 또는 임상 예측을 구현하지 않습니다. 모든 예제 매개변수는 시연용 가상값이며 실험 데이터로 보정하고 독립 검증해야 합니다.
