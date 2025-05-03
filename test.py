"""
    입력받은 계정으로 매매
"""
import json, time, os
import argparse
import trader as TR
import com_func as CF
import polars as pl
import statistics as stats

import deal_multi as DM

# 입력받은 인자 추출
parser = argparse.ArgumentParser(description="투자주체 확인")
parser.add_argument("--owner", help="투자 주체")
args = parser.parse_args()

run_break = False
if args.owner is None:
    print("계정을 입력 해야함!!!")
    run_break = True

# 종목, OPEN API URL
STOCK_CD = "229200"
STOCK_NM = "KODEX 150 ETF"
BASE_URL = "https://openapivts.koreainvestment.com:29443" if args.owner == 'DEV' else "https://openapi.koreainvestment.com:9443"

# 시각 정의
START_DEAL_TM = '090000'
END_DEAL_TM = '151500'
START_TM_BUY = '091500'  # 매수 시작 시간 기준
EARLY_BUY_CHK_TM = '090300'  # 장초반 급상승 체크 시간

# 시세 데이터의 저장
LIST_SISE_PRICE = []
df_sise = pl.DataFrame([])

# 직전 거래일 정보 확인
dict_last_info = CF.get_previous_trading_info(STOCK_CD)
preday_updn_rt = dict_last_info['change_percent']  # 전일대비 상승하락 비율
preday_close_price = int(dict_last_info['close_price'])  # 전일 종가
preday_result_msg = f"# 전일 종가: {preday_close_price:,}원, 전일대비 상승률: {preday_updn_rt}%"
print('#' * 120)
print(preday_result_msg)
print('#' * 120)

# 거래에 관련한 모든 정보
with open("../env/config.json", "r") as f:
    config = json.load(f)
# 인자로 받은 계정으로 설정
for dict_value in config["accounts"]:
    if dict_value['owner'] != args.owner:
        continue
    # 로직에서 사용하게 되는 계정정보
    APP_KEY = dict_value['app_key']
    APP_SECRET = dict_value['app_secret']
    ACC_NO = dict_value['account_number']
    ORDER_QTY = dict_value['order_qty']
    SLACK_WEBHOOK_URL = dict_value['slack_webhook_url']
    # 토큰은 시작에서 한번만
    TOKEN = CF.get_token(args.owner, BASE_URL, APP_KEY, APP_SECRET)

# 매수, 매도 한글 설명 값
dict_deal_desc = {
    'BUY':'매수',
    'SELL':'매도',
}

# 일자 파라미터. 당일
start_date = CF.get_current_time().split(' ')[0]
end_date   = CF.get_current_time().split(' ')[0]


# 슬랙 메세지 기본. 호출 후 필요한 인자만 추가하여 사용
def init_slack_params():
    dict_params = {
        'start_date': start_date,
        'end_date': end_date, 
        'order_type': '', 
        'ord_qty': 0, 
        'price': 0, 
        'buy_avg_price': 0,
        'result':'',
        'msg': '',
        'slack_webhook_url': '',
        'stock_code': STOCK_CD,
        'stock_name': STOCK_NM,
    }

    return dict_params


# 꼐정별 상태 메세지 전송
def send_account_status_msg(status_msg):
    # 슬랙 파라미터 생성
    dict_params = init_slack_params()
    dict_params['order_type'] = 'STATUS'
    dict_params['result'] = '상태 알림'
    dict_params['msg'] = status_msg
    dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
    # 슬랙 전송
    CF.make_for_send_msg(dict_params)
    # 연속 두번 전송 막기 위함
    time.sleep(0.5)



# 계정별 재고
def save_account_data(div):
    order_info = ''
    # 재고 현황
    if div == 'STOCK':
        dict_stock = TR.get_stock_info(args.owner, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, TOKEN)
        (stock_qty, stock_avg_prc) = (dict_stock['stock_qty'], dict_stock['stock_avg_prc'])
        return stock_qty, stock_avg_prc
    # 직전 매도, 매수 평균
    elif div == 'AVG':
        list_avg_prc = []
        for div in ['매도','매수']:
            dict_div_price = TR.last_deal_avg_price(args.owner, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, TOKEN, start_date, end_date, div)
            list_avg_prc.append(dict_div_price['last_deal_avg_prc'])
        (sell_avg_prc, buy_avg_prc) = (list_avg_prc[0], list_avg_prc[1])
        return sell_avg_prc, buy_avg_prc
    # 주문 수량 및 금액
    elif div == 'ORD':
        deposit_amt = TR.get_deposit(
                args.owner, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, STOCK_CD, TOKEN
            )
        # 지정한 수량이 있으면
        if ORDER_QTY != '0':
            # 지정한 수량
            ord_abl_qty = ORDER_QTY
        else:
            # 상한가 적용된 주문가능수량
            ord_abl_qty = CF.calc_order_qty(deposit_amt, preday_close_price)
  
        return ord_abl_qty, deposit_amt
    
# 계정별 매수 주문
def execute_buy(msg):
    # 주문
    if TR.buy_stock(args.owner, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, STOCK_CD, ORDER_QTY, TOKEN):
        # 매수 후 잠깐 대기. 데이터를 위해. 어짜피 바로 매도안됨.
        time.sleep(3)
        sell_avg_prc, buy_avg_prc = save_account_data('AVG')
        # 슬랙 메세지 전송
        dict_params = init_slack_params()
        dict_params['order_type'] = 'BUY'
        dict_params['ord_qty'] = ORDER_QTY
        dict_params['price'] = buy_avg_prc
        dict_params['buy_avg_price'] = buy_avg_prc
        dict_params['msg'] = msg
        dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
        CF.make_for_send_msg(dict_params)
        return True
    else:
        return False
    
# 계정별 매도 주문
def execute_sell():
    # 주문
    if TR.sell_stock(args.owner, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, STOCK_CD, ORDER_QTY, TOKEN):
        # 매수 후 잠깐 대기. 데이터를 위해. 어짜피 바로 매수안됨.
        time.sleep(3)
        sell_avg_prc, buy_avg_prc = save_account_data('AVG')
        # 슬랙 메세지 전송
        dict_params = init_slack_params()
        dict_params['order_type'] = 'SELL'
        dict_params['ord_qty'] = ORDER_QTY
        dict_params['price'] = sell_avg_prc
        dict_params['buy_avg_price'] = buy_avg_prc
        sell_earn_rt = CF.calc_earn_rt(sell_avg_prc, buy_avg_prc)
        if sell_earn_rt > 0.0:
            dict_params['result'] = 'UP'
            dict_params['msg'] = f"매도 후 {sell_earn_rt}% 이익. ^___^"
        else:
            dict_params['result'] = 'DN'
            dict_params['msg'] = f"매도 후 {sell_earn_rt}% 손실. ㅠㅠ"
        dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
        print(dict_params)
        # 매도에 대한 결과 메세지 전송
        CF.make_for_send_msg(dict_params)
        return True
    else:
        return False


if __name__ == "__main__":
    slack_msg = '매수 테스트!!!'
    # execute_buy(slack_msg)
    execute_sell()
    time.sleep(3)
    dict_result = TR.get_stock_info(args.owner, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, TOKEN)
    print(dict_result)