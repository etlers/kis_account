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
    dict_info = {
        'ETLERS':'60',
        # 'SOOJIN':'3',
    }

    # 시작
    while True:
        # 현재시각
        now_dtm = CF.get_current_time().split(' ')[1]
        # 8시 20분 장전 시간외거래 이전 대기
        if now_dtm < '082000':
            time.sleep(0.5)
            continue

        for owner, qty in dict_info.items():
            print(owner, qty)
            for dict_value in config["accounts"]:
                if dict_value['owner'] == owner:
                    dict_account = dict_value
                    # 장전거래, 어제 종가
                    if TR.buy_stock(dict_account, qty, '05'):
                        dict_buy_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매수')
                        AVG_WHOLE_BUYING = dict_buy_avg_prc['last_deal_avg_prc']
                        CF.send_slack_alert("BUY", dict_account, qty, AVG_WHOLE_BUYING, '', '주문성공')
                        print(f"{owner} : {AVG_WHOLE_BUYING:,}")
                break
            break
                    