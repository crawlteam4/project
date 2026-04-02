import subprocess
import sys
import os

# ────────────────────────────────────────────────────────────────────────────────
# 설정값 (프로젝트에 맞게 수정)
# ────────────────────────────────────────────────────────────────────────────────
ENV_NAME       = 'my_project'
PYTHON_VERSION = '3.14'
APP_FILE       = 'DDAS.py'
REQUIREMENTS   = [
    'streamlit',
    'pandas',
    'geopandas',
    'folium',
    'streamlit-folium',
    'scikit-learn',
    'shapely',
    'sqlalchemy',
    'pymysql',
    'numpy',
    'pyodbc',
    'plotly'
]


# ────────────────────────────────────────────────────────────────────────────────
# 명령어 실행
# ────────────────────────────────────────────────────────────────────────────────
def run_cmd(command):
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        encoding='cp949'
    )
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0 and result.stderr:
        print(f"❌ 오류: {result.stderr}")
    return result


# ────────────────────────────────────────────────────────────────────────────────
# 가상환경 목록 조회
# ────────────────────────────────────────────────────────────────────────────────
def get_env_list():
    result = run_cmd('conda env list')
    return [
        line.split()[0] for line in result.stdout.split('\n')
        if line.strip() and not line.startswith('#')
    ]


# ────────────────────────────────────────────────────────────────────────────────
# 설치된 패키지 목록 조회
# ────────────────────────────────────────────────────────────────────────────────
def get_package_list():
    result = run_cmd(f'conda run -n {ENV_NAME} pip list')
    lines  = [line for line in result.stdout.split('\n')[2:] if line.strip()]
    return [line.split()[0].lower() for line in lines]


# ────────────────────────────────────────────────────────────────────────────────
# 1단계: 가상환경 생성
# ────────────────────────────────────────────────────────────────────────────────
def step_create_env():
    print("\n[ 1단계 ] 가상환경 확인 중...")
    if ENV_NAME in get_env_list():
        print(f"  ✅ '{ENV_NAME}' 환경 이미 존재 → 스킵")
        return

    print(f"  🔨 '{ENV_NAME}' 환경 생성 중 (Python {PYTHON_VERSION})...")
    result = run_cmd(f'conda create -n {ENV_NAME} python={PYTHON_VERSION} -y')

    if result.returncode == 0:
        print(f"  ✅ '{ENV_NAME}' 환경 생성 완료")
    else:
        print(f"  ❌ 환경 생성 실패 → 종료")
        sys.exit(1)


# ────────────────────────────────────────────────────────────────────────────────
# 2단계: 패키지 설치
# ────────────────────────────────────────────────────────────────────────────────
def step_install_packages():
    print("\n[ 2단계 ] 패키지 설치 확인 중...")
    existing = get_package_list()

    to_install = [pkg for pkg in REQUIREMENTS if pkg.lower() not in existing]
    already    = [pkg for pkg in REQUIREMENTS if pkg.lower() in existing]

    if already:
        print(f"  ✅ 이미 설치됨 → 스킵: {', '.join(already)}")

    if not to_install:
        print("  ✅ 모든 패키지 설치 완료 상태")
        return

    pkg_str = ' '.join(to_install)
    print(f"  📦 설치 중: {', '.join(to_install)}")
    result = run_cmd(f'conda run -n {ENV_NAME} pip install {pkg_str}')

    if result.returncode == 0:
        print("  ✅ 패키지 설치 완료")
    else:
        print("  ❌ 패키지 설치 실패 → 종료")
        sys.exit(1)


# ────────────────────────────────────────────────────────────────────────────────
# 3단계: Streamlit 앱 실행
# ────────────────────────────────────────────────────────────────────────────────
def step_run_app():
    print(f"\n[ 3단계 ] '{APP_FILE}' 실행 중...")

    # app.py 파일 존재 여부 확인
    if not os.path.exists(APP_FILE):
        print(f"  ❌ '{APP_FILE}' 파일을 찾을 수 없습니다.")
        sys.exit(1)

    # Popen: run.py 종료 후에도 streamlit 유지
    subprocess.Popen(
        f'conda run -n {ENV_NAME} streamlit run {APP_FILE}',
        shell=True
    )
    print(f"  ✅ 앱 실행 완료 → 브라우저에서 확인하세요 (http://localhost:8501)")


# ────────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("  프로젝트 환경 설정 시작")
    print("=" * 50)

    ENV_NAME = input("가상환경 이름 입력: ").strip()
    if not ENV_NAME:
        print("환경 이름을 입력해주세요.")
        sys.exit(1)


    step_create_env()
    step_install_packages()
    step_run_app()

    print("\n" + "=" * 50)
    print("  모든 설정 완료")
    print("=" * 50)