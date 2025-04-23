import polars as pl
import requests
import json
import time
from datetime import datetime, timedelta
from itertools import groupby

from bs4 import BeautifulSoup

import trader as TR


# 로그 파일로 생성
def save_to_log_file(owner, data):
    fnm = f"./logs/{get_current_time(full='Y').split(' ')[0]}.log"
    with open(fnm, 'a', encoding='utf-8-sig') as log_file:
        log_file.write(data)


# 운영, 모의에 맞는 TR_ID 생성
def set_real_tr_id(tr_id, owner):
    if owner == 'DEV':
        BASE_URL = "https://openapivts.koreainvestment.com:29443"
        return ['V' + tr_id[1:], BASE_URL]
    else:
        BASE_URL = "https://openapi.koreainvestment.com:9443"
        return [tr_id, BASE_URL]

# 수익률 계산
def calc_earn_rt(now, base):
    if base == 0:
        rt = 0
    else:
        rt = round((now - base) / base * 100, 2)
    return rt

# 증가 감소에 대한 확인
def check_trend(lst, div='all'):
    if len(lst) < 5: 
        return False, False
    increasing = all(lst[i] <= lst[i + 1] for i in range(len(lst)-1))  # 증가 여부 확인
    decreasing = all(lst[i] >= lst[i + 1] for i in range(len(lst)-1))  # 감소 여부 확인

    if div == 'all':
        return increasing, decreasing
    elif div == 'last_1':
        # 마지막 상승
        if lst[-2] < lst[-1]:
            return "LAST_1_INC"
        # 마지막 하락
        elif lst[-2] > lst[-1]:
            return "LAST_1_DEC"
        else:
            return "PASS"
    elif div == 'last_2':
        # 마지막 2개의 상승
        if lst[-3] > lst[-2] and lst[-2] > lst[-1]:
            return "LAST_2_DEC"
        # 마지막 2개의 하락
        elif lst[-3] < lst[-2] and lst[-2] < lst[-1]:
            return "LAST_2_INC"
        else:
            return "PASS"
    else:
        # 마지막 3개의 상승
        if lst[-4] > lst[-3] and lst[-3] > lst[-2] and lst[-2] > lst[-1]:
            return "LAST_3_DEC"
        # 마지막 3개의 하락
        elif lst[-4] < lst[-3] and lst[-3] < lst[-2] and lst[-2] < lst[-1]:
            return "LAST_3_INC"
        else:
            return "PASS"

####################################################################
# 현재일시
def get_current_time(full='N'):
    if full == 'Y':
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        return datetime.now().strftime("%Y%m%d %H%M%S")
    
####################################################################
# 지정한 날짜 문자열과 날짜 수를 받아, 이전 날짜를 문자열로 반환하는 함수.
def get_previous_date(date_str: str, days_before: int, date_format: str = "%Y-%m-%d") -> str:
    base_date = datetime.strptime(date_str, date_format)
    previous_date = base_date - timedelta(days=days_before)
    return previous_date.strftime(date_format)

####################################################################
# 네이버 증권에서 특정 종목의 어제 상승률을 가져오는 함수
def get_naver_stock_yesterday_change(stock_code):
    url = f"https://finance.naver.com/item/sise.naver?code={stock_code}"

    # 웹 페이지 가져오기
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        return f"Error: Unable to fetch data (Status Code {response.status_code})"

    # HTML 파싱
    soup = BeautifulSoup(response.text, "html.parser")

    try:
        # 현재가 가져오기
        price_now_element = soup.select_one("p.no_today span.blind")
        if price_now_element:
            price_now = float(price_now_element.text.strip().replace(',', ''))
        else:
            return "Error: Cannot find current price"

        # 전일 종가 가져오기
        price_prev_element = soup.select("table.no_info tr")[0].select("td")[0].select_one("span.blind")
        if price_prev_element:
            price_prev = float(price_prev_element.text.strip().replace(',', ''))
        else:
            return "Error: Cannot find previous close price"

        # 상승률 직접 계산
        change_rate = ((price_now - price_prev) / price_prev) * 100

        dict_result = {
            "현재가": price_now,
            "전일 종가": price_prev,
            "어제 상승률 (%)": round(change_rate, 2)
        }

        print(dict_result)

        return dict_result['어제 상승률 (%)'], dict_result['전일 종가']
    
    except Exception as e:
        return f"Error: {str(e)}"

####################################################################
# 전 거래일 추출 - 기본 삼성전자로 함
def get_previous_trading_day(stock_code="005930"):
    import datetime

    url = f"https://finance.naver.com/item/sise_day.nhn?code={stock_code}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 날짜 리스트 파싱
    dates = []
    for row in soup.select('table.type2 tr'):
        cols = row.find_all('td')
        if len(cols) >= 6:
            date_text = cols[0].get_text(strip=True)
            try:
                date_obj = datetime.datetime.strptime(date_text, "%Y.%m.%d")
                dates.append(date_obj.date())
            except Exception as e:
                print(e)
                continue

    # 최신 날짜 기준 정렬 후 두 번째 값이 전 거래일
    dates = sorted(list(set(dates)), reverse=True)
    if len(dates) >= 2:
        return dates[1]  # 두 번째 날짜가 전 거래일
    else:
        return None
    
####################################################################
# 슬랙으로 메세지 보내기
def send_slack_alert(order_type, dict_account, qty, price, result, msg):
    icon_ord = {
        "BUY": "🟢",
        "SELL": "🔴",
    }.get(order_type, "🔔")

    icon_result = {
        "UP": "📈",
        "DN": "📉"
    }.get(result, "🔔")
    
    if order_type in ('BUY','SELL'):
        text = f"{icon_ord} *{order_type} 체결 알림*\n종목: `{dict_account['stock_name']}`\n수량: `{qty}`주\n가격: `{price:,}`원"
        text = text + '\n\n' + f"{icon_result} {msg}"
    else:
        text = f"{icon_result} {msg}"

    SLACK_WEBHOOK_URL = dict_account['slack_webhook_url']
    
    payload = {
        "text": text
    }
    
    response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload))
    
    if response.status_code != 200:
        print("Slack 알림 전송 실패:", response.status_code, response.text)

####################################################################
def get_previous_trading_info(stock_code):
    url = f"https://finance.naver.com/item/sise_day.nhn?code={stock_code}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.encoding = 'euc-kr'
    soup = BeautifulSoup(response.text, 'html.parser')

    today = datetime.today().date()
    rows = soup.select('table.type2 tr')

    prices = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 7:
            continue

        date_str = cols[0].text.strip()
        try:
            row_date = datetime.strptime(date_str, '%Y.%m.%d').date()
        except ValueError:
            continue

        if row_date < today:
            close_price_str = cols[1].text.strip().replace(',', '')
            try:
                close_price = int(close_price_str)
                prices.append((row_date, close_price))
            except ValueError:
                continue

        if len(prices) == 2:
            break

    if len(prices) < 2:
        return {"error": "데이터 부족"}

    latest_date, latest_close = prices[0]
    prev_date, prev_close = prices[1]

    change_amount = latest_close - prev_close
    change_percent = (change_amount / prev_close) * 100

    return {
        'stock_code': stock_code,
        'date': latest_date.strftime('%Y.%m.%d'),
        'close_price': latest_close,
        'change_amount': change_amount,
        'change_percent': round(change_percent, 2)
    }

####################################################################
# 최고가 기준 이후 시세 데이터 추출
def get_sise_list_by_high_price(df_sise):
    # 최고가
    high_prc = max(df_sise['PRC'])
    df_filter = df_sise.filter(pl.col('PRC') == high_prc)
    # 최고가 중 가장 오래된 금액
    min_dtm = min(df_filter['DTM'])
    # 이후 시세 데이터
    df_sise = df_sise.filter(pl.col('DTM') >= min_dtm)
    
    return list(df_sise["PRC"])


# 매수 수량 계산
def calc_order_qty(deposit, now_prc):
    try:
        fee_rate = 0.3  # 0.3%
        unit_price = now_prc * (1 + fee_rate)
        return str(int(deposit // unit_price) - 1)
    except:
        return '0'
    

# 최고가 기준 이후 시세 데이터 추출
def get_sise_list_by_high_price(df_sise):
    # 최고가
    high_prc = max(df_sise['PRC'])
    df_filter = df_sise.filter(pl.col('PRC') == high_prc)
    # 최고가 중 가장 오래된 금액
    min_dtm = min(df_filter['DTM'])
    # 이후 시세 데이터
    df_sise = df_sise.filter(pl.col('DTM') >= min_dtm)
    
    return list(df_sise["PRC"])

# 기준횟수 이상으로 연속 상승, 하락한 횟수 추출
def count_up_down_trends(prices, threshold=5):
    increase_count = 0
    decrease_count = 0

    current_trend = None  # 'up' or 'down'
    streak = 0

    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            if current_trend == 'up':
                streak += 1
            else:
                if current_trend == 'down' and streak >= threshold:
                    decrease_count += 1
                current_trend = 'up'
                streak = 1
        elif prices[i] < prices[i - 1]:
            if current_trend == 'down':
                streak += 1
            else:
                if current_trend == 'up' and streak >= threshold:
                    increase_count += 1
                current_trend = 'down'
                streak = 1
        else:
            # 변화 없음 -> 이전 트렌드 종료
            if current_trend == 'up' and streak >= threshold:
                increase_count += 1
            elif current_trend == 'down' and streak >= threshold:
                decrease_count += 1
            current_trend = None
            streak = 0

    # 마지막 구간 체크
    if current_trend == 'up' and streak >= threshold:
        increase_count += 1
    elif current_trend == 'down' and streak >= threshold:
        decrease_count += 1

    return increase_count, decrease_count

# 메세지 생성 및 호출
def make_for_send_msg(dict_account, dict_params):
    # 슬랙으로 메세지 전송
    if dict_params['order_type'] == 'BUY':
        send_slack_alert(dict_params['order_type'], dict_account, dict_params['qty'], dict_params['price'], dict_params['result'], dict_params['msg'])
    elif dict_params['order_type'] == 'SELL':
        # 직전 매수 평균
        if dict_params['buy_avg_price'] == 0:
            deal_earn_rt = 0.0
        else:
            deal_earn_rt = round((dict_params['price'] - dict_params['buy_avg_price']) / dict_params['buy_avg_price'] * 100, 2)
        # 결과 메세지 생성
        if deal_earn_rt > 0.0:
            result = 'UP'
            msg = f'{deal_earn_rt}% 수익!! ^___^'
        else:
            result = 'DN'
            msg = f'{deal_earn_rt}% 손실!! ㅠㅠ'

        send_slack_alert(dict_params['order_type'], dict_account, dict_params['qty'], dict_params['price'], result, f"{dict_params['msg']} {msg}")
    else:
        send_slack_alert(dict_params['order_type'], dict_account, dict_params['qty'], dict_params['price'], dict_params['result'], f"{dict_params['msg']}")
    # 기본 메세지 출력
    print(f"{dict_params['msg']}")
    
# 매도를 위한 금액 조건 확인
def check_sell(check_hm, avg_prc, now_prc, base_rt):
    add_rt = 0.0
    # 시간에 따른 수익률 절감을 위한 비교 시분 목록. 최대 0.3% 빠짐
    if check_hm > '1330':
        add_rt += 0.001
    if check_hm > '1430':
        add_rt += 0.001
    if check_hm > '1500':
        add_rt += 0.001
    # 기본으로 설정
    base_sell_price = int(round(avg_prc * (base_rt - add_rt), 2))
    # 이상이면 매도 처리
    if int(now_prc) >= base_sell_price:
        return True, base_sell_price
    else:
        return False, base_sell_price
    

# 매도 수익률 계산
def calc_deal_profit_rate(account_info, start_date, end_date):
    dict_deal_div = {
        '매도': '01',
        '매수': '02',
    }
    list_dict_result = TR.get_last_buy_trade(account_info, start_date, end_date)
    
    # 구분에 밎는 금액을 리스트로 저장후
    list_sell_amt = []
    list_buy_amt = []
    for dict_data in list_dict_result:
        if dict_data['DIV'] == '현금매도':
            list_sell_amt.append(dict_data['TOT_AMT'])
        elif dict_data['DIV'] == '현금매수':
            list_buy_amt.append(dict_data['TOT_AMT'])
    # 수익률 계산
    sell_amt = sum(list_sell_amt)
    buy_amt = sum(list_buy_amt)
    
    if buy_amt == 0:
        return 0, 0, 0.0, 0, 0
    
    profit_rt = round((sell_amt - buy_amt) / buy_amt * 100, 2)
    sell_avg = int(sell_amt / len(list_sell_amt))
    buy_avg = int(buy_amt / len(list_buy_amt))

    return sell_amt, buy_amt, profit_rt, sell_avg, buy_avg


# 당일 거래 결과
def today_deal_result(dict_account, dict_params):
    time.sleep(1)
    # 수익률 계산 및 최종 매도금액 저장
    today_sell_amt, today_buy_amt, deal_earn_rt, today_sell_avg, today_buy_avg = calc_deal_profit_rate(
            dict_account, dict_params['start_date'], dict_params['end_date']
        )
    # 결과 출력
    print('#' * 100)
    print(f'# 오늘 거래결과: {deal_earn_rt}%  매수: {today_buy_amt:,}({today_buy_avg:,})  매도: {today_sell_amt:,}({today_sell_avg:,})')
    print('#' * 100)
    profit_amt = today_sell_amt - today_buy_amt
    # 보유 자산에 대한 결과
    dict_stock_info = TR.get_stock_info(dict_account)
    amount_gap = int(dict_stock_info['total_eval_amt']) - int(dict_stock_info['bf_asset_eval_amt'])
    try:
        today_amt_rt = round((amount_gap / int(dict_stock_info['bf_asset_eval_amt'])) * 100, 5)
    except:
        today_amt_rt = 0.0
    # 메세지 생성
    slack_msg = f"전일 {int(dict_stock_info['bf_asset_eval_amt']):,}원에서 {int(dict_stock_info['total_eval_amt']):,}원으로 "
    if amount_gap > 0:
        slack_msg += f"{amount_gap:,}원 {today_amt_rt}% 증가!! ^___^"
        result = 'UP'
    else:
        slack_msg += f"{amount_gap:,}원 {today_amt_rt}% 감소... ㅠㅠ"
        result = 'DN'
    # 결과 슬랙으로 전송
    send_slack_alert('RESULT', dict_account, dict_params['qty'], dict_params['price'], dict_params['result'], f"{dict_params['msg']} {slack_msg}")
    # 결과 데이터 저장
    try:
        df_deal = pl.read_csv(
            './data/deal_result.csv',
            schema_overrides={
                "OWNER": pl.Utf8,
                "DTM": pl.Utf8,
                "EARN_RT": pl.Float64,
                "ASSET_AMT": pl.Int64,
                "EVAL_AMT": pl.Int64,
                "DEAL_RT": pl.Float64,
                "BUY_AMT": pl.Int64,
                "BUY_AVG": pl.Int64,
                "SELL_AMT": pl.Int64,
                "SELL_AVG": pl.Int64,                    
            }
        )
    except FileNotFoundError:
        df_deal = pl.DataFrame({
            "OWNER": [],
            "DTM": [],
            "EARN_RT": [],
            "ASSET_AMT": [],
            "EVAL_AMT": [],
            "DEAL_RT": [],
            "BUY_AMT": [],
            "BUY_AVG": [],
            "SELL_AMT": [],
            "SELL_AVG": [],
        }).with_columns([
            pl.col("OWNER").cast(pl.Utf8),
            pl.col("DTM").cast(pl.Utf8),
            pl.col("EARN_RT").cast(pl.Float64),
            pl.col("ASSET_AMT").cast(pl.Int64),
            pl.col("EVAL_AMT").cast(pl.Int64),
            pl.col("DEAL_RT").cast(pl.Float64),
            pl.col("BUY_AMT").cast(pl.Int64),
            pl.col("BUY_AVG").cast(pl.Int64),
            pl.col("SELL_AMT").cast(pl.Int64),
            pl.col("SELL_AVG").cast(pl.Int64),
        ])
    # 새 행 (모두 정수값)
    new_row = pl.DataFrame({
        "OWNER": [dict_account['owner']],
        "DTM": [str(get_current_time().split(' ')[0])],
        "EARN_RT": [today_amt_rt],
        "ASSET_AMT": [int(dict_stock_info['bf_asset_eval_amt'])],
        "EVAL_AMT": [int(dict_stock_info['total_eval_amt'])],
        "DEAL_RT": [deal_earn_rt],
        "BUY_AMT": [today_buy_amt],
        "BUY_AVG": [today_buy_avg],
        "SELL_AMT": [today_sell_amt],
        "SELL_AVG": [today_sell_avg],            
    })
    # 데이터 추가 및 저장
    df_deal = df_deal.vstack(new_row)
    df_deal.write_csv(f"./data/deal_result.csv", include_header=True)
