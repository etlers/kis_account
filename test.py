import json, time, os
import multiprocessing
import trader as TR
import com_func as CF
import polars as pl
import argparse


# 여러개를 돌릴때 사용하고자 함
parser = argparse.ArgumentParser(description="투자주체 확인")
parser.add_argument("--owner", help="투자 주체")
args = parser.parse_args()


# 거래에 관련한 모든 정보
with open("../env/config.json", "r") as f:
    config = json.load(f)
# 계정정보를 기본 이틀러스로 아니면 인자로 받은 계정으로 설정
owner = args.owner.upper() if args.owner else "DEV"
for dict_value in config["accounts"]:
    if dict_value['owner'] == owner:
        dict_account = dict_value
        break

# 일자 파라미터. 당일
start_date = CF.get_current_time().split(' ')[0]
end_date   = CF.get_current_time().split(' ')[0]


# 거래 시작
# tail -f /Users/etlers/Documents/kis_account/cron_$(date +%Y%m%d).log
if __name__ == '__main__':
    # if TR.sell_stock(dict_account, '1'):
    #     # 직전 매도 평균
    # dict_sell_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매수')
    # print(dict_account)
    dict_result = TR.get_stock_info(dict_account, alarm='N')
    print(dict_result)
    dict_result = TR.get_deposit(dict_account)
    print(dict_result)
                    