import json, time, os
import multiprocessing
import trader as TR
import com_func as CF
import polars as pl


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
if __name__ == '__main__':
    # 거래에 관련한 모든 정보
    with open("config.json", "r") as f:
        config = json.load(f)
    
    accounts = config["accounts"]

    # 일자 파라미터. 당일
    start_date = "20250418" #CF.get_current_time().split(' ')[0]
    end_date   = CF.get_current_time().split(' ')[0]

    # 마지막 매도 평균 금액
    dict_params = {
        'start_date': start_date,
        'end_date': end_date,
        'div': '매도',
        'alarm': 'N',
        'print': 'N'
    }
    call_parallel_func(run_last_deal_avg_prc, accounts, dict_params)
    # run_last_deal_avg_prc(accounts, start_date, end_date, '매도', alarm='N')
    print(dict_acc_last_avg_price)