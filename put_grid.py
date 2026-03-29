import os
import shutil
from pathlib import Path

# ───────────────────────────────────────────────
# ★ 설정: 이동할 목적지 폴더를 여기에 입력하세요
TARGET_FOLDER = "C:/crawling/test/project/data/grid/"
# ───────────────────────────────────────────────

DOWNLOADS = Path.home() / "Downloads"

def move_grid_csvs():
    target = Path(TARGET_FOLDER)

    # 목적지 폴더 없으면 자동 생성
    target.mkdir(parents=True, exist_ok=True)

    # Downloads에서 grid_ 로 시작하는 .csv 파일 탐색
    csv_files = list(DOWNLOADS.glob("grid_*.csv"))

    if not csv_files:
        print("⚠  Downloads 폴더에 grid_*.csv 파일이 없습니다.")
        return

    print(f"📂 이동 대상 폴더: {target}\n")

    moved = 0
    for f in csv_files:
        dest = target / f.name

        # 같은 이름 파일이 이미 있으면 덮어쓸지 확인
        if dest.exists():
            answer = input(f"  ⚠  '{f.name}' 이(가) 이미 존재합니다. 덮어쓸까요? (y/n): ").strip().lower()
            if answer != "y":
                print(f"  ⏭  건너뜀: {f.name}")
                continue

        shutil.move(str(f), str(dest))
        print(f"  ✅ 이동 완료: {f.name}")
        moved += 1

    print(f"\n총 {moved}개 파일 이동 완료.")

if __name__ == "__main__":
    move_grid_csvs()
    input("\n[Enter] 키를 누르면 창이 닫힙니다...")