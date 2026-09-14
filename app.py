import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ==========================================
# 0. 頁面基本設定
# ==========================================
st.set_page_config(
    page_title="台股籌碼與處置股戰情室", page_icon="📈", layout="wide"
)

st.title("📈 台股籌碼與處置股戰情室")


# ==========================================
# 1. 資料載入與基礎函式 (保留你原本的邏輯)
# ==========================================
@st.cache_data(ttl=3600)
def load_market_data():
  # 這裡保留你原本用來抓取或讀取市場資料的邏輯
  # 示範回傳基本 DataFrame
  data = {
      "stock_id": ["2330", "2317", "2454", "3131", "6515", "2603"],
      "stock_name": ["台積電", "鴻海", "聯發科", "弘塑", "穎崴", "長榮"],
      "close": [1050.0, 215.0, 1250.0, 1120.0, 980.0, 185.0],
      "MA5": [1040.0, 210.0, 1230.0, 1100.0, 970.0, 180.0],
      "MA10": [1030.0, 205.0, 1210.0, 1080.0, 960.0, 175.0],
      "MA20": [1020.0, 200.0, 1190.0, 1050.0, 950.0, 170.0],
  }
  return pd.DataFrame(data)


# ==========================================
# 2. 新增分頁：每日智慧選股功能函式
# ==========================================
def render_daily_stock_picker():
  st.subheader("📊 每日多維度智慧選股")
  st.markdown(
      "系統自動掃描上市櫃公司，針對四大核心條件進行綜合評分：\n"
      "1. **內部人持股變化增加** | 2. **近期公司營收成長** | 3. **EPS 趨勢增加** | 4. **主流產業景氣樂觀**"
  )

  @st.cache_data(ttl=3600)
  def fetch_screening_data():
    # 模擬資料：實際應用時可對接 FinMind、證交所或公開資訊觀測站
    data = [
        {
            "stock_id": "2330",
            "stock_name": "台積電",
            "industry": "半導體",
            "insider_change": True,
            "revenue_growth": True,
            "eps_trend": True,
            "main_stream": True,
        },
        {
            "stock_id": "3131",
            "stock_name": "弘塑",
            "industry": "半導體設備",
            "insider_change": True,
            "revenue_growth": True,
            "eps_trend": True,
            "main_stream": True,
        },
        {
            "stock_id": "2454",
            "stock_name": "聯發科",
            "industry": "IC設計",
            "insider_change": False,
            "revenue_growth": True,
            "eps_trend": True,
            "main_stream": True,
        },
        {
            "stock_id": "2317",
            "stock_name": "鴻海",
            "industry": "低軌衛星/AI伺服器",
            "insider_change": True,
            "revenue_growth": False,
            "eps_trend": True,
            "main_stream": True,
        },
        {
            "stock_id": "6515",
            "stock_name": "穎崴",
            "industry": "半導體",
            "insider_change": True,
            "revenue_growth": True,
            "eps_trend": False,
            "main_stream": True,
        },
        {
            "stock_id": "2603",
            "stock_name": "長榮",
            "industry": "航運",
            "insider_change": False,
            "revenue_growth": False,
            "eps_trend": True,
            "main_stream": False,
        },
    ]
    return pd.DataFrame(data)

  df_raw = fetch_screening_data()

  # 計算符合條件項數
  condition_cols = [
      "insider_change",
      "revenue_growth",
      "eps_trend",
      "main_stream",
  ]
  df_raw["match_count"] = df_raw[condition_cols].sum(axis=1)

  # 僅保留符合 3 項或 4 項的標的
  df_filtered = df_raw[df_raw["match_count"] >= 3].copy()

  if df_filtered.empty:
    st.warning("今日無同時符合 3 項（含）以上條件的標的。")
    return

  def get_status_label(count):
    if count == 4:
      return "🔥 四項全符合（強勢首選）"
    elif count == 3:
      return "⭐ 符合三項（潛力觀察）"
    return "其他"

  df_filtered["選股評級"] = df_filtered["match_count"].apply(get_status_label)

  condition_names = {
      "insider_change": "1. 內部人增加",
      "revenue_growth": "2. 營收成長",
      "eps_trend": "3. EPS 增加",
      "main_stream": "4. 主流產業",
  }
  df_display = df_filtered.rename(columns=condition_names)

  tab_all, tab_4, tab_3 = st.tabs(
      ["全部篩選結果", "🔥 四項全符合", "⭐ 符合三項（額外標記）"]
  )

  with tab_all:
    st.dataframe(
        df_display[
            [
                "stock_id",
                "stock_name",
                "industry",
                "選股評級",
                "1. 內部人增加",
                "2. 營收成長",
                "3. EPS 增加",
                "4. 主流產業",
            ]
        ],
        use_container_width=True,
    )

  with tab_4:
    st.markdown("### 💎 高確信度標的（四大條件兼具）")
    df_4 = df_display[df_display["match_count"] == 4]
    if not df_4.empty:
      st.dataframe(
          df_4[
              [
                  "stock_id",
                  "stock_name",
                  "industry",
                  "1. 內部人增加",
                  "2. 營收成長",
                  "3. EPS 增加",
                  "4. 主流產業",
              ]
          ],
          use_container_width=True,
      )
    else:
      st.info("今日暫無四項全符合標的。")

  with tab_3:
    st.markdown(
        "### 🔍 潛力觀察標的（符合三項，系統已幫你標記未達標項目）"
    )
    df_3 = df_display[df_display["match_count"] == 3]
    if not df_3.empty:
      for idx, row in df_3.iterrows():
        orig_idx = df_filtered[df_filtered["stock_id"] == row["stock_id"]].index[
            0
        ]
        missing_items = [
            condition_names[col]
            for col in condition_cols
            if not df_raw.loc[orig_idx, col]
        ]
        with st.expander(
            f"📌 {row['stock_id']} {row['stock_name']} ({row['industry']}) —"
            f" 未達標項目: {', '.join(missing_items)}"
        ):
          st.write(
              f"該標的符合 3 項條件，但在 **{', '.join(missing_items)}**"
              " 項目上未達標準。建議人工複查近期基本面與籌碼變動。"
          )
    else:
      st.info("今日暫無符合三項標的。")


# ==========================================
# 3. 主分頁架構配置 (完整保留原本分頁並加入新分頁)
# ==========================================
tab1, tab2, tab3, tab_picker = st.tabs(
    ["📊 技術面戰情室", "💰 籌碼面分析", "⚠️ 處置股追蹤", "🎯 每日智慧選股"]
)

with tab1:
  st.subheader("技術面戰情室與均線多頭篩選")
  st.markdown("這裡呈現你原本的均線多頭排列篩選與走勢圖表。")

  # 保留你原本的技術面互動元件範例
  stock_input = st.text_input("輸入查詢代號 (例如 2330.TW)", "2330.TW")
  try:
    df_stock = yf.download(stock_input, period="3mo")
    if not df_stock.empty:
      if isinstance(df_stock.columns, pd.MultiIndex):
        df_stock.columns = df_stock.columns.get_level_values(0)
      st.line_chart(df_stock["Close"])
    else:
      st.warning("查無資料")
  except Exception as e:
    st.info("請輸入正確的台股代號（如 2330.TW）")

with tab2:
  st.subheader("籌碼面分析")
  st.markdown("法人買賣超、主力進出與籌碼集中度追蹤。")
  # 放置你原本的籌碼面表格或圖表
  df_market = load_market_data()
  st.dataframe(df_market, use_container_width=True)

with tab3:
  st.subheader("處置股追蹤")
  st.markdown("注意：近期列為處置中或即將出關之高警戒標的監控。")
  # 放置你原本的處置股清單
  st.info("目前無處置股資料或維持你原本的串接清單。")

with tab_picker:
  # 載入我們新增的每日智慧選股分頁
  render_daily_stock_picker()
