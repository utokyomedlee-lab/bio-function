# BPL 0.3 — 조직 손상 및 회복의 단순 예시
# 모든 계수는 가상의 교육·소프트웨어 테스트용 값입니다.

[model]
name = "Tissue Repair Toy Model"
version = "0.3.0"
purpose = "조직 손상, 염증 부하, 회복 세포 집단의 결합 동역학 예시"
status = "illustrative_simulation"

[simulation]
start = 0.0
end = 20.0
step = 0.2
time_unit = "day"
integrator = "rk4"

[[components]]
id = "organism"
level = "organism"
parent = ""
description = "모델 개체"

[[components]]
id = "wound_site"
level = "organ"
parent = "organism"
description = "국소 손상 부위의 개념적 구획"

[[components]]
id = "wound_tissue"
level = "tissue"
parent = "wound_site"
description = "손상 및 회복이 진행되는 조직"

[[components]]
id = "repair_cells"
level = "cell"
parent = "wound_tissue"
description = "회복 관련 세포 집단의 상대 수준"

[[components]]
id = "signaling_molecules"
level = "molecule"
parent = "wound_tissue"
description = "염증 및 회복 신호를 요약한 분자 구획"

[constants]
repair_rate = 0.08
cell_growth = 0.12
cell_capacity = 5.0
inflammation_production = 0.25
inflammation_decay = 0.20

[states.injury]
initial = 1.0
unit = "fraction_of_initial_injury"
min = 0.0
max = 1.0
rate = "-repair_rate * repair_cells * injury / cell_capacity"
description = "초기 손상 대비 잔존 손상 비율"

[states.repair_cells]
initial = 1.0
unit = "relative_population"
min = 0.0
max = 5.0
rate = "cell_growth * repair_cells * (1 - repair_cells / cell_capacity) * (0.2 + injury)"
description = "회복 관련 세포 집단의 개념적 상대 수준"

[states.inflammation]
initial = 0.2
unit = "relative_signal"
min = 0.0
rate = "inflammation_production * injury - inflammation_decay * inflammation"
description = "조직의 염증 신호 부하를 나타내는 단순 상태 변수"

[equations.tissue_integrity]
output = "integrity_proxy"
expression = "1 - injury"

[equations.repair_balance]
output = "repair_inflammation_balance"
expression = "repair_cells / (1 + inflammation)"
