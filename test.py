"""
    입력받은 계정으로 매매
"""
import time, os
import argparse
import polars as pl
import statistics as stats

import param_value as PV  # 파라미터 정보
import trader as TR  # Transaction 정보
import com_func as CF  # 공통함수


# 입력받은 인자 추출
parser = argparse.ArgumentParser(description="투자주체 확인")
parser.add_argument("--owner", help="투자 주체")
args = parser.parse_args()
# 계정을 확인 후 없으면 종료
run_break = False
if args.owner is None:
    print("계정을 입력 해야함!!!")
    run_break = True


# 투자자 거래정보
dict_value = CF.get_owner_config(args.owner)
# 인자로 받은 계정으로 설정
APP_KEY = dict_value['app_key']
APP_SECRET = dict_value['app_secret']
ACC_NO = dict_value['account_number']
ORDER_QTY = dict_value['order_qty']
SLACK_WEBHOOK_URL = dict_value['slack_webhook_url']
# 거래 URL
BASE_URL = PV.BASE_URL_DEV if args.owner == 'DEV' else PV.BASE_URL_PROD
# 토큰은 시작에서 한번만.
TOKEN_OWNER = args.owner.split("_")[0]
print(TOKEN_OWNER)
# TOKEN = CF.get_token(TOKEN_OWNER, BASE_URL, APP_KEY, APP_SECRET)