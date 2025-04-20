"""
    병렬작업.
    - 매수, 매도, 잔고, 마지막 매도(매수) 금액
    - 추가매수 없음
"""
import json, time, os
import multiprocessing
import trader as TR
import com_func as CF
import polars as pl


# 거래에 관련한 모든 정보
with open("config.json", "r") as f:
    config = json.load(f)

accounts = config["accounts"]

# 시세 조회 딜레이 시간
DELAY_SEC = 0.25
# 시세 리스트
LIST_SISE_PRICE = []  # 추세 확인을 위한 리스트
SISE_PRICE = []  # 검증을 위한 시세 데이터

# 매수, 매도
dict_deal_desc = {
    'BUY':'매수',
    'SELL':'매도',
}
# 시세 데이터 저장
df_sise = pl.DataFrame([])
# 계정별 예수금
dict_acc_deposit = {}
# 계정별 잔고
dict_acc_stock_info = {}
# 계정별 잔고매도(매수) 평균 금액
dict_acc_last_buy_avg_price = {}
dict_acc_last_sell_avg_price = {}
# 계정별 매도, 매수 결과
dict_sell_stock = {}
dict_buy_stock = {}

# 일자 파라미터. 당일
start_date = CF.get_current_time().split(' ')[0]
end_date   = CF.get_current_time().split(' ')[0]
# 직전 거래일 정보 확인
dict_last_info = CF.get_previous_trading_info(accounts[0]['stock_code'])
preday_updn_rt = dict_last_info['change_percent']  # 전일대비 상승하락 비율
preday_close_price = int(dict_last_info['close_price'])  # 전일 종가
print(f"전일 종가: {preday_close_price:,}원, 전일대비 상승률: {preday_updn_rt}%")


####################################################################################################
# 예수금 조회 (병렬 실행 + 결과 수집)
# 결과 정리
def adjust_deposit_result(results):
    # 출력 확인
    for dict_val in results:
        ord_abl_qty = CF.calc_order_qty(dict_val['deposit'], preday_close_price)
        dict_acc_deposit[dict_val['account']] = [dict_val['deposit'], ord_abl_qty]
        print(f" - {dict_val['account']} 예수금: {dict_val['deposit']:,}원, 주문가능수량: {ord_abl_qty}주")

# 실제 함수 호출
def run_deposit(account_info, q):
    results = TR.get_deposit(account_info)
    q.put(results)
####################################################################################################

####################################################################################################
# 잔고 조회 (병렬 실행 + 결과 수집)
# 결과 정리
def adjust_stock_info_result(results):
    # 출력 확인
    for dict_val in results:
        # print(f" - {dict_val['account']} 수량: {dict_val['stock_cnt']} 잔고평균가:{dict_val['stock_cnt']:,}원")
        dict_acc_stock_info[dict_val['account']] = [
                dict_val['stock_cnt'],
                dict_val['stock_avg_prc'],
                dict_val['buy_abl_amt'],
                dict_val['total_eval_amt'],
                dict_val['bf_asset_eval_amt'],
            ]

# 실제 함수 호출
def run_stock_info(account_info, q, dict_params):
    results = TR.get_stock_info(account_info, dict_params['alarm'])
    q.put(results)
####################################################################################################

####################################################################################################
# 마지막 평균 매도(매수) 금액 조회 (병렬 실행 + 결과 수집)
# 결과 정리
def adjust_last_deal_avg_prc_result(results):
    # 출력 확인
    for dict_val in results:
        if dict_val['div'] == '매도':
            dict_acc_last_sell_avg_price[dict_val['account']] = dict_val['last_deal_avg_prc']
        elif dict_val['div'] == '매수':
            dict_acc_last_buy_avg_price[dict_val['account']] = dict_val['last_deal_avg_prc']

# 실제 함수 호출
def run_last_deal_avg_prc(account_info, q, dictg_param):
    results = TR.last_deal_avg_price(account_info, start_date, end_date, dictg_param['div'])
    q.put(results)
####################################################################################################

####################################################################################################
# 전량 매도 (병렬 실행 + 결과 수집)
# 결과 정리
def adjust_sell_stock_result(results):
    # 출력 확인
    for dict_val in results:
        dict_sell_stock[dict_val['account']] = dict_val['tf']

# 실제 함수 호출
def run_sell_stock(account_info, q, dict_param):
    results = TR.sell_stock(account_info, dict_acc_stock_info, start_date, end_date, dict_param['now_prc'])
    # 매도 후 잔고 조회
    q.put(results)
####################################################################################################




# 병렬 실행 + 결과 수집
def call_parallel_func(func_name, accounts, dict_params):
    dict_func_info = {
        run_deposit:['예수금 조회', adjust_deposit_result,],
        run_stock_info:['잔고 조회', adjust_stock_info_result,],
        run_last_deal_avg_prc:['마지막 매도(매수) 평균 금액 조회', adjust_last_deal_avg_prc_result,],
        run_sell_stock:['잔고 매도', adjust_sell_stock_result,],
    }
    if dict_params['print'] == 'Y':
        print(f"## {dict_func_info[func_name][0]} 시작")
    # 계좌 수량
    q = multiprocessing.Queue()
    # 잔고는 모든 계정에서 병렬 실행
    processes = []
    for account in accounts:
        p = multiprocessing.Process(target=func_name, args=(account, q, dict_params))
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
def execute():
    # 시세 데이터 저장을 위한 글로벌 변수 선언
    global df_sise
    # 글로벌 변수 설정
    EARLY_BUY_CHK_TM = '090300'  # 장초반 급상승 체크 시간
    START_TM_BUY = '091500'  # 매수 시작 시간 기준
    END_DEAL_TM = '151500'  # 종료시각
    DEC_SELL_RT = 0.0005  # 시간에 따른 절감 수익률 (0.05%)
    # 계정별 장시작 메세지
    dict_acc_open_msg = {}
    # 계정별 마지막 거래 금액
    dict_acc_last_price = {}
    # 매도 기준 수익률 변경을 위한 파일
    file_nm_sell_rt = 'sell_rt.txt'
    full_path_sell_rt = f'./{file_nm_sell_rt}'
    # 기준금액 확인을 위한 파일
    file_nm_bp = 'start_price.txt'
    full_path_bp = f'./{file_nm_bp}'    
    # 즉시 매수를 위한 파일
    file_nm_buy = 'direct_buy.txt'
    full_path_buy = f'./{file_nm_buy}'
    # 즉시 매도를 위한 파일
    file_nm_sell = 'direct_sell.txt'
    full_path_sell = f'./{file_nm_sell}'
    # 불리언 변수
    additional_buy_tf = False  # 추가 매수 여부
    step_down_up_tf = False  # V자 반등 체크
    send_start_msg_tf = False  # 장 시작 메세지 전송 여부
    
    print('#' * 100 )
    for account in accounts:
        print(f"# {account['name']} 종목: {account['stock_code']} [{account['stock_name']}]")
    
    ####################################################################
    # 어제 많이 상승 했다면 신중하게 매수
    if preday_updn_rt > 1.5:
        preaday_status = '상승. 신중하게 매수'
    # 어제 많이 하락 했다면 과감하게 매수
    elif preday_updn_rt < -1.5:
        preaday_status = '하락. 과감하게 매수'
    # 일상적인 경우
    else:
        preaday_status = '일반적인 진행'
        
    #------------------------------------------------------------------------
    # 상태 변수 초기화 위한 잔고 수량 및 평균 금액
    #------------------------------------------------------------------------
    position = 'BUY'
    #------------------------------------------------------------------------
    # 시작 전 알림 메세지
    open_msg = f"⏸ 장 시작!! \n  직전거래일({dict_last_info['date'].replace('.','-')}) 마감: {preday_close_price}. {preday_updn_rt}% {preaday_status}"
    # #------------------------------------------------------------------------
    # # 주문가능금액 확인
    # 예수금 조회 (병렬 실행 + 결과 수집)
    dict_params = {
        'print': 'Y',
    }
    call_parallel_func(run_deposit, accounts, dict_params)
    # 예수금 조회 결과 정리
    # {'ETLERS': [995613, '65'], 'SOOJIN': [50002, '3']}
        
    # 계정별 장시작 메세지 생성
    for account in accounts:
        # 계정별 예수금 및 주문가능금액
        ord_abl_qty = dict_acc_deposit[account['name']][1]
        ord_abl_amt = dict_acc_deposit[account['name']][0]
        open_msg += f'\n  주문가능금액: {ord_abl_amt:,}원, 상한가(30%) 적용 주문가능수량: {ord_abl_qty}주'
        dict_acc_open_msg[account['name']] = open_msg


    # 시작
    while True:
        # 현재시각
        now_dtm = CF.get_current_time().split(' ')[1]
        ####################################################################
        # 9시 장 개시 전이면 대기
        if now_dtm < '085959':
            print(CF.get_current_time(full='Y').split(' ')[1])
            time.sleep(1)
            # 대기중 혹시라도 파일이 남아 있다면 해당 파일을 대기 폴더로 이동한다.
            if os.path.isfile(full_path_sell):
                os.rename(full_path_sell, f'./file/{file_nm_sell}')
            continue
        ####################################################################
        # 재시작이 아닌 경우만 장 시작 메세지 전송
        if now_dtm < '090500':
            if send_start_msg_tf == False:
                CF.make_for_send_msg('Start!!', 0, 0, '오픈 알림', open_msg)
                send_start_msg_tf = True
        ####################################################################
        # 15시 15분이 되면 종료
        if now_dtm > END_DEAL_TM:
            # 마지막 매도 평균 금액
            dict_params = {
                'div': '매도',
                'alarm': 'N',
                'print': 'N'
            }
            # 잔고 조회 (병렬 실행 + 결과 수집)
            call_parallel_func(run_stock_info, accounts, dict_params)
            dict_params = {
                'now_prc': current_price,
            }
            call_parallel_func(run_sell_stock, accounts, 'N', dict_params)
            break

        # 시세
        current_price = TR.get_current_price(accounts[0])
        # 금액이 이상한 경우
        if current_price == -999:
            continue
        ####################################################################
        # 전일 대비 상승하락 비율
        preday_current_rt = CF.calc_earn_rt(current_price, preday_close_price)
        ####################################################################
        # 처음이면
        if pre_price is None:
            # 최초 데이터 저장
            LIST_SISE_PRICE.append(current_price)
            # 이전 금액으로 저장 후 다음 금액 추출
            pre_price = current_price
            continue
        # 이전과 동일하면 다음 데이터 처리
        elif current_price == pre_price:
            continue
        else:
            pre_price = current_price
        # 검증을 위한 데이터의 저장
        new_row = pl.DataFrame({
            "DTM": [CF.get_current_time()],
            "PRC": [current_price]
        })
        df_sise = df_sise.vstack(new_row)
        # 로직에서 사용하는 데이터는 동일한 시세 제외한 시세를 저장
        LIST_SISE_PRICE.append(current_price)
        ####################################################################
        # 저가 갱신
        if current_price < today_low_price:
            today_low_price = current_price
            low_price_change_cnt += 1
        ####################################################################
        # 고가 갱신
        if current_price > today_high_price:
            today_high_price = current_price
            high_price_change_cnt += 1
        ####################################################################
        # 거래 시작금액
        if base_price == 0:
            base_price = current_price
            print('#' * 100)
            print(f"📌 거래 기준 금액: {base_price:,}")
            print('#' * 100)

        ####################################################################
        # 추세 확인
        if len(LIST_SISE_PRICE) < 5:
            print(f'### 시세 데이터 부족. {len(LIST_SISE_PRICE)}개')
            continue
        # 가장 마지막 5개 금액의 상승, 하락 여부
        inc_tf, dec_tf = CF.check_trend(LIST_SISE_PRICE[-5:], div='all')
        ####################################################################
        # V자 반등.
        # 최소 우선 5개 연속 하락을 한번으로 판단하자
        threshold = 5
        # 이전 V자 반등이 없었던 경우
        if step_down_up_tf == False:
            # 최소 50개 이상에서 판단하자
            if df_sise.height > 50:
                # 꼭대기 이후 몇번 내려왔는지로 하자. 오르락 내리락으로 조건을 만족하는 것을 방지하기 위함
                list_sise_for_rebound = CF.get_sise_list_by_high_price(df_sise)
                seq_inc_cnt, seq_dec_cnt = CF.count_up_down_trends(list_sise_for_rebound, threshold)
        ####################################################################
        # 매수 후 매도를 위한 매수 금액에 대한 수익률 계산
        if AVG_WHOLE_BUYING == 0.0:
            now_earn_rt = 0.0
        else:
            now_earn_rt = CF.calc_earn_rt(current_price, AVG_WHOLE_BUYING)

        ####################################################################
        # 매수인 경우만
        ####################################################################
        if position == 'BUY':
            #------------------------------------------------------------------------
            # 거래 시작금액 비율을 위한 계산
            base_current_rt = CF.calc_earn_rt(current_price, base_price)
            pre_sell_current_rt = CF.calc_earn_rt(current_price, SELL_AVG_PRICE)
            # 이후 매수 대기 메세지
            buy_msg = f"# {CF.get_current_time(full='Y').split(' ')[1]} {dict_deal_desc[position]} {buy_cnt}회차] 저가: {today_low_price:,}, "            
            if SELL_AVG_PRICE > 0:
                # 직전 매도가 있었다면 매수 기준이 되는 직전 매도금액 표시
                buy_msg += f"기준: {SELL_AVG_PRICE:,}, 직전 매도대비 {pre_sell_current_rt}% 현재: {current_price}, 고가: {today_high_price:,}"
            else:
                buy_msg += f"현재: {current_price:,}, 고가: {today_high_price:,}"
            buy_msg += "\n" + f"# 시작대비: {base_current_rt}%, 전일대비: {preday_current_rt}%, "
            buy_msg += f"{threshold}연속상승: {seq_inc_cnt}, {threshold}연속하락: {seq_dec_cnt}, "
            buy_msg += f"저가갱신: {low_price_change_cnt}, 고가갱신: {high_price_change_cnt}"
            print(buy_msg)
            print('#' * 100 )
        ####################################################################
        # 매도를 위한 모니터링
        ####################################################################
        else:
            pass


    # 잔고 조회 (병렬 실행 + 결과 수집)
    # call_parallel_func(run_stock_info, accounts, 'N')
    # print(dict_acc_stock_info)

    
if __name__ == "__main__":
    execute()
