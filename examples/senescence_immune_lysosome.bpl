# BPL 0.3 — 노화세포·면역 제거·리소좀 분해 상호작용 예제
# 모든 숫자와 속도상수는 언어 기능 시연용 가상값입니다.

[model]
name = "Senescence-Immune-Lysosome Interaction Demonstrator"
version = "0.3.0"
purpose = "노화세포 축적, 면역 제거 및 리소좀 분해의 결합 반응망을 시험"
status = "illustrative_simulation"

[simulation]
start = 0.0
end = 50.0
step = 0.25
time_unit = "year"
integrator = "rk4"

[parameters]
senescence_input_rate = 0.080
immune_clearance_rate = 0.080
immune_clearance_fraction = 0.35
damage_production_rate = 0.040
lysosome_degradation_rate = 0.120
lysosome_km = 0.30
lysosome_decline_rate = 0.006
lysosome_recovery_rate = 0.020
senescent_reference = 1.0
lysosomal_reference = 1.0

[parameter_bounds.immune_clearance_fraction]
min = 0.0
max = 1.0

[states.senescent_cells]
initial = 1.0
unit = "relative_to_reference"
min = 0.0
description = "노화세포 상대 부담"

[states.healthy_protein_pool]
initial = 1.0
unit = "relative_pool"
min = 0.0
description = "손상되지 않은 단백질 풀의 가상 상대량"

[states.damaged_protein_pool]
initial = 1.0
unit = "relative_pool"
min = 0.0
description = "분해 대상 손상 단백질 풀의 가상 상대량"

[states.lysosomal_capacity]
initial = 1.0
unit = "relative_to_reference"
min = 0.0001
max = 1.2
description = "리소좀의 기능적 분해능력 상대값"

[states.recycled_material]
initial = 0.0
unit = "relative_pool"
min = 0.0
description = "리소좀 분해 후 회수된 물질의 가상 풀"

[reactions.senescence_input]
rate = "senescence_input_rate / (1 + 0.25 * senescent_cells)"
stoichiometry = { senescent_cells = 1.0 }
description = "노화세포 부담의 지속 유입을 나타내는 가상 flux"

[reactions.immune_clearance]
rate = "immune_clearance_rate * immune_clearance_fraction * senescent_cells"
stoichiometry = { senescent_cells = -1.0 }
description = "면역 제거능력에 따른 노화세포 부담 감소"

[reactions.protein_damage]
rate = "damage_production_rate * healthy_protein_pool"
stoichiometry = { healthy_protein_pool = -1.0, damaged_protein_pool = 1.0 }
description = "건강한 단백질 풀이 손상 단백질 풀로 이동"

[reactions.lysosomal_degradation]
rate = "lysosome_degradation_rate * lysosomal_capacity * damaged_protein_pool / (lysosome_km + damaged_protein_pool)"
stoichiometry = { damaged_protein_pool = -1.0, recycled_material = 1.0 }
description = "리소좀 분해능력에 따른 손상 단백질 처리"

[reactions.lysosome_decline]
rate = "lysosome_decline_rate * lysosomal_capacity"
stoichiometry = { lysosomal_capacity = -1.0 }
description = "리소좀 분해능력 저하를 나타내는 가상 flux"

[reactions.lysosome_recovery]
rate = "lysosome_recovery_rate * max(0, 0.8 - lysosomal_capacity)"
stoichiometry = { lysosomal_capacity = 1.0 }
description = "리소좀 분해능력 회복을 나타내는 가상 flux"

[equations.x_relative]
output = "x"
expression = "senescent_cells / senescent_reference"

[equations.i_fraction]
output = "i"
expression = "immune_clearance_fraction"

[equations.L_relative]
output = "L"
expression = "lysosomal_capacity / lysosomal_reference"

[equations.aging_original]
output = "y_original"
expression = "ln(1 + senescent_cells / senescent_reference - immune_clearance_fraction) / ln(1 + lysosomal_capacity / lysosomal_reference)"

[equations.aging_clearance_candidate]
output = "y_candidate"
expression = "ln(1 + (senescent_cells / senescent_reference) * (1 - immune_clearance_fraction)) / ln(1 + lysosomal_capacity / lysosomal_reference)"
