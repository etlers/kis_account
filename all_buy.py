"""
    모든 계정의 매수 처리
"""
import param_value as PV # 파라미터 정보
import com_func as CF


# 거래에 관련한 모든 정보
config = CF.get_config_json()

# 인자로 받은 계정으로 설정
for dict_value in config["accounts"]:
    # 제외할 투자자 확인
    if dict_value['owner'] in PV.list_except_owner:
        continue
    # 로직에서 사용하게 되는 계정정보
    APP_KEY = dict_value['app_key']
    APP_SECRET = dict_value['app_secret']
    ACC_NO = dict_value['account_number']
    ORDER_QTY = dict_value['order_qty']
    SLACK_WEBHOOK_URL = dict_value['slack_webhook_url']
    # 토큰은 시작에서 한번만
    TOKEN = CF.get_token(dict_value['owner'], PV.BASE_URL, APP_KEY, APP_SECRET)
    # 거래 URL
    BASE_URL = PV.BASE_URL_DEV if dict_value['owner'] == 'DEV' else PV.BASE_URL_PROD
    # 거래를 위한 인자 딕셔너리
    dict_param_deal = {
        'start_date':PV.start_date,
        'end_date':PV.end_date,
        'OWNER':dict_value['owner'],
        'BASE_URL':BASE_URL,
        'APP_KEY':APP_KEY,
        'APP_SECRET':APP_SECRET,
        'ACC_NO':ACC_NO,
        'TOKEN':TOKEN,
        'STOCK_CD':PV.STOCK_CD,
        'STOCK_NM':PV.STOCK_NM,
        'ORDER_QTY':ORDER_QTY,
        'slack_msg':'강제 매수!!',
        'SLACK_WEBHOOK_URL':SLACK_WEBHOOK_URL,
        'preday_close_price':PV.preday_close_price,
    }
    # 계정별 지정한 수량으로 매수
    CF.execute_buy(dict_param_deal)
