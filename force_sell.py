import json, time, os
import multiprocessing
import trader as TR
import com_func as CF
import polars as pl


# 일자 파라미터. 당일
start_date = CF.get_current_time().split(' ')[0]
end_date   = CF.get_current_time().split(' ')[0]


# 거래 시작
# tail -f /Users/etlers/Documents/kis_account/cron_$(date +%Y%m%d).log
if __name__ == '__main__':
    # 거래에 관련한 모든 정보
    with open("../env/config.json", "r") as f:
        config = json.load(f)
    
    accounts = config["accounts"]

    # 계정정보를 기본 이틀러스로 아니면 인자로 받은 계정으로 설정
    for dict_value in config["accounts"]:
        if dict_value['owner'] == 'SOOJIN':
            dict_account = dict_value
            break

    dict_stock_info = TR.get_stock_info(dict_account)
    ORDER_QTY, STOCK_AVG_PRC = (dict_stock_info['stock_cnt'], dict_stock_info['stock_avg_prc'])
    print(dict_stock_info)

    # # 직전 매수 평균
    # dict_buy_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매수')
    # AVG_WHOLE_BUYING = dict_buy_avg_prc['last_deal_avg_prc']
    # BASE_SELL_RT = 1.003

    # # 매도
    # if TR.sell_stock(dict_account, ORDER_QTY):
    #     # 직전 매도 평균
    #     dict_sell_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매도')
    #     dict_params = {
    #         'start_date': start_date,
    #         'end_date': end_date, 
    #         'order_type': 'SELL', 
    #         'qty': ORDER_QTY, 
    #         'price': dict_sell_avg_prc['last_deal_avg_prc'], 
    #         'buy_avg_price': AVG_WHOLE_BUYING,
    #         'result':'',
    #         'msg': slack_msg
    #     }
    #     CF.make_for_send_msg(dict_account, dict_params)

    # while True:
    #     now_dtm = CF.get_current_time().split(' ')[1]
    #     current_price = -9999
    #     while current_price == -9999:
    #         current_price = TR.get_current_price(dict_account)

    #     # if pre_price == current_price:
    #     #     continue

    #     now_earn_rt = CF.calc_earn_rt(current_price, AVG_WHOLE_BUYING)

    #     # 매도 조건 확인
    #     base_sell_price = int(AVG_WHOLE_BUYING * BASE_SELL_RT)
    #     sell_tf = False
    #     if current_price > base_sell_price:
    #         sell_tf = True
    #     # 기준 대비 얼마나 남았는지
    #     rate_for_base_sell_price = CF.calc_earn_rt(current_price, base_sell_price)
    #     # 금액 확인 및 상황 출력
    #     sell_msg = f"# {CF.get_current_time(full='Y').split(' ')[1]}. 강제매도] "
    #     sell_msg += f"현재: {current_price:,}({now_earn_rt}%) "
    #     sell_msg += f"기준: {base_sell_price:,}({rate_for_base_sell_price}%({base_sell_price - current_price})) "
    #     sell_msg += f"매수: {AVG_WHOLE_BUYING:,}"
    #     print(sell_msg)
        
    #     if now_dtm > '152500' or sell_tf:
    slack_msg = f"✅ 강제 매도. 결과: "

    #         # 매도
    if TR.sell_stock(dict_account, ORDER_QTY):
        # 직전 매도 평균
        dict_sell_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매도')
        dict_params = {
            'start_date': start_date,
            'end_date': end_date, 
            'order_type': 'SELL', 
            'qty': ORDER_QTY, 
            'price': dict_sell_avg_prc['last_deal_avg_prc'], 
            'buy_avg_price': dict_sell_avg_prc['last_deal_avg_prc'],
            'result':'',
            'msg': slack_msg
        }
        CF.make_for_send_msg(dict_account, dict_params)
    #     pre_price = current_price
