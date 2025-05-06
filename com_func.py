import polars as pl
import requests
import os, json
import time
from datetime import datetime, timedelta
from itertools import groupby

from bs4 import BeautifulSoup

import trader as TR


# 거래에 관련한 모든 정보
def get_config_json(): 
    with open("../env/config.json", "r") as f:
        return json.load(f)

# 투자자 거래정보 
def get_owner_config(owner):
    config = get_config_json()
    # 계정정보를 인자로 받은 계정으로 설정
    for dict_value in config["accounts"]:
        if dict_value['owner'] == owner:
            return dict_value

# 운영, 모의에 맞는 TR_ID 생성
def set_real_tr_id(tr_id):
    return 'V' + tr_id[1:]

# 대기 메세지
def wating_message(secs, msg):
    icnt = secs
    while icnt > 0:
        print(f"{msg} {icnt}초")
        icnt -= 1
        time.sleep(1)

# 토큰 발행
def get_token(owner, base_url, app_key, app_secret):
    TOKEN_FILE = f"../env/token/token_cache_{owner}.json"

    """ 존재하는 액세스 토큰 삭제 """
    def delete_token():
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
                print(f"토크파일 삭제 완료!!")
            except Exception as e:
                print(f"토큰파일 삭제 실패: {e}")
    
    """ 액세스 토큰을 JSON 파일에 저장 """
    def save_token(token_data):
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)

    """ JSON 파일에서 액세스 토큰을 불러옴 """
    def load_token():
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                return json.load(f)
        return None

    """ 새로운 Access Token을 요청 """
    def request_new_token():
        url = f"{base_url}/oauth2/tokenP"
        print(url)
        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "appsecret": app_secret,
        }
        headers = {"content-type": "application/json"}
        
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        
        if "access_token" in data:
            access_token = data["access_token"]
            expires_in = int(data.get("expires_in", 3600))  # 만료 시간 (1시간)
            expires_at = time.time() + expires_in - 10  # 안전하게 10초 전 갱신

            token_data = {
                "access_token": access_token,
                "expires_at": expires_at
            }
            save_token(token_data)

            print("✅ 새로운 Access Token 저장 완료")
            return access_token
        else:
            print("❌ Access Token 발급 실패:", data)
            return None
        
    """ Access Token을 불러오거나 만료되었으면 새로 발급 """
    def get_access_token():
        token_data = load_token()

        if token_data:
            expire_time = token_data.get("expires_at", 0)
            current_time = time.time()

            # ✅ 기존 토큰이 아직 유효하면 재사용
            if current_time < expire_time:
                # print("🔑 기존 Access Token 재사용")
                return token_data["access_token"]

        print("🔄 Access Token 새로 발급 중...")
        return request_new_token()
    
    # 기존에 존재하는 토큰 삭제
    delete_token()
    # 토큰 발급
    token = get_access_token()
    # 발급된 토큰 전달
    return token

    
# 현재일시
def get_current_time(full='N'):
    if full == 'Y':
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        return datetime.now().strftime("%Y%m%d %H%M%S")
    
# 지정한 날짜 문자열과 날짜 수를 받아, 이전 날짜를 문자열로 반환하는 함수.
def get_previous_date(date_str: str, days_before: int, date_format: str = "%Y-%m-%d") -> str:
    """
    지정한 날짜 문자열과 날짜 수를 받아, 이전 날짜를 문자열로 반환하는 함수.

    :param date_str: 기준 날짜 (문자열 형식, 예: '2025-03-27')
    :param days_before: 며칠 전인지 (예: 7)
    :param date_format: 날짜 포맷 (기본값은 '%Y-%m-%d')
    :return: 계산된 이전 날짜 (문자열)
    """
    base_date = datetime.strptime(date_str, date_format)
    previous_date = base_date - timedelta(days=days_before)
    return previous_date.strftime(date_format)


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
    

# 슬랙으로 메세지 보내기
def send_slack_alert(order_type, stock_code, ord_qty, price, result, msg, slack_webhook_url):
    icon_ord = {
        "BUY": "🟢",
        "SELL": "🔴",
    }.get(order_type, "🔔")

    icon_result = {
        "UP": "📈",
        "DN": "📉"
    }.get(result, "🔔")
    
    if order_type in ('BUY','SELL'):
        text = f"{icon_ord} *{order_type} 체결 알림*\n종목: `{stock_code}`\n수량: `{ord_qty}`주\n가격: `{price:,}`원"
        text = text + '\n\n' + f"{icon_result} {msg}"
    else:
        text = f"{icon_result} {msg}"
    
    payload = {
        "text": text
    }

    response = requests.post(slack_webhook_url, data=json.dumps(payload))
    
    if response.status_code != 200:
        print("Slack 알림 전송 실패:", response.status_code, response.text)


# 메세지 생성 및 호출
def make_for_send_msg(dict_params):
    # 슬랙 전송을 위한 인자의 구성
    order_type = dict_params['order_type'] 
    stock_code = dict_params['stock_code']
    ord_qty = dict_params['ord_qty']
    price = dict_params['price']
    result = dict_params['result']
    msg = dict_params['msg']
    slack_webhook_url = dict_params['slack_webhook_url']

    # 슬랙으로 메세지 전송
    if dict_params['order_type'] == 'BUY':
        send_slack_alert(order_type, stock_code, ord_qty, price, result, msg, slack_webhook_url)
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

        send_slack_alert(order_type, stock_code, ord_qty, price, result, msg, slack_webhook_url)
    else:
        send_slack_alert(order_type, stock_code, ord_qty, price, result, msg, slack_webhook_url)
    # 기본 메세지 출력
    print(f"{msg}")


# 매도 수익률 계산
def calc_deal_profit_rate(owner, start_date, end_date, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, ACNT_PRDT_CD, ACCESS_TOKEN):
    list_dict_result = TR.get_last_buy_trade(
            owner, start_date, end_date, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, ACNT_PRDT_CD, ACCESS_TOKEN
        )
    
    if list_dict_result is None:
        return 0, 0, 0.0, 0, 0
    
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
def today_deal_result(dict_params):
    start_date = dict_params['start_date']
    end_date = dict_params['end_date']
    OWNER = dict_params['OWNER']
    BASE_URL = dict_params['BASE_URL']
    APP_KEY = dict_params['APP_KEY']
    APP_SECRET = dict_params['APP_SECRET']
    ACC_NO = dict_params['ACC_NO']
    ACNT_PRDT_CD = dict_params['ACNT_PRDT_CD']
    TOKEN = dict_params['TOKEN']
    SLACK_WEBHOOK_URL=dict_params['SLACK_WEBHOOK_URL']

    time.sleep(1)
    # 수익률 계산 및 최종 매도금액 저장
    start_date = get_current_time().split(' ')[0]
    end_date   = get_current_time().split(' ')[0]

    try:
        today_sell_amt, today_buy_amt, deal_earn_rt, today_sell_avg, today_buy_avg = calc_deal_profit_rate(
                OWNER, start_date, end_date, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, ACNT_PRDT_CD, TOKEN
            )
        # 결과 출력
        print('#' * 100)
        print(f'# {OWNER} 오늘 거래결과: {deal_earn_rt}%  매수: {today_buy_amt:,}({today_buy_avg:,})  매도: {today_sell_amt:,}({today_sell_avg:,})')
        print('#' * 100)
        profit_amt = today_sell_amt - today_buy_amt
        # 보유 자산에 대한 결과
        dict_stock_info = TR.get_stock_info(
                OWNER, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, TOKEN
            )
        amount_gap = int(dict_stock_info['total_eval_amt']) - int(dict_stock_info['bf_asset_eval_amt'])
        if dict_stock_info['bf_asset_eval_amt'] == 0:
            today_amt_rt = 0
        else:
            today_amt_rt = round((amount_gap / int(dict_stock_info['bf_asset_eval_amt'])) * 100, 5)
        # 메세지 생성
        slack_msg = f"전일 {int(dict_stock_info['bf_asset_eval_amt']):,}원에서 {int(dict_stock_info['total_eval_amt']):,}원으로 "
        if amount_gap > 0:
            slack_msg += f"{amount_gap:,}원 {today_amt_rt}% 증가!! ^___^"
            result = 'UP'
        else:
            slack_msg += f"{amount_gap:,}원 {today_amt_rt}% 감소... ㅠㅠ"
            result = 'DN'
        # 결과 슬랙으로 전송
        send_slack_alert('RESULT', '', 0, 0, result, slack_msg, SLACK_WEBHOOK_URL)

        # 결과 데이터 저장
        try:
            df_deal = pl.read_csv(
                './data/deal_result.csv',
                schema_overrides={
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
                "DTM": pl.Series([], pl.Utf8),
                "EARN_RT": pl.Series([], pl.Float64),
                "ASSET_AMT": pl.Series([], pl.Int64),
                "EVAL_AMT": pl.Series([], pl.Int64),
                "DEAL_RT": pl.Series([], pl.Float64),
                "BUY_AMT": pl.Series([], pl.Int64),
                "BUY_AVG": pl.Series([], pl.Int64),
                "SELL_AMT": pl.Series([], pl.Int64),
                "SELL_AVG": pl.Series([], pl.Int64),                
            })
        # 새 행 (모두 정수값)
        new_row = pl.DataFrame({
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
        
    except Exception as e:
        print(e)


# 현재 수익률
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


# 상승장 매수 전략 확인
def rise_buy_strategy(lst):
    if len(lst) < 7: 
        return False
    if check_trend(lst[:5]) != 'INC':
        return False
    
    # 마지막 상승 이고 5연속 상승 후 하락 상승인 경우
    if (lst[-1] > lst[-2]) and (lst[-2] < lst[-3]):
        return True
    
    return False


# 하락장 매수 전략 확인
def fall_buy_strategy(lst):
    if len(lst) < 7: 
        return False
    if check_trend(lst[:5]) != 'DEC':
        return False
    
    # 마지막 하락 이고 5연속 하락 후 상승 하락인 경우
    if (lst[-1] < lst[-2]) and (lst[-2] > lst[-3]):
        return True
    
    return False


# 현재가의 저가, 고가에서의 위치
def get_position_ratio(low, current, high):
    if high == low:
        return 0.0
    else:
        # 비율 계산: (현재가 - 저가) / (고가 - 저가)
        return (current - low) / (high - low)
    
# 장초반 수량이 있으면 해당 수량으로 아니면 기준 수량으로
def return_first_buy_qty(base, first):
    if first == 0:
        return base, first
    else:
        return first, 0

# 리스트에서 요소 제거
def remove_used_hour_min_element():
    global LIST_DEC_HM
    if LIST_DEC_HM:
        LIST_DEC_HM.pop(0)  # 앞에서부터 하나 제거
        print(f"현재 리스트 상태: {LIST_DEC_HM}")
    else:
        print("이미 리스트가 비어 있습니다.")
    
# 기준횟수 이상 연속으로 증가한 횟수
def count_long_increasing_sequences(lst, min_length):
    count = 0
    n = len(lst)
    i = 0  # 리스트 인덱스

    while i < n - 1:
        length = 1  # 현재 증가하는 구간의 길이
        # 증가하는 구간의 길이 측정
        while i < n - 1 and lst[i] < lst[i + 1]:
            length += 1
            i += 1
        # 입력받은 최소 증가 횟수 이상이면 카운트
        if length >= min_length:
            count += 1
        i += 1  # 다음 비교를 위해 인덱스 증가

    return count


# 기준횟수 이상 연속으로 감소한 횟수
def count_long_decreasing_sequences(lst, min_length):
    count = 0
    n = len(lst)
    i = 0  # 리스트 인덱스

    while i < n - 1:
        length = 1  # 현재 감소하는 구간의 길이
        # 감소하는 구간의 길이 측정
        while i < n - 1 and lst[i] > lst[i + 1]:
            length += 1
            i += 1
        # 입력받은 최소 감소 횟수 이상이면 카운트
        if length >= min_length:
            count += 1
        i += 1  # 다음 비교를 위해 인덱스 증가

    return count


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


# 매수 수량 계산
def calc_order_qty(buy_cash, now_prc):
    try:
        fee_rate = 0.3  # 0.3%
        unit_price = now_prc * (1 + fee_rate)
        return str(int(buy_cash // unit_price) - 1)
    except:
        return '0'

# 모두 감소여부 확인
def is_strictly_decreasing(lst):
    return all(lst[i] > lst[i+1] for i in range(len(lst) - 1))

# 연속된 중복 요소를 제거
def remove_duplicates_groupby(lst):
    return [key for key, group in groupby(lst)]


# 현재 시세 조회
def get_price(DELAY_SEC, BASE_URL, APP_KEY, APP_SECRET, ACCESS_TOKEN, STOCK_CODE):
    time.sleep(DELAY_SEC)
    data = TR.get_current_price(
            ACCESS_TOKEN, STOCK_CODE, BASE_URL, APP_KEY, APP_SECRET
        )
    try:
        sise_prc = int(data["output"]["stck_prpr"])  # 현재가
    except:
        sise_prc = -9999
    return sise_prc


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


# 슬랙 메세지 기본. 호출 후 필요한 인자만 추가하여 사용
def init_slack_params(start_date, end_date, STOCK_CD, STOCK_NM):
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


# 계정별 재고
def save_account_data(div, dict_params):
    start_date = dict_params['start_date']
    end_date = dict_params['end_date']
    OWNER = dict_params['OWNER']
    BASE_URL = dict_params['BASE_URL']
    APP_KEY = dict_params['APP_KEY']
    APP_SECRET = dict_params['APP_SECRET']
    ACC_NO = dict_params['ACC_NO']
    TOKEN = dict_params['TOKEN']
    STOCK_CD = dict_params['STOCK_CD']
    ORDER_QTY = dict_params['ORDER_QTY']
    preday_close_price  = dict_params['preday_close_price']

    # 재고 현황
    if div == 'STOCK':
        dict_stock = TR.get_stock_info(OWNER, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, TOKEN)
        (stock_qty, stock_avg_prc) = (dict_stock['stock_qty'], dict_stock['stock_avg_prc'])
        return stock_qty, stock_avg_prc
    # 직전 매도, 매수 평균
    elif div == 'AVG':
        list_avg_prc = []
        for div in ['매도','매수']:
            dict_div_price = TR.last_deal_avg_price(OWNER, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, TOKEN, start_date, end_date, div)
            list_avg_prc.append(dict_div_price['last_deal_avg_prc'])
        (sell_avg_prc, buy_avg_prc) = (list_avg_prc[0], list_avg_prc[1])
        return sell_avg_prc, buy_avg_prc
    # 주문 수량 및 금액
    elif div == 'ORD':
        deposit_amt = TR.get_deposit(
                OWNER, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, STOCK_CD, TOKEN
            )
        # 지정한 수량이 있으면
        if ORDER_QTY != '0':
            # 지정한 수량
            ord_abl_qty = ORDER_QTY
        else:
            # 상한가 적용된 주문가능수량
            ord_abl_qty = calc_order_qty(deposit_amt, preday_close_price)
  
        return ord_abl_qty, deposit_amt
    

# 계정별 매수 주문
def execute_buy(dict_params):
    start_date = dict_params['start_date']
    end_date = dict_params['end_date']
    OWNER = dict_params['OWNER']
    BASE_URL = dict_params['BASE_URL']
    APP_KEY = dict_params['APP_KEY']
    APP_SECRET = dict_params['APP_SECRET']
    ACC_NO = dict_params['ACC_NO']
    TOKEN = dict_params['TOKEN']
    STOCK_CD = dict_params['STOCK_CD']
    STOCK_NM = dict_params['STOCK_NM']
    ORDER_QTY = dict_params['ORDER_QTY']
    slack_msg  = dict_params['slack_msg']
    SLACK_WEBHOOK_URL  = dict_params['SLACK_WEBHOOK_URL']

    # 주문
    if TR.buy_stock(OWNER, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, STOCK_CD, ORDER_QTY, TOKEN):
        # 매수 후 잠깐 대기. 데이터를 위해. 어짜피 바로 매도안됨.
        wating_message(3, '매수 후 매수 평균 추출을 위한 대기...')
        sell_avg_prc, buy_avg_prc = save_account_data('AVG', dict_params)
        # 슬랙 메세지 전송
        dict_params = init_slack_params(start_date, end_date, STOCK_CD, STOCK_NM)
        dict_params['order_type'] = 'BUY'
        dict_params['ord_qty'] = ORDER_QTY
        dict_params['price'] = buy_avg_prc
        dict_params['buy_avg_price'] = buy_avg_prc
        dict_params['msg'] = slack_msg
        dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
        make_for_send_msg(dict_params)
        return True
    else:
        return False


# 계정별 매도 주문
def execute_sell(dict_params):
    start_date = dict_params['start_date']
    end_date = dict_params['end_date']
    OWNER = dict_params['OWNER']
    BASE_URL = dict_params['BASE_URL']
    APP_KEY = dict_params['APP_KEY']
    APP_SECRET = dict_params['APP_SECRET']
    ACC_NO = dict_params['ACC_NO']
    TOKEN = dict_params['TOKEN']
    STOCK_CD = dict_params['STOCK_CD']
    STOCK_NM = dict_params['STOCK_NM']
    ORDER_QTY = dict_params['ORDER_QTY']
    SLACK_WEBHOOK_URL  = dict_params['SLACK_WEBHOOK_URL']

    # 주문
    if TR.sell_stock(OWNER, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, STOCK_CD, ORDER_QTY, TOKEN):
        # 매수 후 잠깐 대기. 데이터를 위해. 어짜피 바로 매수안됨.
        wating_message(3, '매도 후 매도 평균 추출을 위한 대기...')
        sell_avg_prc, buy_avg_prc = save_account_data('AVG', dict_params)
        # 슬랙 메세지 전송
        dict_params = init_slack_params(start_date, end_date, STOCK_CD, STOCK_NM)
        dict_params['order_type'] = 'SELL'
        dict_params['ord_qty'] = ORDER_QTY
        dict_params['price'] = sell_avg_prc
        dict_params['buy_avg_price'] = buy_avg_prc
        sell_earn_rt = calc_earn_rt(sell_avg_prc, buy_avg_prc)
        if sell_earn_rt > 0.0:
            dict_params['result'] = 'UP'
            dict_params['msg'] = f"매도 후 {sell_earn_rt}% 이익. ^___^"
        else:
            dict_params['result'] = 'DN'
            dict_params['msg'] = f"매도 후 {sell_earn_rt}% 손실. ㅠㅠ"
        dict_params['slack_webhook_url'] = SLACK_WEBHOOK_URL
        # 매도에 대한 결과 메세지 전송
        make_for_send_msg(dict_params)
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
