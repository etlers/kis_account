"""
    계정을 입력 받아서 해당 계정으로 매매
"""
import json, time, os
import argparse
import trader as TR
import com_func as CF
import polars as pl
import statistics as stats

# 인자를 받아서 처리. 없으면 등록된 것으로
# 여러개를 돌릴때 사용하고자 함
parser = argparse.ArgumentParser(description="투자주체 확인")
parser.add_argument("--owner", help="투자 주체")
args = parser.parse_args()


# 거래에 관련한 모든 정보
with open("../env/config.json", "r") as f:
    config = json.load(f)
# 계정정보를 기본 이틀러스로 아니면 인자로 받은 계정으로 설정
owner = args.owner.upper() if args.owner else "SOOJIN"
for dict_value in config["accounts"]:
    if dict_value['owner'] == owner:
        dict_account = dict_value
        break

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
dict_last_info = CF.get_previous_trading_info(dict_account['stock_code'])
preday_updn_rt = dict_last_info['change_percent']  # 전일대비 상승하락 비율
preday_close_price = int(dict_last_info['close_price'])  # 전일 종가
print(f"전일 종가: {preday_close_price:,}원, 전일대비 상승률: {preday_updn_rt}%")


# 거래 시작
def monitor_price():
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
    print(f"# 투자자: {dict_account['owner']}.  종목: {dict_account['stock_code']} [{dict_account['stock_name']}]")
    
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
    dict_deposit = TR.get_deposit(dict_account)
    # 계정별 예수금 및 주문가능금액
    ord_abl_amt = dict_deposit['deposit']
    ord_abl_qty = CF.calc_order_qty(ord_abl_amt, preday_close_price)
    open_msg += f'\n  주문가능금액: {ord_abl_amt:,}원, 상한가(30%) 적용 주문가능수량: {ord_abl_qty}주'
    #------------------------------------------------------------------------
    # 상태 변수 초기화 위한 잔고 수량 및 평균 금액
    #------------------------------------------------------------------------
    dict_stock_info = TR.get_stock_info(dict_account)
    STOCK_CNT, STOCK_AVG_PRC = (dict_stock_info['stock_cnt'], dict_stock_info['stock_avg_prc'])
    if STOCK_CNT > 0:
        position = 'SELL'
        print(f'{position}!! {STOCK_CNT}주 ')
        print(f'{position}!! {STOCK_CNT}주 ')
        print(f'{position}!! {STOCK_CNT}주 ')
    else:
        position = 'BUY'
    #------------------------------------------------------------------------
    # 시작 전 알림 메세지
    open_msg = f"⏸ 장 시작!! \n  직전거래일({dict_last_info['date'].replace('.','-')}) 마감: {preday_close_price}. {preday_updn_rt}% {preaday_status}"
    #------------------------------------------------------------------------
    buy_cnt = 1  # 매수 회차
    sell_cnt = 1  # 매도 회차
    v_rebound_cnt = 0  # V자 반등 횟수
    now_earn_rt = 0.0  # 수익률
    slack_msg = '' # 슬랙으로 보낼 메세지
    pre_price = None

    ####################################################################
    # 시작
    ####################################################################
    start_price = TR.get_current_price(dict_account)
    base_price = 0  # 거래 시작 금액으로 하락율 기준
    # 당일 저가 및 고가
    today_low_price = start_price
    today_high_price = start_price
    low_price_change_cnt = 0  # 저가 갱신 횟수
    high_price_change_cnt = 0  # 고가 갱신 횟수
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
    #--------------------------------------------------------
    # 수량
    if int(ord_abl_qty) > 0:
        ORDER_QTY = ord_abl_qty  # 매수 가능 수량
    else:
        ORDER_QTY = '1'  # 없으면 테스트로 1주
    #--------------------------------------------------------
    # 수익 기준
    BASE_SELL_RT = 1.005  # 매도 수익률을 0.5% 기본으로 설정
    #--------------------------------------------------------
    # 직전 매도 평균
    dict_sell_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매도')
    # 직전 매수 평균
    dict_buy_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매수')
    SELL_AVG_PRICE, AVG_WHOLE_BUYING = (dict_sell_avg_prc['last_deal_avg_prc'], dict_buy_avg_prc['last_deal_avg_prc'])
    # 직전 매수 평균이 없으면 잔고 금액으로 설정
    if AVG_WHOLE_BUYING == 0.0:
        AVG_WHOLE_BUYING = STOCK_AVG_PRC
    # 장 시작 메세지 전송
    print('#' * 100)
    if AVG_WHOLE_BUYING > 0:
        print(f"📌 직전 매수: {AVG_WHOLE_BUYING:,}")
    if SELL_AVG_PRICE > 0.0:
        print(f"📌 직전 매도: {SELL_AVG_PRICE:,}")
    print(f"📌 시작 금액: {start_price:,}")
    print('#' * 100)
    #--------------------------------------------------------
    # 불리언 변수
    additional_buy_tf = False  # 추가 매수 여부
    step_down_up_tf = False  # V자 반등 체크
    send_start_msg_tf = False  # 장 시작 메세지 전송 여부
        
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
                dict_param = {
                    'start_date': start_date,
                    'end_date': end_date, 
                    'order_type': 'Start!!', 
                    'qty': 0, 
                    'price': 0, 
                    'buy_avg_price': 0,
                    'result':'오픈 알림',
                    'msg': open_msg
                }
                CF.make_for_send_msg(dict_account, dict_param)
                send_start_msg_tf = True
        ####################################################################
        # 15시 15분이 되면 종료
        if now_dtm > END_DEAL_TM:
            if STOCK_CNT > 0:
                slack_msg = "⏳ 장 마감 시간 도래, 매도 후 프로그램 종료"
                # 매도
                if TR.sell_stock(dict_account, ORDER_QTY):
                    # 직전 매도 평균
                    dict_sell_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매도')
                    sell_cnt += 1
                    dict_param = {
                        'start_date': start_date,
                        'end_date': end_date, 
                        'order_type': 'SELL', 
                        'qty': ORDER_QTY, 
                        'price': dict_sell_avg_prc['last_deal_avg_prc'], 
                        'buy_avg_price': 0,
                        'result':'',
                        'msg': slack_msg
                    }
                    CF.make_for_send_msg(dict_account, dict_param)
            else:
                slack_msg = "⏳ 장 마감 시간 도래, 매도할 수량 없음. 프로그램 종료"
                dict_param = {
                        'start_date': start_date,
                        'end_date': end_date, 
                        'order_type': 'CLOSE', 
                        'qty': 0, 
                        'price': 0, 
                        'buy_avg_price': 0,
                        'result':'',
                        'msg': slack_msg
                    }
                CF.make_for_send_msg(dict_account, dict_param)
            break

        # 시세
        current_price = TR.get_current_price(dict_account)
        # 금액이 이상한 경우
        if current_price == -9999:
            continue
        ####################################################################
        # 수동으로 매수를 한다. 특정 경로에 파일 존재
        ####################################################################
        if os.path.isfile(full_path_buy):
            slack_msg = '### 수동 매수!!!'
            if TR.buy_stock(dict_account, ORDER_QTY):
                # 직전 매수 평균
                dict_buy_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매수')
                AVG_WHOLE_BUYING = dict_buy_avg_prc['last_deal_avg_prc']
                buy_cnt += 1
                position = 'SELL'
                os.rename(full_path_buy, f'./file/{file_nm_buy}')
                dict_param = {
                        'start_date': start_date,
                        'end_date': end_date, 
                        'order_type': 'BUY', 
                        'qty': ORDER_QTY, 
                        'price': AVG_WHOLE_BUYING, 
                        'buy_avg_price': AVG_WHOLE_BUYING,
                        'result':'',
                        'msg': slack_msg
                    }
                CF.make_for_send_msg(dict_account, dict_param)
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
        # 변동성이 심한 장초반에는 매수하지 말자. 데이터는 쌓아두고 매수는 이후에 한다.
        if position == 'BUY' and now_dtm < START_TM_BUY:
            # 전일대비 극초반 급상승 중이면 바로 매수
            if now_dtm < EARLY_BUY_CHK_TM:
                if preday_current_rt > 0.29 and preday_current_rt < 0.7:
                    slack_msg = f'# 장초반 급상승({preday_current_rt}%) 매수'
                    if TR.buy_stock(dict_account, ORDER_QTY):
                        # 직전 매수 평균
                        dict_buy_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매수')
                        AVG_WHOLE_BUYING = dict_buy_avg_prc['last_deal_avg_prc']
                        buy_cnt += 1
                        position = 'SELL'
                        dict_param = {
                                'start_date': start_date,
                                'end_date': end_date, 
                                'order_type': 'BUY', 
                                'qty': ORDER_QTY, 
                                'price': AVG_WHOLE_BUYING, 
                                'buy_avg_price': AVG_WHOLE_BUYING,
                                'result':'',
                                'msg': slack_msg
                            }
                        CF.make_for_send_msg(dict_account, dict_param)
                        low_price_change_cnt = 0
                        high_price_change_cnt = 0
                        BASE_SELL_RT = 1.007  # 수익률 상향
                        continue
                # 극초반 매수 조건을 만족하지 않으면 데이터 쌓기만 함
                print(f"# 매수대기 {CF.get_current_time(full='Y').split(' ')[1]}] 저가: {today_low_price}, 현재: {current_price}({preday_current_rt}%), 고가: {today_high_price}")
                continue
        ####################################################################
        # 지정한 기준금액이 있으면 확인 후 다음 데이터 추출
        if os.path.isfile(full_path_bp):
            with open(full_path_bp, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    if '#' in line: continue
                    # 지정한 금액 추출
                    SELL_AVG_PRICE = int(line.strip().replace(',',''))
                    print(f'# 매수 기준금액 지정: {SELL_AVG_PRICE:,}')
                    print('#' * 100)
                    # 파일 이동
            os.rename(full_path_bp, f'./file/{file_nm_bp}')
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
        # 전체 매도를 위한 잔고 수량 및 평균 금액
        dict_stock_info = TR.get_stock_info(dict_account)
        STOCK_CNT, STOCK_AVG_PRC = (dict_stock_info['stock_cnt'], dict_stock_info['stock_avg_prc'])
        ####################################################################
        # 강제 매도. 특정 경로에 파일이 있으면 매도 처리.
        # 목표 수익률은 가지 못할거 같은데 또 하락할거 같은 느낌이 드는 경우 익절을 위함
        if os.path.isfile(full_path_sell):
            if STOCK_CNT == 0:
                slack_msg = f"# 강제 매도. 잔고 없음. 거래 종료"
                dict_param = {
                    'start_date': start_date,
                    'end_date': end_date, 
                    'order_type': 'CLOSE', 
                    'qty': 0, 
                    'price': 0, 
                    'buy_avg_price': 0,
                    'result':'',
                    'msg': slack_msg
                }
                CF.make_for_send_msg(dict_account, dict_param)
            else:
                slack_msg = f"✅ 강제 매도. 수익률: {now_earn_rt}%"
                # 매도
                if TR.sell_stock(dict_account, ORDER_QTY):
                    # 직전 매도 평균
                    dict_sell_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매도')
                    sell_cnt += 1
                    dict_param = {
                        'start_date': start_date,
                        'end_date': end_date, 
                        'order_type': 'SELL', 
                        'qty': ORDER_QTY, 
                        'price': dict_sell_avg_prc['last_deal_avg_prc'], 
                        'buy_avg_price': 0,
                        'result':'',
                        'msg': slack_msg
                    }
                    CF.make_for_send_msg(dict_account, dict_param)
            # 파일 이동 및 종료
            os.rename(full_path_sell, f'./file/{file_nm_sell}')
            break

        ####################################################################
        # 매수 후 14시가 넘었는데 1.5%가 넘게 내려왔다면 손절하자
        if now_dtm > '140000':
            if STOCK_CNT > 0 and now_earn_rt < -1.5:
                slack_msg = f"### 손절매도!!! {now_earn_rt}%"
                # 매도
                if TR.sell_stock(dict_account, ORDER_QTY):
                    # 직전 매도 평균
                    dict_sell_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매도')
                    sell_cnt += 1
                    dict_param = {
                        'start_date': start_date,
                        'end_date': end_date, 
                        'order_type': 'SELL', 
                        'qty': ORDER_QTY, 
                        'price': dict_sell_avg_prc['last_deal_avg_prc'], 
                        'buy_avg_price': 0,
                        'result':'',
                        'msg': slack_msg
                    }
                    CF.make_for_send_msg(dict_account, dict_param)
                break

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
            #------------------------------------------------------------------------
            # 13시 30분 이후는 매수하지 않는다. 매도만 한다.
            # 금액만으로 판단이 안됨. 잔고가 있는지 확인해야 함
            if now_dtm > '133000':
                if STOCK_CNT == 0:
                    slack_msg = f"# 13시 30분 이후 잔고 없음. 거래 종료"
                    dict_param = {
                        'start_date': start_date,
                        'end_date': end_date, 
                        'order_type': 'CLOSE', 
                        'qty': 0, 
                        'price': 0, 
                        'buy_avg_price': 0,
                        'result':'',
                        'msg': slack_msg
                    }
                    CF.make_for_send_msg(dict_account, dict_param)
                    break
                else:
                    position = 'SELL'
                    continue
            #------------------------------------------------------------------------
            # 11시 이전 시작(직전)대비 기준이상 빠지고 5연속 상승하면 매수한다.
            start_vs_down_tf = False
            slack_msg_start_vs_down = ''
            if now_dtm < '110000':
                # 5연속 상승인 경우
                if inc_tf:
                    # 이전 매도가 있었던 경우
                    if buy_cnt > 1:
                        if pre_sell_current_rt < -1.5:
                            start_vs_down_tf = True
                            slack_msg_start_vs_down = f'이전 매도대비 {pre_sell_current_rt}% 하락 후 5연속 상승. 매수'
                    # 최초 매수의 경우
                    else:
                        if base_current_rt < -1.9:
                            start_vs_down_tf = True
                            slack_msg_start_vs_down = f'시작대비 {base_current_rt}% 하락 후 5연속 상승. 매수'
            #------------------------------------------------------------------------
            # 이전 매도보다 -0.3% 아래로 내려갔을 경우 즉, 99.7% 가격 이하에서만 매수를 한다.
            if start_vs_down_tf == False and SELL_AVG_PRICE > 0.0:
                if pre_sell_current_rt > -0.3:
                    print(f'# 이전 매도대비 -0.3% 이하 조건 불만족. 현재 {pre_sell_current_rt}% 상승. 매수 대기')
                    print('#' + '-' * 99 )
                    BASE_SELL_RT = 1.004 # 두번째 이상부터는 0.4%로 수익률 하향. 익절이 어려율 확률이 높다.
                    continue
            #------------------------------------------------------------------------
            # 단계적 하락 후 상승. V자 반등을  잡고자 함. 단, V자 반등은 한번만 함
            # 5번 연속 하락 발생이 4번 이상 발생하고 오르기 시작한 시점에
            if v_rebound_cnt == 0:
                slack_msg_step_down_up = ''
                if step_down_up_tf == False and seq_dec_cnt > 3 and inc_tf:
                    # 마지막 조건으로 연속 하락의 횟수가 연속 상승의 횟수보다 최소 3번 이상은 많아야 한다.
                    # 거의 꼭지점에 다시 올라온 상태를 거르기 위함
                    if seq_dec_cnt - seq_inc_cnt > 2:
                        step_down_up_tf = True
                        slack_msg_step_down_up = f'{threshold}연속 단계적 하락 {seq_dec_cnt}회 후 5연속 상승. 매수'
            #------------------------------------------------------------------------
            # 횡보장. 중간값을 기준으로 0.3% 이내에서 오르락 내리락 하다 마지막에 5개가 튀어오르면 매수하자
            sideways_tf = False
            slack_msg_sideways = ''
            if len(LIST_SISE_PRICE) < 50:
                pass
            else:
                # 최근 5틱이 모두 상승이면서
                if inc_tf:
                    base_tick = 150
                    # 최근 150틱을 기준으로
                    base_max_prc = max(LIST_SISE_PRICE[-base_tick:])
                    base_min_prc = min(LIST_SISE_PRICE[-base_tick:])
                    median_prc = stats.median(LIST_SISE_PRICE[-base_tick:])
                    min_max_rt = CF.calc_earn_rt(base_max_prc, base_min_prc)
                    # 0.3% 미만 상승 했거나 중간값 대비 위 아래로 0.3% 범위 내인 경우
                    if (min_max_rt < 0.3) or (base_max_prc < median_prc * 1.003 and base_min_prc > median_prc * 0.997):
                        slack_msg_sideways = f'### {base_tick}틱 횡보장 최소값 대비 최대 값 비율 {min_max_rt}% 및 {base_min_prc} ~ {base_max_prc} 구간 및 중간값({median_prc}) 0.3% 이내 후 상승. 매수!!!'
                        sideways_tf = True
                        BASE_SELL_RT = 1.0045 # 수익률 하향
            #------------------------------------------------------------------------                
            # V자 반등은 한번만 하기 위함
            #------------------------------------------------------------------------
            if v_rebound_cnt == 1:
                step_down_up_tf = False
            #------------------------------------------------------------------------                
            # 매수조건 확인 후 매수
            # 기울기 급하락, 상승장, 횡보장, 최근 모두 하락 중 하나라도 만족
            #------------------------------------------------------------------------
            if step_down_up_tf or sideways_tf or start_vs_down_tf:
                slack_msg = ''
                if step_down_up_tf:
                    slack_msg += slack_msg_step_down_up + '\n'
                    v_rebound_cnt = 1
                if sideways_tf:
                    slack_msg += slack_msg_sideways + '\n'
                if start_vs_down_tf:
                    slack_msg += slack_msg_start_vs_down + '\n'
                # 매수 후 매수 평균 금액
                if TR.buy_stock(dict_account, ORDER_QTY):
                    # 직전 매수 평균
                    dict_buy_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매수')
                    AVG_WHOLE_BUYING = dict_buy_avg_prc['last_deal_avg_prc']
                    buy_cnt += 1
                    position = 'SELL'
                    dict_param = {
                            'start_date': start_date,
                            'end_date': end_date, 
                            'order_type': 'BUY', 
                            'qty': ORDER_QTY, 
                            'price': AVG_WHOLE_BUYING, 
                            'buy_avg_price': AVG_WHOLE_BUYING,
                            'result':'',
                            'msg': slack_msg
                        }
                    CF.make_for_send_msg(dict_account, dict_param)
                    # 매수 횟수 증가
                    buy_cnt += 1
                    # 매도 진행으로 변경
                    position = 'SELL'
                    low_price_change_cnt = 0
                    high_price_change_cnt = 0
        
        ####################################################################
        # 매도를 위한 모니터링
        ####################################################################
        else:
            # 매도 수익률 조정이 있으면 기준 수익률 변경
            if os.path.isfile(full_path_sell_rt):
                with open(full_path_sell_rt, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        if '#' in line: continue
                        # 지정한 기준 수익률 추출
                        BASE_SELL_RT = float(line.strip().replace(',',''))
                        print(f'### 매도 기준 수익률 지정: {BASE_SELL_RT}')
                        print('#' * 100)
                        # 파일 이동
                os.rename(full_path_sell_rt, f'./file/{file_nm_sell_rt}')
            #------------------------------------------------------------------------
            # 10시 이전 조기 매수매도의 경우 수익률을 높여줌
            if now_dtm < '100000':
                BASE_SELL_RT = 1.006
            else:
                BASE_SELL_RT = 1.005
            #------------------------------------------------------------------------
            # 매도 조건 확인
            sell_tf, base_sell_price = CF.check_sell(now_dtm[:4], AVG_WHOLE_BUYING, current_price, BASE_SELL_RT)
            # 기준 대비 얼마나 남았는지
            rate_for_base_sell_price = CF.calc_earn_rt(current_price, base_sell_price)
            # 금액 확인 및 상황 출력
            sell_msg = f"# {CF.get_current_time(full='Y').split(' ')[1]}. {dict_deal_desc[position]} {sell_cnt}회차] "
            sell_msg += f"현재: {current_price:,}({now_earn_rt}%) "
            sell_msg += f"기준: {base_sell_price:,}({rate_for_base_sell_price}%({base_sell_price - current_price})) "
            sell_msg += f"매수: {AVG_WHOLE_BUYING:,}"
            print(sell_msg)
            #------------------------------------------------------------------------
            # 매도 조건에 맞으면
            if sell_tf:
                # 매도
                if TR.sell_stock(dict_account, ORDER_QTY):
                    # 직전 매도 평균
                    dict_sell_avg_prc = TR.last_deal_avg_price(dict_account, start_date, end_date, div='매도')
                    sell_cnt += 1
                    dict_param = {
                        'start_date': start_date,
                        'end_date': end_date, 
                        'order_type': 'SELL', 
                        'qty': ORDER_QTY, 
                        'price': dict_sell_avg_prc['last_deal_avg_prc'], 
                        'buy_avg_price': 0,
                        'result':'',
                        'msg': slack_msg
                    }
                    CF.make_for_send_msg(dict_account, dict_param)
                else:
                    break
                # 매수로 변경
                position = 'BUY'

    
if __name__ == "__main__":
    monitor_price()
    # 당일 수익률 확인  
    CF.today_deal_result(dict_account, start_date, end_date)
    # 데이터 저장
    print(df_sise.shape)
    df_sise.write_csv(f"./data/log_data_{CF.get_current_time().split(' ')[0]}.csv", include_header=True)
