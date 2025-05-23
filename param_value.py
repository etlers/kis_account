import com_func as CF

# 종목, OPEN API URL
BASE_URL_DEV = "https://openapivts.koreainvestment.com:29443"
BASE_URL_PROD  = "https://openapi.koreainvestment.com:9443"

# 투자자 거래정보
dict_value = CF.get_owner_config(args.owner)
# 인자로 받은 계정으로 설정
APP_KEY = dict_value['app_key']
APP_SECRET = dict_value['app_secret']
ACC_NO = dict_value['account_number']
ORDER_QTY = dict_value['order_qty']
STOCK_CD = dict_value['stock_code']
STOCK_NM = dict_value['stock_name']
SLACK_WEBHOOK_URL = dict_value['slack_webhook_url']

# 시각 정의
START_DEAL_TM = '090000'  # 매수 시작 시간
END_DEAL_TM = '151500'  # 매도 마감 시간
NO_MORE_BUY_CHK_TM = '133000'  # 더이상 매수하지 ㅇ낳는 시간
IN_START_BUY_TM = '093000'  # 매수 시작 시간 기준
RISE_EARLY_CHK_TM_START = '090300'  # 장초반 급상승 체크 시작 시간
RISE_EARLY_CHK_TM_END = '090500'  # 장초반 급상승 체크 종료 시간
DOWN_IN_LOW_RATE_TM = '110000'  # 매수를 위한 하락비율 체크 시간

# 직전 거래일 정보 확인
dict_last_info = CF.get_previous_trading_info(STOCK_CD)
preday_updn_rt = dict_last_info['change_percent']  # 전일대비 상승하락 비율
preday_close_price = int(dict_last_info['close_price'])  # 전일 종가

# 매수, 매도 한글 설명 값
dict_deal_desc = {
    'BUY':'매수',
    'SELL':'매도',
}

# 일자 파라미터. 당일
start_date = CF.get_current_time().split(' ')[0]
end_date   = CF.get_current_time().split(' ')[0]

# 일괄 처리 제외할 대상
list_except_owner = [
    'ETLERS',
]

# 상태메세지 전송시각
list_buy_status_tm = [
    '100000',
    '110000',
    '120000',
    '130000',
    '140000',
    '150000',
]

# 매도 상태메세지 전송시각
list_sell_status_tm = [
    '100000', '103000',
    '110000', '113000',
    '120000', '123000',
    '130000', '133000',
    '140000', '143000',
    '150000', '153000',
]
