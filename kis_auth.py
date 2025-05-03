"""
    Key, Secret 값을 이용해 ACCESS TOKEN 추출.
    이후 해당 값으로 움직이고자 함
"""
import os
from dotenv import load_dotenv

# .env 파일이 있는 경로를 지정합니다.
if os.name == 'posix':
    # macOS/Linux 환경에서 .env 파일 경로 설정
    dotenv_path = "/Users/etlers/Documents/env/.env"
else:
    # Windows 환경에서 .env 파일 경로 설정
    dotenv_path = "C:/Users/etlers/projects/env/.env"   
# 지정된 경로에 있는 .env 파일을 로드합니다.
load_dotenv(dotenv_path=dotenv_path, override=True)

# 투자주체
OWNER = 'ETLERS'
# 실계좌여부
PROD = 'Y'
# 실계좌
PROD_APP_KEY = os.getenv(f'PROD_APP_KEY_{OWNER}')
PROD_APP_SECRET = os.getenv(f'PROD_APP_SECRET_{OWNER}')
PROD_ACC_NO = os.getenv(f'PROD_ACC_NO_{OWNER}')
PROD_BASE_URL = "https://openapi.koreainvestment.com:9443"  # 실투자 서버 URL
# 모의투자
DEV_APP_KEY = os.getenv(f'DEV_APP_KEY_{OWNER}')
DEV_APP_SECRET = os.getenv(f'DEV_APP_SECRET_{OWNER}')
DEV_ACC_NO = os.getenv(f'DEV_ACC_NO_{OWNER}')
DEV_BASE_URL = "https://openapivts.koreainvestment.com:29443"  # 모의투자 서버 URL

# 매수수량
ORDER_QTY = "3"
# 대상 종목 - 에수금 기준 없음.
JONGMOK = '229200'  # 코스닥150(6백만)
JONGMOK_NM = '코스닥150'
# JONGMOK = '411060'
# JONGMOK_NM = '금현물'
# 예수금 천만원 이상이 있어야 함.
# JONGMOK = '122630'  # 코스피200 2X(레버리지)(14백만))
# JONGMOK_NM = '코스피200 2X(레버리지)'
# 슬랙 메세지 웹훅 주소
SLACK_WEBHOOK_URL = os.getenv(f'SLACK_WEBHOOK_URL_{OWNER}')