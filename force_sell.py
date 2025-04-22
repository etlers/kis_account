import json, time, os
import multiprocessing
import trader as TR
import com_func as CF
import polars as pl


# 일자 파라미터. 당일
start_date = CF.get_current_time().split(' ')[0]
end_date   = CF.get_current_time().split(' ')[0]

# 계정별 잔고매도(매수) 평균 금액
dict_acc_last_avg_price = {}

####################################################################################################
# 마지막 평균 매도(매수) 금액 조회 (병렬 실행 + 결과 수집)
# 결과 정리
def adjust_last_deal_avg_prc_result(results):
    # 출력 확인
    for dict_last_deal_avg_prc in results:
        dict_acc_last_avg_price[dict_last_deal_avg_prc['account']] = dict_last_deal_avg_prc['last_deal_avg_prc']

# 실제 함수 호출
def run_last_deal_avg_prc(account_info, q, start_date, end_date, div, alarm='N'):
    results = TR.last_deal_avg_price(account_info, start_date, end_date, div)
    q.put(results)


# 병렬 실행 + 결과 수집
def call_parallel_func(func_name, accounts, dict_params):
    dict_func_info = {
        # run_deposit:['예수금 조회', adjust_deposit_result,],
        # run_stock_info:['잔고 조회', adjust_stock_info_result,],
        run_last_deal_avg_prc:['마지막 매도(매수) 평균 금액 조회', adjust_last_deal_avg_prc_result,],
    }
    if dict_params['print'] == 'Y':
        print(f"## {dict_func_info[func_name][0]} 시작")
    # 계좌 수량
    q = multiprocessing.Queue()
    # 잔고는 모든 계정에서 병렬 실행
    processes = []
    for account in accounts:
        p = multiprocessing.Process(target=func_name, args=(
                account, q, dict_params['start_date'], dict_params['end_date'], dict_params['div'], dict_params['alarm'])
            )
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    # 결과 수집
    results = []
    while not q.empty():
        results.append(q.get())

    # 출력 확인
    dict_func_info[func_name][1](results)
    if dict_params['print']  == 'Y':
        print(f"## {dict_func_info[func_name][0]} 종료")

    return results


# 거래 시작
# tail -f /Users/etlers/Documents/kis_account/cron_$(date +%Y%m%d).log
if __name__ == '__main__':
    # 거래에 관련한 모든 정보
    with open("../env/config.json", "r") as f:
        config = json.load(f)
    
    accounts = config["accounts"]

    # 계정정보를 기본 이틀러스로 아니면 인자로 받은 계정으로 설정
    for dict_value in config["accounts"]:
        if dict_value['owner'] == 'DEV':
            dict_account = dict_value
            break

    dict_stock_info = TR.get_stock_info(dict_account)
    ORDER_QTY, STOCK_AVG_PRC = (dict_stock_info['stock_cnt'], dict_stock_info['stock_avg_prc'])

    # 직전 매수 평균
    dict_buy_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매수')
    AVG_WHOLE_BUYING = dict_buy_avg_prc['last_deal_avg_prc']
    BASE_SELL_RT = 1.003

    while True:
        now_dtm = CF.get_current_time().split(' ')[1]
        current_price = -9999
        while current_price == -9999:
            current_price = TR.get_current_price(dict_account)

        # if pre_price == current_price:
        #     continue

        now_earn_rt = CF.calc_earn_rt(current_price, AVG_WHOLE_BUYING)

        # 매도 조건 확인
        base_sell_price = int(AVG_WHOLE_BUYING * BASE_SELL_RT)
        sell_tf = False
        if current_price > base_sell_price:
            sell_tf = True
        # 기준 대비 얼마나 남았는지
        rate_for_base_sell_price = CF.calc_earn_rt(current_price, base_sell_price)
        # 금액 확인 및 상황 출력
        sell_msg = f"# {CF.get_current_time(full='Y').split(' ')[1]}. 강제매도] "
        sell_msg += f"현재: {current_price:,}({now_earn_rt}%) "
        sell_msg += f"기준: {base_sell_price:,}({rate_for_base_sell_price}%({base_sell_price - current_price})) "
        sell_msg += f"매수: {AVG_WHOLE_BUYING:,}"
        print(sell_msg)
        
        if now_dtm > '152500' or sell_tf:
            slack_msg = f"✅ 강제 매도. 결과: "

            # 매도
            if TR.sell_stock(dict_account, ORDER_QTY):
                # 직전 매도 평균
                dict_sell_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매도')
                dict_params = {
                    'start_date': start_date,
                    'end_date': end_date, 
                    'order_type': 'SELL', 
                    'qty': ORDER_QTY, 
                    'price': dict_sell_avg_prc['last_deal_avg_prc'], 
                    'buy_avg_price': AVG_WHOLE_BUYING,
                    'result':'',
                    'msg': slack_msg
                }
                CF.make_for_send_msg(dict_account, dict_params)

                break
        pre_price = current_price
