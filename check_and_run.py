import datetime
import holidays
import subprocess
import os
import argparse

# 인자를 받아서 처리. 없으면 등록된 것으로
# 여러개를 돌릴때 사용하고자 함
parser = argparse.ArgumentParser(description="투자주체 확인")
parser.add_argument("--owner", help="투자 주체")
args = parser.parse_args()

owner = args.owner.upper() if args.owner else "SOOJIN"

# 오늘 날짜
today = datetime.date.today()
kr_holidays = holidays.KR()

# 로그 파일 경로 설정
log_dir = f"/Users/etlers/Documents/kis_account/logs/{owner}"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"cron_{today.strftime('%Y%m%d')}.log")

# 공휴일이 아니면 main.py 실행
if today not in kr_holidays:
    with open(log_file, "a") as f:
        subprocess.run(
            ["/Library/Frameworks/Python.framework/Versions/3.11/bin/python3", f"/Users/etlers/Documents/kis_account/main.py --owner {owner}"],
            stdout=f,
            stderr=subprocess.STDOUT
        )
