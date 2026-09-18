import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_disposition_stocks(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # 觸發 HTTP 4xx / 5xx 異常
        
        # 先檢查內容是否為空
        if not response.text.strip():
            print("目前無處置股票資料，或今日為非營業日。")
            return []

        return response.json()

    except json.JSONDecodeError:
        print("解析 JSON 失敗！伺服器可能回傳了 HTML 擋牆，前 200 字內容：")
        print(response.text[:200])
        return []
    except requests.exceptions.RequestException as e:
        print(f"網路請求錯誤: {e}")
        return []
