import os
import json
import time
import requests

import com_func as CF

DELAY_SEC = 0.5  # 대기 시간 (초)


# 대표 계정으로 현재가 조회
def get_current_price(base_url, app_key, app_secret, token, stock_code):
    time.sleep(DELAY_SEC)

    url = f'{base_url}/uapi/domestic-stock/v1/quotations/inquire-price'
    tr_id = "FHKST01010100"

    headers = {
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id
    }
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": stock_code
    }
    response = requests.get(url, headers=headers, params=params)
    res = requests.get(url, headers=headers, params=params).json()
    sise = res.get("output", {}).get("stck_prpr", "-9999")
    
    return int(sise)


# 예수금 조회
def get_deposit(owner, base_url, app_key, app_secret, acc_no, stock_code, token):
    time.sleep(DELAY_SEC)

    url = f'{base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-order'
    tr_id = "TTTC8908R"
    tr_id = CF.set_real_tr_id(tr_id) if owner == 'DEV' else tr_id
    
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
    }

    params = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": "01",
        "PDNO": stock_code,
        "ORD_UNPR": "0",
        "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "N",
        "OVRS_ICLD_YN": "N"
        }
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        deposit = int(data['output']['ord_psbl_cash'])  # 매수 가능 금액
    except:
        deposit = 0
    
    return deposit


# 매도를 위한 계좌 수량 추출
def get_stock_info(owner, base_url, app_key, app_secret, acc_no, token):
    time.sleep(DELAY_SEC)

    url = f'{base_url}/uapi/domestic-stock/v1/trading/inquire-balance'
    tr_id = "TTTC8434R"
    tr_id = CF.set_real_tr_id(tr_id) if owner == 'DEV' else tr_id

    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id, 
    }

    params = {
        "CANO": acc_no,
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
        "account": owner,
        'stock_qty' : 0,
        'stock_avg_prc' : 0,
        'buy_abl_amt' : 0,
        'total_eval_amt' : 0,
        'bf_asset_eval_amt' : 0,
    }

    try:
        if response.status_code == 200:
            # 거래를 위한 재고 및 매수 가능금액
            dict_result['stock_qty'] = int(float(data['output1'][0]['hldg_qty']))
            dict_result['stock_avg_prc'] = int(float(data['output1'][0]['pchs_avg_pric']))
            # 거래 종료에 대한 통계 
            dict_result['buy_abl_amt'] = data['output2'][0]['dnca_tot_amt']
            dict_result['total_eval_amt'] = data['output2'][0]['tot_evlu_amt']
            dict_result['bf_asset_eval_amt'] = data['output2'][0]['bfdy_tot_asst_evlu_amt']

            return dict_result
        else:
            # print(f"❌ 잔고 조회 실패: {response.status_code}")
            return dict_result
    except Exception as e:
        # print("❌ 잔고 조회 실패:", json.dumps(data, indent=2, ensure_ascii=False))
        return dict_result



# 일자별 매매 체결내역 조회
def get_last_buy_trade(owner, start_date, end_date, BASE_URL, APP_KEY, APP_SECRET, ACC_NO, ACNT_PRDT_CD, ACCESS_TOKEN, SLL_BUY_DVSN_CD='00'):
    time.sleep(DELAY_SEC)

    if owner == 'DEV':
        return None

    url = f'{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld'
    tr_id = "TTTC8001R"
    tr_id = CF.set_real_tr_id(tr_id) if owner == 'DEV' else tr_id

    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id,  # (신)TTTC0081R  (구)TTTC8001R
    }

    params = {
        "CANO": ACC_NO,
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
    print(data)
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
def last_deal_avg_price(owner, base_url, app_key, app_secret, acc_no, token, start_date, end_date, div='매수'):
    dict_result = {
        "account": owner,
        "div": div,
        "last_deal_avg_prc": 0,
    }

    dict_deal_div = {
        '매도': '01',
        '매수': '02',
    }
    
    if owner == 'DEV':
        return dict_result
    
    try:
        list_dict_result = get_last_buy_trade(
                owner, base_url, app_key, app_secret, acc_no, token, start_date, end_date, dict_deal_div[div]
            )
        
        # 마지막부터 읽고자 역으로 재생성
        list_dict_result.reverse()
        avg_prc = int(list_dict_result[0]['AVG_PRC']) if len(list_dict_result) > 0 else 0

        dict_result["last_deal_avg_prc"] = avg_prc
    except:
        pass
        
    return dict_result


# 전량 시장가 매도
def sell_stock(owner, base_url, app_key, app_secret, acc_no, stock_code, ord_qty, token):
    time.sleep(DELAY_SEC)

    url = f'{base_url}/uapi/domestic-stock/v1/trading/order-cash'
    tr_id = "TTTC0801U"
    tr_id = CF.set_real_tr_id(tr_id) if owner == 'DEV' else tr_id

    sell_headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id  # 모의투자 현금 매도 주문
    }

    sell_payload = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": '01',
        "PDNO": stock_code,  # 종목 코드
        "ORD_QTY": ord_qty,  # 보유 수량 전체 매도
        "ORD_UNPR": "0",  # 시장가 주문
        "ORD_DVSN": "01",  # 시장가 매도
        "ORD_PRCS_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "N",
        "OSLP_YN": "N"
    }
    sell_response = requests.post(url, headers=sell_headers, data=json.dumps(sell_payload))

    if sell_response.status_code == 200:
        print(f"✅ {owner}] {stock_code} {ord_qty}주 매도 주문 성공!")
        return True
    else:
        print(f"🚨 {owner}] 매도 주문 실패:", sell_response.json())
        return False


# 매수 처리
def buy_stock(owner, base_url, app_key, app_secret, acc_no, stock_code, ord_qty, token):
    time.sleep(DELAY_SEC)

    url = f'{base_url}/uapi/domestic-stock/v1/trading/order-cash'
    tr_id = "TTTC0802U"
    tr_id = CF.set_real_tr_id(tr_id) if owner == 'DEV' else tr_id

    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id  # 모의투자 현금 매수 주문
    }

    order_payload = {
        "CANO": acc_no,  # 계좌번호
        "ACNT_PRDT_CD": '01',
        "PDNO": stock_code,  # 종목코드
        "ORD_QTY": ord_qty,  # 주문수량
        "ORD_UNPR": '0',  # 시장가는 0 입력
        "ORD_DVSN": '01',  # 시장가 주문 (01)
        "ORD_PRCS_DVSN": "01",  # 주문처리구분 (01: 시장가)
        "CMA_EVLU_AMT_ICLD_YN": "N",  # CMA 평가금액 포함 여부
        "OSLP_YN": "N"  # 공매도 여부 (N: 일반 매수)
    }
    print(order_payload)

    order_response = requests.post(url, headers=headers, data=json.dumps(order_payload))

    # 주문 결과 출력
    if order_response.status_code == 200:
        print("📌 주문 성공:", order_response.json())
        return True
    else:
        print("🚨 주문 실패:", order_response.json())
        return False
    