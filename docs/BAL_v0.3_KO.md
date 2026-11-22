# BAL v0.3 — 다중 구획 동역학 엔진

BAL v0.3은 BAL 비선형 지수 커널을 장 흡수, 간 대사, 혈중 분포, 조직 전달 및 내성 동역학과 결합한 연구용 시뮬레이터입니다. PK에서 영감을 얻은 질량 구획 모델이며 임상적으로 검증된 약동학 모델이나 용량 권고 도구가 아닙니다.

## 상태변수
- D: DDS 제형/방출 저장소
- G: 장관 내 약물량
- H: 간 구획 약물량
- P: 혈장 구획 약물량
- T: 조직 구획 약물량
- L_gut, L_hep, L_sys, L_tissue: 각 단계의 누적 손실/대사량
- b: BAL 기저 저항/내성 상태

## DDS 방출
초기 방출 버스트가 감소하는 1차 방출률:
`k_rel(t) = k_release * (1 + release_burst * exp(-t / burst_tau))`
`dD/dt = -k_rel(t) * D`

## 구획 동역학
`dG/dt = k_rel(t)D - (k_abs + k_gut_deg)G`

`dH/dt = k_abs G - (k_hep_met + k_hep_to_plasma)H`

`dP/dt = k_hep_to_plasma H - k_pt P + k_tp T - k_sys_clear P`

`dT/dt = k_pt P - (k_tp + k_tissue_clear)T`

제거/대사 항은 누적 손실 상태에 더해 전체 투여량의 질량수지를 검증합니다.

## 간 초회통과율 근사
간 구획에서 대사와 혈장 유입이 경쟁하는 1차 제거 경로라고 가정하면:
`m_eff = k_hep_met / (k_hep_met + k_hep_to_plasma)`

`1 - m_eff`는 단순 경쟁위험 근사에서 혈장 유입으로 빠져나가는 비율입니다. 실제 간 추출률의 완전한 생리학적 모델은 아닙니다.

## BAL 코어와 조직 노출 가중 내성
`y_core(t) = ln(1 + alpha*a*(1-m_eff)) / ln(1 + beta*b(t))`

`E_tissue(t) = T / (T + tissue_reference)`

`db/dt = gamma * y_core(t) * E_tissue(t) - tolerance_recovery * (b(t) - b0)`

`y_core`는 기존 BAL 정규화 모델을 유지합니다. `y_core * E_tissue`는 조직 노출로 가중한 보조 지표입니다. 기존 임계 조건은 코어 지수에 대해 `alpha*a*(1-m_eff) > beta*b`이며, 등호는 임계 경계입니다.

초기 조건이 `b(0)=b0`이고 입력이 비음수이면 연속 방정식에서 `b(t) >= b0`인 영역은 불변입니다.

## 질량수지
`D + G + H + P + T + L_gut + L_hep + L_sys + L_tissue = initial_dose`

연속계의 각 유량은 한 구획의 감소와 다른 구획/손실 상태의 동일한 증가로 짝지어져 총량을 보존합니다. 수치 오차는 `max_mass_balance_error`로 보고합니다.

## 수치 방법
고정 시간 간격의 classical RK4를 사용합니다. RK4는 임의로 큰 시간 간격에서 양성을 보장하지 않으므로, 물질 구획이 유의하게 음수가 되면 오류를 발생시키고 더 작은 `dt`를 요구합니다.

## 실행
```bash
python -m pip install -e .
bal-sim --config examples/bal_multicompartment.json
python -m unittest discover -s tests -v
```

## 불확실성 분석
JSON 설정의 `uncertainty.ranges`에 파라미터별 `[low, high]`를 지정하면 균등분포 시나리오 표본을 만듭니다. 평균 및 5/50/95 백분위수를 요약합니다. 이 범위는 사용자가 지정한 시나리오 경계이며 실험에서 추정한 확률분포가 아닙니다.

## 모델 범위와 제한
1. 구획은 well-mixed이며 공간적 농도 구배를 표현하지 않습니다.
2. 구획 변수는 농도가 아닌 양(amount)이며, 단위 체계는 사용자 정의입니다.
3. 간 대사는 선형 1차 경로이며 효소 포화, 수송체 포화, 장내 미생물 대사는 포함하지 않습니다.
4. 내성은 하나의 현상론적 상태변수이며 수용체 내성, 면역반응, 유전자 조절과 동일시하지 않습니다.
5. 매개변수는 소프트웨어 시연용 가상값입니다. 실측 데이터 적합 및 외부 검증 전에는 생체이용률, 치료 유효성 또는 임상 용량으로 해석할 수 없습니다.
