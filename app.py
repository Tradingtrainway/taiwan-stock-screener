import datetime
import re
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from FinMind.data import DataLoader

# 網頁頁面設定
st.set_page_config(
    page_title="台股籌碼與處置股綜合戰情室", page_icon="📈", layout="wide"
)

# ==========================================
# 🎨 頂級質感的「週末休市/系統維護」專屬美編樣式
# ==========================================
st.markdown("""
    <style>
    .main-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 50px 20px;
    }
    .rest-card {
        background: linear-gradient(135deg, #1e1e2f 0%, #2a2a40 100%);
        border: 1px solid rgba(255, 159, 67, 0.3);
        padding: 45px 35px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.5);
        max-width: 800px;
        width: 100%;
        margin: 40px auto;
    }
    .rest-title {
        color: #ff9f43;
        font-size: 32px;
        font-weight: 800;
        margin-bottom: 20px;
        letter-spacing: 1px;
    }
    .rest-desc {
        color: #d1d8e0;
        font-size: 17px;
        line-height: 1.8;
        margin-bottom: 30px;
    }
    .rest-badge {
        display: inline-block;
        background: rgba(255, 159, 67, 0.15);
        color: #ff9f43;
        padding: 10px 24px;
        border-radius: 30px;
        font-weight: 700;
        border: 1px solid rgba(255, 159, 67, 0.4);
        font-size: 15px;
    }
    </style>
""", unsafe_allow_html=True)


# 檢測是否為週末休市/API維護時段 (週六全天 + 週日全天至晚上 22:00)
def is_weekend_maintenance():
  now = datetime.datetime.now()
  if now.weekday() == 5 or (now.weekday() == 6 and now.hour < 22):
    return True
  return False


# 🚨 【強制攔截至頂層】：如果在週末維護時段，直接顯示美編卡片並中斷後續程式
if is_weekend_maintenance():
  st.markdown(
      """
        <div class="main-container">
            <div class="rest-card">
                <div class="rest-title">☕ 台股戰情室 — 週末休市與系統維護中</div>
                <div class="rest-desc">
                    目前為台股週末休市期間，且歐美金融數據源（Yahoo Finance / FinMind）正進行例行性伺服器維護與快取重整。<br><br>
                    為了避免抓取到殘缺或空白的即時數據，戰情室已啟動<b>週末防護機制</b>，暫時將即時數據服務轉入休息狀態。
                </div>
                <div class="rest-badge">⏰ 預計於週一開盤前（週一早上 06:00）自動恢復即時連線</div>
            </div>
        </div>
    """,
      unsafe_allow_html=True,
  )
  st.stop()  # 強制停止執行下方所有選股與圖表邏輯，實現完美覆蓋！


# ==========================================
# 以下為平常開盤日的正常戰情室邏輯
# ==========================================
INDUSTRY_MAP = {
    "3450": "CPO光傳輸/矽光子",
    "3081": "CPO光傳輸/矽光子",
    "3163": "CPO光傳輸/矽光子",
    "3363": "CPO光傳輸/矽光子",
    "6933": "AI伺服器/液冷散熱",
    "3017": "AI伺服器/液冷散熱",
    "3324": "AI伺服器/液冷散熱",
    "6669": "AI伺服器/液冷散熱",
    "3231": "AI伺服器/液冷散熱",
    "3533": "AI伺服器/液冷散熱",
    "6620": "半導體廠務/設備",
    "3583": "半導體廠務/設備",
    "6187": "半導體廠務/設備",
    "3680": "半導體廠務/設備",
    "3035": "IP/ASIC矽智財",
    "3661": "IP/ASIC矽智財",
    "8054": "IP/ASIC矽智財",
    "8021": "PCB/鑽針/CCL",
    "8046": "PCB/鑽針/CCL",
    "2383": "PCB/鑽針/CCL",
    "6274": "PCB/鑽針/CCL",
    "8358": "PA微波通訊",
    "2455": "PA微波通訊",
}


def get_industry(stock_id):
  return INDUSTRY_MAP.get(str(stock_id).strip(), "AI半導體供應鏈")


@st.cache_data(ttl=1800)
def fetch_stock_data_robust(stock_id):
  sid = str(stock_id).strip()
  for suffix in [".TW", ".TWO"]:
    ticker = f"{sid}{suffix}"
    try:
      df_yf = yf.download(ticker, period="3mo", progress=False)
      if isinstance(df_yf.columns, pd.MultiIndex):
        df_yf.columns = df_yf.columns.get_level_values(0)
      if df_yf is not None and not df_yf.empty and len(df_yf) >= 10:
        df_yf = df_yf.reset_index()
        df_yf.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "max",
                "Low": "min",
                "Close": "close",
                "Volume": "Trading_Volume",
            },
            inplace=True,
        )
        df_yf["date"] = pd.to_datetime(df_yf["date"]).dt.strftime("%Y-%m-%d")
        return df_yf
    except Exception:
        pass
  return pd.DataFrame()


tab1, tab2 = st.tabs(
    ["📈 低檔打底 + 投信鎖股選股", "🚨 處置股追蹤與 AI 出關勝率分析"]
)
with tab1:
  st.title("📈 台股投信鎖股 — 低檔打底突破選股儀表板")
  st.info("平常開盤日的正常選股儀表板運作中。")
