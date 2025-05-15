import datetime
import holidays
import subprocess
import os
import com_func as CF

# 오늘 날짜
today = datetime.date.today()
kr_holidays = holidays.KR()

# 로그 파일 경로 설정
log_dir = "/Users/etlers/Documents/kis_account/logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"cron_{today.strftime('%Y%m%d')}.log")

# 공휴일이 아니면 main.py 실행
if today not in kr_holidays:
    with open(log_file, "a") as f:
        subprocess.run(
            [
                "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3", 
                "/Users/etlers/Documents/kis_account/deal_account.py",
                " --owner",
                "SOOJIN"
            ],
            stdout=f,
            stderr=subprocess.STDOUT
        )
        