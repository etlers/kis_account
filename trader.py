import os
import json
import time
import requests

import com_func as CF


BASE_URL = "https://openapi.koreainvestment.com:9443"
DELAY_SEC = 0.5  # 대기 시간 (초)
    

def get_token(account_info):
    TOKEN_FILE = f"./token/token_cache_{account_info['owner']}.json"
    
    def save_token(token_data):
        """ 액세스 토큰을 JSON 파일에 저장 """
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)


    def load_token():
        """ JSON 파일에서 액세스 토큰을 불러옴 """
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                return json.load(f)
        return None


    def request_new_token():
        """ 새로운 Access Token을 요청 """
        url = f"{BASE_URL}/oauth2/tokenP"
        print(url)
        payload = {
            "grant_type": "client_credentials",
            "appkey": account_info['app_key'],
            "appsecret": account_info['app_secret'],
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
        

    def get_access_token():
        """ Access Token을 불러오거나 만료되었으면 새로 발급 """
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
    
    token = get_access_token()
    return token


# 대표 계정으로 현재가 조회
def get_current_price(account_info, delay_sec = 0.25, jongmok_code = "229200", jongmok_name = "KODEX 150 ETF"):
    time.sleep(delay_sec) # 대기 시간 추가
    try:
        token = get_token(account_info)
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": account_info["app_key"],
            "appsecret": account_info["app_secret"],
            "tr_id": "FHKST01010100"
        }
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": jongmok_code
        }
        url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
        res = requests.get(url, headers=headers, params=params).json()
        price = res.get("output", {}).get("stck_prpr", "N/A")
        # print(f"[{account_info['owner']}] {jongmok_name} 현재가: {price}")
        return int(price.replace(",", "").replace("N/A", "-999"))  # N/A인 경우 0으로 처리
    except Exception as e:
        print(f"[{account_info['owner']}] Error: {e}")
        return -999


def get_balance(account_info):
    token = get_token(account_info)
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": account_info["app_key"],
        "appsecret": account_info["app_secret"],
        "tr_id": "TTTC8434R",
        "custtype": "P",
        "content-type": "application/json"
    }
    params = {
        "CANO": account_info["account_number"],
        "ACNT_PRDT_CD": '01',
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance"
    res = requests.get(url, headers=headers, params=params).json()
    dict_result = {
        "account": account_info["owner"],
        "balance": res.get("output1", [])
    }

    return dict_result


# 예수금 조회
def get_deposit(account_info):
    time.sleep(DELAY_SEC)
    token = get_token(account_info)
    url = f'{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-order'
    
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": account_info["app_key"],
        "appsecret": account_info["app_secret"],
        "tr_id": "TTTC8908R",
    }

    params = {
        "CANO": account_info["account_number"],
        "ACNT_PRDT_CD": "01",
        "PDNO": account_info["stock_code"],
        "ORD_UNPR": "0",
        "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "N",
        "OVRS_ICLD_YN": "N"
        }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    deposit = int(data['output']['ord_psbl_cash'])  # 매수 가능 금액
    dict_result = {
        "account": account_info["owner"],
        "deposit": deposit,
    }
    return dict_result


# 매도를 위한 계좌 수량 추출
def get_stock_info(account_info, alarm='N'):
    time.sleep(DELAY_SEC)
    token = get_token(account_info)
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"

    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": account_info["app_key"],
        "appsecret": account_info["app_secret"],
        "tr_id": "TTTC8434R", 
    }

    params = {
        "CANO": account_info["account_number"],
        "ACNT_PRDT_CD": '01',
        "AFHR_FLPR_YN": "N",  # 시간외 단일가 여부
        "OFL_YN": "N",  # 오프라인 여부
        "INQR_DVSN": "01",  # 조회구분코드 (01: 종목별)
        "UNPR_DVSN": "01",  # 단가구분코드 (01: 기준가)
        "FUND_STTL_ICLD_YN": "N",  # 펀드결제분 포함 여부
        "FNCG_AMT_AUTO_RDPT_YN": "N",  # 융자금액 자동상환 여부
        "PRCS_DVSN": "01",  # 처리구분코드
        "CTX_AREA_FK100": "",  # 연속조회검색조건1
        "CTX_AREA_NK100": "",  # 연속조회검색조건2
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    dict_result = {
        "account": account_info["owner"],
        'stock_cnt' : -999,
        'stock_avg_prc' : -999,
        'buy_abl_amt' : -999,
        'total_eval_amt' : -999,
        'bf_asset_eval_amt' : -999,
    }

    try:
        if response.status_code == 200:
            # 거래를 위한 재고 및 매수 가능금액
            dict_result['stock_cnt'] = int(float(data['output1'][0]['hldg_qty']))
            dict_result['stock_avg_prc'] = int(float(data['output1'][0]['pchs_avg_pric']))
            # 거래 종료에 대한 통계 
            dict_result['buy_abl_amt'] = data['output2'][0]['dnca_tot_amt']
            dict_result['total_eval_amt'] = data['output2'][0]['tot_evlu_amt']
            dict_result['bf_asset_eval_amt'] = data['output2'][0]['bfdy_tot_asst_evlu_amt']

            return dict_result
        else:
            print(f"❌ 잔고 조회 실패: {response.status_code}")
            return dict_result
    except Exception as e:
        # print("❌ 잔고 조회 실패:", json.dumps(data, indent=2, ensure_ascii=False))
        return dict_result



# 일자별 매매 체결내역 조회
def get_last_buy_trade(account_info, start_date, end_date, SLL_BUY_DVSN_CD='00'):
    time.sleep(DELAY_SEC)
    token = get_token(account_info)
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"

    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": account_info["app_key"],
        "appsecret": account_info["app_secret"],
        "tr_id": "TTTC8001R",  # (신)TTTC0081R  (구)TTTC8001R
    }

    params = {
        "CANO": account_info["account_number"],
        "ACNT_PRDT_CD": '01',
        "INQR_STRT_DT": start_date,
        "INQR_END_DT": end_date,
        "SLL_BUY_DVSN_CD": SLL_BUY_DVSN_CD,  # 00, 01=매도, 02=매수
        "INQR_DVSN": "1",  # 종목별
        "PDNO": "",  # 종목코드 비워두면 전체
        "CCLD_DVSN": "01",  # 체결구분: 01=정상
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "01",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    i = 0
    list_dict_sell = []
    for dict_data in data['output1']:
        i += 1
        list_dict_sell.append(
            {
                "SEQ": i,
                "DIV": dict_data.get("sll_buy_dvsn_cd_name", ""),
                "DEAL_DT": dict_data.get("ord_dt", ""),
                "DEAL_TM": int(dict_data.get("ord_tmd", 0)),
                "STOCK_NM": dict_data.get("prdt_name", ""),
                "AVG_PRC": int(dict_data.get("avg_prvs", 0)),
                "TOT_QTY": int(dict_data.get("tot_ccld_qty", 0)),
                "TOT_AMT": int(dict_data.get("tot_ccld_amt", 0)),
            }
        )

    try:
        return list_dict_sell
    except Exception as e:
        return f"Error parsing data: {e}"


# 마지막 매도(또는 매수)의 평균 단가만 가져오기
def last_deal_avg_price(account_info, start_date, end_date, div='매수'):
    dict_deal_div = {
        '매도': '01',
        '매수': '02',
    }
    list_dict_result = get_last_buy_trade(account_info, start_date, end_date, dict_deal_div[div])
    
    # 마지막부터 읽고자 역으로 재생성
    list_dict_result.reverse()
    avg_prc = int(list_dict_result[0]['AVG_PRC']) if len(list_dict_result) > 0 else 0

    dict_result = {
        "account": account_info["owner"],
        "div": div,
        "last_deal_avg_prc": avg_prc,
    }
        
    return dict_result


# 전량 시장가 매도
def sell_stock(account_info, ord_qty):
    time.sleep(DELAY_SEC)
    token = get_token(account_info)
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"

    sell_headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": account_info["app_key"],
        "appsecret": account_info["app_secret"],
        "tr_id": "TTTC0801U"  # 모의투자 현금 매도 주문
    }

    sell_payload = {
        "CANO": account_info["account_number"],
        "ACNT_PRDT_CD": '01',
        "PDNO": account_info["stock_code"],  # 종목 코드
        "ORD_QTY": ord_qty,  # 보유 수량 전체 매도
        "ORD_UNPR": "0",  # 시장가 주문
        "ORD_DVSN": "01",  # 시장가 매도
        "ORD_PRCS_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "N",
        "OSLP_YN": "N"
    }
    sell_response = requests.post(url, headers=sell_headers, data=json.dumps(sell_payload))

    if sell_response.status_code == 200:
        print(f"✅ {account_info["owner"]}] {account_info["stock_code"]} {ord_qty}주 매도 주문 성공!")
        return True
    else:
        print(f"🚨 {account_info["owner"]}] 매도 주문 실패:", sell_response.json())
        return False

# 매수 처리
def buy_stock(account_info, ord_qty):
    time.sleep(DELAY_SEC)
    token = get_token(account_info)
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"

    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": account_info["app_key"],
        "appsecret": account_info["app_secret"],
        "tr_id": "TTTC0802U"  # 모의투자 현금 매수 주문
    }

    order_payload = {
        "CANO": account_info["account_number"],  # 계좌번호
        "ACNT_PRDT_CD": '01',
        "PDNO": account_info['stock_code'],  # 종목코드
        "ORD_QTY": ord_qty,  # 주문수량
        "ORD_UNPR": "0",  # 시장가는 0 입력
        "ORD_DVSN": '01',  # 시장가 주문 (01)
        "ORD_PRCS_DVSN": "01",  # 주문처리구분 (01: 시장가)
        "CMA_EVLU_AMT_ICLD_YN": "N",  # CMA 평가금액 포함 여부
        "OSLP_YN": "N"  # 공매도 여부 (N: 일반 매수)
    }

    order_response = requests.post(url, headers=headers, data=json.dumps(order_payload))

    # 주문 결과 출력
    if order_response.status_code == 200:
        print("📌 주문 성공:", order_response.json())
        return True
    else:
        print("🚨 주문 실패:", order_response.json())
        return False
    