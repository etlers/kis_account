"""
    입력받은 계정으로 매매
"""
import json, time, os
import argparse
import trader as TR
import com_func as CF
import polars as pl
import statistics as stats

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
    status_msg = f""
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
        # 매도에 대한 결과 메세지 전송
        CF.make_for_send_msg(dict_params)
        return True
    else:
        return False
            

# 매도를 위한 기준 금액 확인
def check_for_sell(check_hm, avg_prc, now_prc, base_rt):
    add_rt = 0.0
    # 시간에 따른 수익률 절감을 위한 비교 시분 목록. 최대 0.2% 빠짐
    if check_hm > '1430':
        add_rt += 0.001
    if check_hm > '1500':
        add_rt += 0.001
    # 기본으로 설정
    base_sell_price = int(round(avg_prc * (base_rt - add_rt), 2))
    # 이상이면 매도 처리
    if now_prc >= base_sell_price:
        return True, base_sell_price
    else:
        return False, base_sell_price


def execute_deal():
    # 시세 데이터 저장을 위한 글로벌 변수 선언
    global df_sise, GATHERING_DATA_TF
    # 계정이 없다면 종료
    if run_break:
        return None
    # 거래 구분
    POSITION = 'BUY'
    #------------------------------------------------------------------------
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
    # 시작 전 알림 메세지
    open_msg = f"⏸ 장 시작!! \n  직전거래일({dict_last_info['date'].replace('.','-')}) 마감: {preday_close_price}. {preday_updn_rt}% {preaday_status}"
    #------------------------------------------------------------------------
    # 잔고 수량 및 금액
    ord_abl_qty, deposit_amt = save_account_data('ORD')
    # 메세지 저장
    open_msg += '\n' + f'  주문가능금액: {deposit_amt:,}원, 상한가(30%) 적용 주문가능수량: {ord_abl_qty}주\n'
    #------------------------------------------------------------------------
    buy_cnt = 1  # 매수 회차
    sell_cnt = 1  # 매도 회차
    now_earn_rt = 0.0  # 수익률
    slack_msg = '' # 슬랙으로 보낼 메세지
    ####################################################################
    # 시작
    ####################################################################
    # 시세 추출
    start_price = 0
    while start_price < 1:
        start_price = TR.get_current_price(
                BASE_URL, APP_KEY, APP_SECRET, TOKEN, STOCK_CD
            )
    base_price = 0  # 거래 시작 금액으로 하락율 기준
    # 당일 저가 및 고가
    today_low_price = start_price
    today_high_price = start_price
    low_price_change_cnt = 0  # 저가 갱신 횟수
    high_price_change_cnt = 0  # 고가 갱신 횟수
    pre_price = preday_close_price  # 전일 종가로 설정
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
    # 장시작 전에 기존 파일이 남아 있다면 해당 파일을 대기 폴더로 이동
    if os.path.isfile(full_path_sell):
        os.rename(full_path_sell, f'./file/{file_nm_sell}')
    if os.path.isfile(full_path_sell_rt):
        os.rename(full_path_sell_rt, f'./file/{file_nm_sell_rt}')
    if os.path.isfile(full_path_buy):
        os.rename(full_path_buy, f'./file/{file_nm_buy}')
    if os.path.isfile(full_path_bp):
        os.rename(full_path_bp, f'./file/{file_nm_bp}')
    #--------------------------------------------------------
    # 수익 기준
    BASE_SELL_RT = 1.005  # 매도 수익률을 0.5% 기본으로 설정
    #--------------------------------------------------------
    # 장 시작 메세지 전송
    sell_avg_prc, buy_avg_prc = save_account_data('AVG')
    if buy_avg_prc > 0:
        print(f"# 📌 직전 매수: {buy_avg_prc:,}")
    if sell_avg_prc > 0.0:
        print(f"# 📌 직전 매도: {sell_avg_prc:,}")
    print(f"# 📌 시작 금액: {start_price:,}")
    print('#' * 120)
    #--------------------------------------------------------
    # 불리언 변수
    step_down_up_tf = False  # V자 반등 체크
    send_start_msg_tf = False  # 장 시작 메세지 전송 여부
    force_rate_tf = False  # 강제로 매도 수익률 조정 여부
    down_in_early_day_tf = False  # 시작대비 급락에 대한 여부
    # 금액 변수
    sell_avg_prc = 0  # 직전 매도 평균
    buy_avg_prc = 0  # 직전 매수 평균
    
    ####################################################################
    # 시세를 받아오면서 거래 시작
    ####################################################################
    while True:
        # 현재시각
        now_dtm = CF.get_current_time().split(' ')[1]
        #------------------------------------------------------------------------
        # 9시 장 개시 전이면 대기
        if now_dtm < START_DEAL_TM:
            print(CF.get_current_time(full='Y').split(' ')[1])
            time.sleep(1)
            continue
        #------------------------------------------------------------------------
        # 재시작이 아닌 경우만 장 시작 메세지 전송
        if now_dtm < '090300' and send_start_msg_tf == False:
            # 계정별로 전송
            dict_params = init_slack_params()
            dict_params['order_type'] = 'Start!!'
            dict_params['msg'] = '오픈 알림. ' + open_msg
            dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
            CF.make_for_send_msg(dict_params)
            send_start_msg_tf = True
        #------------------------------------------------------------------------
        # 잔고 수량 및 금액
        # 계정별 잔고 데이터(dict_owner_stock) 활용
        stock_qty, stock_avg_prc = save_account_data('STOCK')    
        #------------------------------------------------------------------------
        # 10시부터 매 시간마다 상태를 슬랙으로 전송
        if now_dtm in ['100000','110000','120000','130000','140000']:
            status_msg = buy_msg if POSITION == 'BUY' else sell_msg
            send_account_status_msg(status_msg)
        #------------------------------------------------------------------------
        # 15시 15분이 되면 종료
        if now_dtm > END_DEAL_TM:
            dict_params = init_slack_params()
            # 잔고가 있으면 매도
            if stock_qty > 0:
                slack_msg = "⏳ 장 마감 시간 도래, 매도 후 프로그램 종료"
                # 매도
                if TR.sell_stock(args.owner, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, STOCK_CD, ORDER_QTY, TOKEN):
                    # 직전 매도 평균 최신화
                    sell_avg_prc, buy_avg_prc = save_account_data('AVG')
                    sell_cnt += 1
                    dict_params['order_type'] = 'SELL'
                    dict_params['msg'] = slack_msg
                    dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL                        
            else:
                slack_msg = "⏳ 장 마감 시간 도래, 매도할 수량 없음. 프로그램 종료"
                dict_params['order_type'] = 'INFO'
                dict_params['msg'] = slack_msg
                dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
            # 슬랙 메세지 전송
            CF.make_for_send_msg(dict_params)
            break
        #------------------------------------------------------------------------
        # 시세
        current_price = TR.get_current_price(
                BASE_URL, APP_KEY, APP_SECRET, TOKEN, STOCK_CD
            )
        # 금액이 이상한 경우
        if current_price == -9999:
            continue
        #------------------------------------------------------------------------
        # 수동으로 매수를 한다. 특정 경로에 파일 존재
        #------------------------------------------------------------------------
        if os.path.isfile(full_path_buy):
            slack_msg = '### 수동 매수!!!'
            if execute_buy(slack_msg):
                buy_cnt += 1
                POSITION = 'SELL'
            os.rename(full_path_buy, f'./file/{file_nm_buy}')
        #------------------------------------------------------------------------
        # 전일 대비 상승하락 비율
        preday_current_rt = CF.calc_earn_rt(current_price, preday_close_price)
        #------------------------------------------------------------------------
        # 이전과 동일하면 다음 데이터 처리
        if current_price == pre_price:
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
        #------------------------------------------------------------------------
        # 저가 갱신
        if current_price < today_low_price:
            today_low_price = current_price
            low_price_change_cnt += 1
        # 고가 갱신
        if current_price > today_high_price:
            today_high_price = current_price
            high_price_change_cnt += 1
        #------------------------------------------------------------------------
        # 거래 시작금액
        if base_price == 0:
            base_price = current_price
            print('#' * 120)
            print(f"# 📌 거래 기준 금액: {base_price:,}")
            print('#' * 120)
        #------------------------------------------------------------------------
        # 추세 확인
        if len(LIST_SISE_PRICE) < 5:
            print(f'### 시세 데이터 부족. {LIST_SISE_PRICE}')
            continue
        # 상승 흐름 판단. 가장 마지막 5개 금액의 상승, 하락 여부
        inc_dec_check_tick = 4
        inc_tf, dec_tf = CF.check_trend(LIST_SISE_PRICE[-inc_dec_check_tick:], div='all')
        # 최근 10개 틱 중에서 마지막이 상승이고 전체 
        #------------------------------------------------------------------------
        # V자 반등.
        # 최소 우선 5개 연속 하락을 한번으로 판단하자
        threshold = 5
        base_tick_step_down = 200
        seq_inc_cnt, seq_dec_cnt = (0,0)
        # 연속 상승, 하락은 최근 50개 이상에서만 판단하자
        if len(LIST_SISE_PRICE) > 50:
            # 꼭대기 이후 몇번 내려왔는지로 하자. 오르락 내리락으로 조건을 만족하는 것을 방지하기 위함
            list_sise_for_rebound = LIST_SISE_PRICE[-base_tick_step_down:]
            seq_inc_cnt, seq_dec_cnt = CF.count_up_down_trends(list_sise_for_rebound, threshold)
        #------------------------------------------------------------------------
        # 매수 후 매도를 위한 매수 금액에 대한 수익률 계산         
        if buy_avg_prc == 0:
            now_earn_rt = 0.0
        else:
            now_earn_rt = CF.calc_earn_rt(current_price, buy_avg_prc)
        #------------------------------------------------------------------------
        # 강제 매도. 특정 경로에 파일이 있으면 매도 처리.
        # 목표 수익률은 가지 못할거 같은데 또 하락할거 같은 느낌이 드는 경우 익절을 위함
        if os.path.isfile(full_path_sell):
            dict_params = init_slack_params()
            if stock_qty == 0:
                slack_msg = f"# 강제 매도. 잔고 없음. 거래 종료"
                dict_params['order_type'] = 'CLOSE'
                dict_params['msg'] = slack_msg
                dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
                CF.make_for_send_msg(dict_params)
            else:
                slack_msg = f"✅ 강제 매도. 수익률: {now_earn_rt}%"
                if TR.sell_stock(args.owner, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, STOCK_CD, str(stock_qty), TOKEN):
                    # 직전 매도 평균 최신화
                    sell_avg_prc, buy_avg_prc = save_account_data('AVG')
                    sell_cnt += 1
                    dict_params['order_type'] = 'SELL'
                    dict_params['msg'] = slack_msg
                    dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
                    CF.make_for_send_msg(dict_params)
            # 파일 이동 및 종료
            os.rename(full_path_sell, f'./file/{file_nm_sell}')
            GATHERING_DATA_TF = True
            break
        #------------------------------------------------------------------------
        # 매도, 매수 평균 금액 최신화
        sell_avg_prc, buy_avg_prc = save_account_data('AVG')
        #------------------------------------------------------------------------
        # 매수인 경우만
        #------------------------------------------------------------------------
        if POSITION == 'BUY':
            #------------------------------------------------------------------------
            # 거래 시작금액 비율을 위한 계산
            base_current_rt = CF.calc_earn_rt(current_price, base_price)
            # 이후 매수 대기 메세지
            buy_msg = f"# {CF.get_current_time(full='Y').split(' ')[1]} [{dict_deal_desc[POSITION]} {buy_cnt}회차] "
            #------------------------------------------------------------------------
            # 변동성이 심한 장초반에는 매수하지 말자. 데이터는 쌓아두고 매수는 이후에 한다.
            if now_dtm < START_TM_BUY:
                # 전일대비 극초반 급상승 중이면 바로 매수
                if now_dtm < EARLY_BUY_CHK_TM:
                    if preday_current_rt > 0.29 and preday_current_rt < 0.7:
                        slack_msg = f'# 장초반 급상승({preday_current_rt}%) 매수'
                        execute_buy(slack_msg)
                        buy_cnt += 1
                        POSITION = 'SELL'
                        low_price_change_cnt = 0
                        high_price_change_cnt = 0
                        BASE_SELL_RT = 1.007  # 수익률 상향
                        # 강제 조정 확인
                        force_rate_tf = True
                        continue
                    # 극초반 매수 조건을 만족하지 않으면 데이터 쌓기만 함
                    buy_msg += f"# 매수대기 {CF.get_current_time(full='Y').split(' ')[1]}] 저가: {today_low_price}, 현재: {current_price}({preday_current_rt}%), 고가: {today_high_price}"
                    print(buy_msg)
                    continue    
            if preday_current_rt > 1.0:
                # 전일대비 고가라 매수 이후 매도가 쉽지 않을 듯
                buy_msg += f"# 전일대비 고가로 매수 대기. 전일대비 {preday_current_rt}% 현재 {current_price}  고가 {today_high_price:,}"
                print(buy_msg)
                print('#' * 120)
                continue
            # 매수대기 메세지
            buy_msg += f"시작대비 {base_current_rt}%  전일대비 {preday_current_rt}%  "
            buy_msg += f"{threshold}연속상승 {seq_inc_cnt}회  {threshold}연속하락 {seq_dec_cnt}회  "
            buy_msg += f"저가갱신 {low_price_change_cnt}회  고가갱신 {high_price_change_cnt}회\n"
            print('#' + '-' * 119 )
            # 직전 매도가 있었다면 매수 기준이 되는 직전 매도금액 표시
            if sell_cnt > 1:
                pre_sell_current_rt = CF.calc_earn_rt(current_price, sell_avg_prc)
                buy_msg += f"# 현재 {current_price} - 기준 {sell_avg_prc:,}({pre_sell_current_rt}%) ({today_low_price:,} ~ {today_high_price:,})"
            else:
                buy_msg += f"# 현재 {current_price:,} ({today_low_price:,} ~ {today_high_price:,})"
            print(buy_msg)
            print('#' * 120)
            #------------------------------------------------------------------------
            # 극초반 아니면 장초반(09시 30분) 상승의 경우는 매수를 지양한다.
            if now_dtm < '093000' and len(LIST_SISE_PRICE) > 50:
                base_rt = 85.0
                icnt = 0
                for prc in LIST_SISE_PRICE:
                    if prc > preday_close_price:
                        icnt += 1
                sise_up_rt = round((icnt / len(LIST_SISE_PRICE)) * 100, 2)
                if sise_up_rt > base_rt:
                    print(f'# 장초반 전일대비 {base_rt}% 이하 상승 조건 {sise_up_rt}%로 불만족. 이후 급락 위험. 매수 대기')
                    print('#' + '-' * 119 )
                    continue
            #------------------------------------------------------------------------
            # 13시 30분 이후는 매수하지 않는다. 매도만 한다.
            if now_dtm > '133000':
                slack_msg = f"# 13시 30분 이후 잔고 없음. 더이상 매수하지 않음. 거래 종료"
                dict_params = init_slack_params()
                dict_params['order_type'] = 'CLOSE'
                dict_params['msg'] = slack_msg
                dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
                CF.make_for_send_msg(dict_params)
                GATHERING_DATA_TF = True
                break
            #------------------------------------------------------------------------
            # 이전 매도보다 -0.3% 아래로 내려갔을 경우 즉, 99.7% 가격 이하에서만 매수를 한다.
            # 대표계정을 기준으로 함
            if POSITION == 'BUY' and sell_avg_prc > 0.0:
                pre_sell_current_rt = CF.calc_earn_rt(current_price, sell_avg_prc)
                if pre_sell_current_rt > -0.3:
                    print(f'# 이전 매도대비 -0.3% 이하 조건 불만족. 현재 {pre_sell_current_rt}% 상승. 매수 대기')
                    print('#' + '-' * 119 )
                    continue
            #------------------------------------------------------------------------
            # 이하 매수는 상승 흐름에서만 즉, 4틱 연속으로 상승한 이후만 적용
            if inc_tf == False:
                print(f'# 아직 상승 흐름으로 진입 못함. {LIST_SISE_PRICE[-inc_dec_check_tick:]}')
                continue
            #------------------------------------------------------------------------
            # 초반에 시작(직전)대비 기준이상 빠지고 연속 상승하면 매수한다.
            down_in_early_day_tf = False
            slack_msg_down_in_early_day = ''
            if now_dtm < '100000':
                if base_current_rt < -1.9 or preday_current_rt < 2.0:
                    down_in_early_day_tf = True
                    slack_msg_down_in_early_day = f'시작대비 {base_current_rt}% 전일대비 {preday_current_rt}% 하락 후 {inc_dec_check_tick}연속 상승. 매수'
                    BASE_SELL_RT = 1.0055
                    # 강제 조정 확인
                    force_rate_tf = True
            #------------------------------------------------------------------------
            # 단계적 하락 후 상승. V자 반등을  잡고자 함.
            slack_msg_step_down_up = ''
            step_down_up_tf == False
            # 5번 연속 하락 발생이 4번 이상 발생하고 오르기 시작한 시점에
            if seq_dec_cnt > 3:                    
                # 마지막 조건으로 연속 하락의 횟수가 연속 상승의 횟수보다 최소 1번 이상은 많아야 한다.
                # 거의 꼭지점에 다시 올라온 상태를 거르기 위함
                if seq_dec_cnt - seq_inc_cnt > 0:
                    step_down_up_tf = True
                    slack_msg_step_down_up = f'{threshold}연속 단계적 하락 {seq_dec_cnt}회 후 {inc_dec_check_tick}연속 상승. 매수'
            # 급락 후 상승
            # 최근 150개 약 30분 급락으로 가장 오랜된 5개 평균과 가장 최근 5개 평균의 차이
            elif len(LIST_SISE_PRICE) > base_tick_step_down * 0.75:
                list_rising = LIST_SISE_PRICE[-base_tick_step_down:]
                new_avg = stats.mean(list_rising[-5:])
                old_avg = stats.mean(list_rising[:5])
                front_rear_rt = CF.calc_earn_rt(new_avg, old_avg)
                # 75% 이상 빠졌다면
                if front_rear_rt < -0.75:
                    step_down_up_tf = True
                    slack_msg_step_down_up = f'급락({front_rear_rt}%) 후 {inc_dec_check_tick}연속 상승. 매수'
            #------------------------------------------------------------------------
            # 횡보장. 중간값을 기준으로 0.25%(1/4분위) 이내에서 오르락 내리락 하다 마지막에 튀어오르면 매수하자
            sideways_tf = False
            slack_msg_sideways = ''
            if len(LIST_SISE_PRICE) < 200:
                pass
            else:
                base_tick_sideway = 150
                # 최근 150틱을 기준으로
                base_max_prc = max(LIST_SISE_PRICE[-base_tick_sideway:])
                base_min_prc = min(LIST_SISE_PRICE[-base_tick_sideway:])
                median_prc = stats.median(LIST_SISE_PRICE[-base_tick_sideway:])
                min_max_rt = CF.calc_earn_rt(base_max_prc, base_min_prc)
                # 중간값 대비 위 아래로 0.15%로 전체 0.3% 범위 내인 경우
                if base_max_prc < median_prc * 1.0015 and base_min_prc > median_prc * 0.9985:
                    slack_msg_sideways = f'### {base_tick_sideway}틱 횡보장 최소값 대비 최대 값 비율 {min_max_rt}% 및 {base_min_prc} ~ {base_max_prc} 구간 및 중간값({median_prc}) 0.25% 이내 후 상승. 매수!!!'
                    sideways_tf = True
                    BASE_SELL_RT = 1.0045 # 수익률 하향
                    # 강제 조정 확인
                    force_rate_tf = True
                # 횡보장 최저 최고가 전일 대비 확인
                if sideways_tf:
                    min_preday_rt = CF.calc_earn_rt(base_min_prc, preday_close_price)
                    max_preday_rt = CF.calc_earn_rt(base_max_prc, preday_close_price)
                    # 최근 30분(150개)의 최저값이 전일보다 0.5% 이상이면 대기하자
                    if min_preday_rt > 0.5:
                        sideways_tf = False
                        print(f'# 횡보장 최근 30분 전일대비 최저가 0.5% 이하 상승 조건 {min_preday_rt}%로 불만족. 최저가 {base_min_prc:,}({preday_close_price:,}). 매수 대기')
                        print('#' + '-' * 119 )
                    # 최근 30분(150개)의 최고값이 전일보다 0.9% 이상이면 대기하자
                    if max_preday_rt > 0.9:
                        sideways_tf = False
                        print(f'# 횡보장 최근 30분 전일대비 최고가 0.9% 이하 상승 조건 {max_preday_rt}%로 불만족. 최저가 {base_max_prc:,}({preday_close_price:,}). 매수 대기')
                        print('#' + '-' * 119 )
            #------------------------------------------------------------------------                
            # 매수조건 확인 후 매수
            # 기울기 급하락, 상승장, 횡보장, 최근 모두 하락 중 하나라도 만족
            #------------------------------------------------------------------------
            if step_down_up_tf or sideways_tf or down_in_early_day_tf:
                slack_msg = ''
                if step_down_up_tf:
                    slack_msg += slack_msg_step_down_up + '\n'
                if sideways_tf:
                    slack_msg += slack_msg_sideways + '\n'
                if down_in_early_day_tf:
                    slack_msg += slack_msg_down_in_early_day + '\n'
                # 매수 진행
                if execute_buy(slack_msg):
                    buy_cnt += 1
                    # 매도 진행으로 변경
                    POSITION = 'SELL'
                    low_price_change_cnt = 0
                    high_price_change_cnt = 0        
        #------------------------------------------------------------------------
        # 매도를 위한 모니터링
        #------------------------------------------------------------------------
        else:
            # 마지막 매수 평균금액이 있어야 함             
            while buy_avg_prc == 0:
                print(f"### 평균 매수 금액 없음!!")
                sell_avg_prc, buy_avg_prc = save_account_data('AVG')
            # 매도 수익률 조정이 있으면 기준 수익률 변경
            if os.path.isfile(full_path_sell_rt):
                with open(full_path_sell_rt, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        if '#' in line: continue
                        # 지정한 기준 수익률 추출
                        BASE_SELL_RT = float(line.strip().replace(',',''))
                        # 강제 조정 확인
                        force_rate_tf = True
                        print(f'### 매도 기준 수익률 지정: {BASE_SELL_RT}')
                        print('#' * 120)
                # 파일 이동
                os.rename(full_path_sell_rt, f'./file/{file_nm_sell_rt}')
            #------------------------------------------------------------------------
            # 수익률 조정
            if force_rate_tf:
                pass  # 강제로 조정한 경우 조정한 수익률 사용
            # 10시 이전 조기 매도의 경우 수익률을 높여줌
            elif now_dtm < '100000':
                BASE_SELL_RT = 1.006
            # 기본으로 설정
            else:
                BASE_SELL_RT = 1.005
            #------------------------------------------------------------------------
            # 매도 조건 확인
            sell_tf, base_sell_price = check_for_sell(
                    now_dtm[:4], buy_avg_prc, current_price, BASE_SELL_RT
                )
            # 기준 대비 얼마나 남았는지
            rate_for_base_sell_price = CF.calc_earn_rt(current_price, base_sell_price)
            # 금액 확인 및 상황 출력
            sell_msg = f"# {CF.get_current_time(full='Y').split(' ')[1]}. {dict_deal_desc[POSITION]} {sell_cnt}회차] "
            sell_msg += f"현재: {current_price:,}({now_earn_rt}%) "
            sell_msg += f"기준: {base_sell_price:,}({rate_for_base_sell_price}%({base_sell_price - current_price})) "
            sell_owner_msg = f"매수: {buy_avg_prc:,}"
            print(sell_msg + sell_owner_msg)
            #------------------------------------------------------------------------
            # 매도 조건에 맞으면
            if sell_tf:
                # 매도    
                if execute_sell():
                    sell_cnt += 1
                    # 매수로 변경
                    POSITION = 'BUY'
                    # 매도 후 기본 조정으로 설정
                    force_rate_tf = False


if __name__ == "__main__":
    # 거래 시작
    execute_deal()
    # 오너가 없어 종료된 것이 아니면
    if run_break == False:
        # 거래 종료에 따른 결과. 당일 수익률 확인
        CF.today_deal_result(
                args.owner, start_date, end_date, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, '01', TOKEN, SLACK_WEBHOOK_URL
            )
        # 시세 데이터 저장
        print(df_sise.shape)
        df_sise.write_csv(f"./data/sise_data_{CF.get_current_time().split(' ')[0]}.csv", include_header=True)
        