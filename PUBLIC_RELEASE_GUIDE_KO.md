# BPL 0.3.0 공개 배포 안내서

이 저장소는 BPL 0.3.0의 소스 코드와 예제, 테스트를 보관합니다.

- GitHub 저장소: https://github.com/utokyomedlee-lab/bio-function
- PyPI 배포 이름(예정): `bpl-biosim`
- Python import: `bpl`
- CLI 명령: `bpl`
- 지원 Python: 3.11 이상
- 현재 버전: 0.3.0
- 라이선스: MIT (권리자 표기 확인 필요)

## 공개 전 권리 및 라이선스 확인

현재 LICENSE 및 package metadata의 저작권자 표기는 `BPL Project`입니다. 실제 권리자 정보와 일치하는지 확인하고 필요하면 수정하세요. MIT 라이선스는 소프트웨어의 재사용·수정·재배포·상업적 이용을 허용합니다. 이 조건에 동의하는 경우에만 공개하세요.

모든 예제 매개변수는 기능 시연을 위한 가상값입니다. 실제 인체 연령별 평균, 임상 기준 또는 검증된 생물학 상수로 해석하지 마세요.

## 로컬 설치 및 실행

저장소를 clone한 다음 프로젝트 루트에서 실행합니다.

```bash
git clone https://github.com/utokyomedlee-lab/bio-function.git
cd bio-function
python -m pip install .
bpl --version
bpl examples --export ./bpl-examples
bpl validate ./bpl-examples/aging_system.bpl
bpl run ./bpl-examples/aging_system.bpl --csv aging.csv
bpl interact validate ./bpl-examples/senescence_immune_lysosome.bpl
bpl interact run ./bpl-examples/senescence_immune_lysosome.bpl --csv interaction.csv
```

테스트:

```bash
python -m unittest discover -s tests -v
```

## PyPI Trusted Publishing 설정

1. https://pypi.org/account/register/ 에서 PyPI 계정을 만들고 이메일을 확인합니다.
2. 2단계 인증을 켭니다.
3. 첫 게시 전에 https://pypi.org/manage/account/publishing/ 을 열고 GitHub Trusted Publisher의 pending publisher를 등록합니다.
4. 다음 값을 입력합니다.

| 설정 | 값 |
|---|---|
| PyPI project name | `bpl-biosim` |
| GitHub owner | `utokyomedlee-lab` |
| Repository name | `bio-function` |
| Workflow filename | `publish-to-pypi.yml` |
| Environment name | `pypi` |

5. GitHub 저장소의 Settings → Environments에서 `pypi` 환경을 생성합니다. 가능하면 배포 승인 보호 규칙을 설정합니다.
6. PyPI에서 프로젝트 이름이 이미 사용 중인지 게시 직전에 확인합니다. Pending Publisher는 프로젝트 이름을 예약하지 않습니다.

PyPI 계정과 GitHub 저장소의 Trusted Publisher 정보가 정확히 일치해야 합니다.

## 첫 공개 릴리스

1. `pyproject.toml`과 `bpl/__init__.py`의 버전이 모두 `0.3.0`인지 확인합니다.
2. GitHub 저장소에서 Releases → Create a new release를 선택합니다.
3. 태그를 `v0.3.0`으로 설정합니다.
4. 릴리스 제목을 `BPL 0.3.0`으로 작성하고 게시합니다.
5. Actions 탭에서 `Publish BPL to PyPI` workflow를 확인합니다.

워크플로는 Python 3.11/3.12/3.13 테스트, 예제 검증, 버전 태그 검사, wheel/sdist 빌드, Twine 메타데이터 검사 후 OIDC Trusted Publishing으로 PyPI 업로드를 시도합니다.

## 설치

PyPI 첫 게시가 성공한 뒤 사용자는 다음 명령으로 설치할 수 있습니다.

```bash
python -m pip install bpl-biosim
bpl --version
bpl examples --export ./bpl-examples
```

## 과학적 범위

BPL 0.3은 ODE 모델 실행기와 well-mixed population/reaction-network 엔진을 제공하는 연구용 프로토타입입니다. 개별 세포 에이전트, 공간적 2D/3D 조직, 장기 생리학 통합, 임상 예측 기능은 구현되어 있지 않습니다. 모든 모델은 실험 데이터로 보정하고 독립적인 실험으로 검증해야 합니다.
