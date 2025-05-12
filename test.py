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


# 투자자 거래정보
dict_value = CF.get_owner_config("SOOJIN")
# 인자로 받은 계정으로 설정
APP_KEY = dict_value['app_key']
APP_SECRET = dict_value['app_secret']
ACC_NO = dict_value['account_number']
ORDER_QTY = dict_value['order_qty']
SLACK_WEBHOOK_URL = dict_value['slack_webhook_url']
# 거래 URL
BASE_URL = PV.BASE_URL_DEV if "SOOJIN" == 'DEV' else PV.BASE_URL_PROD
# 토큰은 시작에서 한번만. 있으면 삭제하고 다시 만듬
TOKEN = CF.get_token("SOOJIN", BASE_URL, APP_KEY, APP_SECRET)

# 거래를 위한 인자 딕셔너리
dict_param_deal = {
    'start_date':PV.start_date,
    'end_date':PV.end_date,
    'OWNER':"SOOJIN",
    'BASE_URL':BASE_URL,
    'APP_KEY':APP_KEY,
    'APP_SECRET':APP_SECRET,
    'ACC_NO':ACC_NO,
    'ACNT_PRDT_CD':'01',
    'TOKEN':TOKEN,
    'STOCK_CD':PV.STOCK_CD,
    'STOCK_NM':PV.STOCK_NM,
    'ORDER_QTY':ORDER_QTY,
    'slack_msg':'',
    'SLACK_WEBHOOK_URL':SLACK_WEBHOOK_URL,
    'preday_close_price':PV.preday_close_price,
}

# 매도, 매수 평균 금액 최신화
sell_avg_prc, buy_avg_prc = CF.get_account_data('AVG', dict_param_deal)

print(sell_avg_prc, buy_avg_prc)