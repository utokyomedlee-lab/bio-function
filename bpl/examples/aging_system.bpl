# BPL 0.3 — 다중 계층 노화 모델 예제
# 아래 초기값과 변화율은 언어 실행을 보여주기 위한 가정값입니다.

[model]
name = "BPL Aging System Demonstrator"
version = "0.3.0"
purpose = "노화세포 부담, 면역 제거율, 리소좀 분해능력의 시간 변화를 시험"
status = "illustrative_simulation"
author = "BPL example"

[simulation]
start = 0.0
end = 10.0
step = 0.25
time_unit = "year"
integrator = "rk4"

[[components]]
id = "human_model"
level = "organism"
parent = ""
description = "전체 개체를 나타내는 모델 루트"

[[components]]
id = "skin"
level = "organ"
parent = "human_model"
description = "예시 피부 장기 구획"

[[components]]
id = "skin_tissue"
level = "tissue"
parent = "skin"
description = "피부 조직 구획"

[[components]]
id = "senescent_cells"
level = "cell"
parent = "skin_tissue"
description = "노화세포 집단의 상대 부담"

[[components]]
id = "lysosome"
level = "organelle"
parent = "senescent_cells"
description = "노화 관련 단백질 및 손상 소기관의 세포 내 분해"

[[components]]
id = "damaged_protein_pool"
level = "molecule"
parent = "lysosome"
description = "분해 대상 분자 풀을 개념적으로 표시"

[[components]]
id = "immune_system"
level = "organ"
parent = "human_model"
description = "면역 제거 기능을 나타내는 시스템 구획"

[constants]
senescence_growth = 0.025
immune_decline = 0.002
lysosome_relaxation = 0.015
lysosome_floor = 0.55

[states.x]
initial = 1.0
unit = "relative_to_reference"
min = 0.0
rate = "senescence_growth * x"
description = "노화세포의 상대적 축적 부담; 기준값 1"

[states.i]
initial = 0.35
unit = "fraction"
min = 0.0
max = 1.0
rate = "-immune_decline * i"
description = "면역 제거 비율의 예시 상태"

[states.L]
initial = 1.0
unit = "relative_to_reference"
min = 0.0001
rate = "-lysosome_relaxation * (L - lysosome_floor)"
description = "리소좀 분해능력의 상대값; 기준값 1"

[equations.aging_original]
output = "y_original"
expression = "ln(1 + x - i) / ln(1 + L)"
description = "원식. x와 i가 동일 척도라는 전제가 필요"

[equations.aging_clearance_adjusted]
output = "y_candidate"
expression = "ln(1 + x * (1 - i)) / ln(1 + L)"
description = "i를 제거 비율로 해석한 후보식. 생물학적 검증 전"
