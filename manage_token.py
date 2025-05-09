import os
import requests
import json
import time
import kis_auth as KA

if KA.PROD == 'Y':
    APP_KEY = KA.PROD_APP_KEY
    APP_SECRET = KA.PROD_APP_SECRET
    ACC_NO = KA.PROD_ACC_NO
    BASE_URL = KA.PROD_BASE_URL
else:
    APP_KEY = KA.DEV_APP_KEY
    APP_SECRET = KA.DEV_APP_SECRET
    ACC_NO = KA.DEV_ACC_NO
    BASE_URL = KA.DEV_BASE_URL

# 투자자별 Access Token 저장 파일
token_path = f'./config/{KA.OWNER}/'
if not os.path.exists(token_path):
    os.makedirs(token_path)
TOKEN_FILE = f"{token_path}access_token.json"  


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
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
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


if __name__ == '__main__':
    token = get_access_token()
