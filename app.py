import sys
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ==========================================
# 頁面基本設定
# ==========================================
st.set_page_config(
    page_title="台股注意與處置股票分析網頁", page_layout="wide"
)

# ==========================================
# API 與資料擷取邏輯
# ==========================================


@st.cache_data(ttl=3600)
def fetch_notice_data():
  """擷取證交所/櫃買中心注意股資料"""
  try:
    url = "https://openapi.twse.com.tw/v1/announcement/notice"
    res = requests.get(url, timeout=10)
    if res.status_code == 200:
      df = pd.DataFrame(res.json())
      if not df.empty:
        df["Code"] = df["Code"].astype(str).str.strip()
        df["Name"] = df["Name"].astype(str).str.strip()
        return df
  except Exception as e:
    st.error(f"擷取注意股資料時發生錯誤: {e}")
  return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_disposition_data():
  """擷取證交所/櫃買中心處置股資料"""
  try:
    url = "https://openapi.twse.com.tw/v1/announcement/disposition"
    res = requests.get(url, timeout=10)
    if res.status_code == 200:
      df = pd.DataFrame(res.json())
      if not df.empty:
        df["Code"] = df["Code"].astype(str).str.strip()
        df["Name"] = df["Name"].astype(str).str.strip()
        return df
  except Exception as e:
    st.error(f"擷取處置股資料時發生錯誤: {e}")
  return pd.DataFrame()


@st.cache_data(ttl=1800)
def fetch_kline_data(stock_id, days=60):
  """動態產生個股 K 線資料 (可接證交所 API 或自訂 API，此處為實用擬真模擬數據範例)"""
  np.random.seed(hash(stock_id) % 2**32)
  end_date = datetime.now()
  dates = [
      (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
      for i in range(days, 0, -1)
  ]

  base_price = (hash(stock_id) % 200) + 50
  prices = [base_price]
  for _ in range(1, days):
    change = np.random.normal(0, 0.025)
    prices.append(max(10, prices[-1] * (1 + change)))

  k_data = []
  for d, p in zip(dates, prices):
    o = p * (1 + np.random.normal(0, 0.005))
    h = max(o, p) * (1 + abs(np.random.normal(0, 0.01)))
    l = min(o, p) * (1 - abs(np.random.normal(0, 0.01)))
    c = p
    v = int(abs(np.random.normal(3000, 1500)))
    k_data.append(
        {"date": d, "open": o, "max": h, "min": l, "close": c, "volume": v}
    )

  return pd.DataFrame(k_data)


# ==========================================
# 繪繪 K 線圖 (支援處置當天標籤與區間渲染)
# ==========================================
def draw_kline(df_stock, stock_title, start_dt=None, end_dt=None):
  df_stock = df_stock.sort_values("date")

  fig = go.Figure(
      data=[
          go.Candlestick(
              x=df_stock["date"],
              open=df_stock["open"],
              high=df_stock["max"],
              low=df_stock["min"],
              close=df_stock["close"],
              increasing_line_color="#d62728",  # 台股紅漲
              decreasing_line_color="#2ca02c",  # 台股綠跌
              name="K線",
          )
      ]
  )

  # 若有處置日期資訊，進行遮罩與標籤繪製
  if pd.notna(start_dt) and pd.notna(end_dt):
    s_str = (
        start_dt.strftime("%Y-%m-%d")
        if isinstance(start_dt, datetime)
        else str(start_dt)[:10]
    )
    e_str = (
        end_dt.strftime("%Y-%m-%d")
        if isinstance(end_dt, datetime)
        else str(end_dt)[:10]
    )

    # 1. 處置期間背景半透明橙黃色區間遮罩
    fig.add_vrect(
        x0=s_str,
        x1=e_str,
        fillcolor="rgba(255, 165, 0, 0.25)",
        layer="below",
        line_width=1,
        line_dash="dot",
        line_color="rgba(255, 140, 0, 0.7)",
    )

    # 2. 找到處置起始當天的 K 線最高價，精準標記紅色箭頭與浮動標籤
    df_start = df_stock[df_stock["date"] == s_str]
    if not df_start.empty:
      high_price = df_start["max"].values[0]
      fig.add_annotation(
          x=s_str,
          y=high_price,
          text="🚨 處置開始",
          showarrow=True,
          arrowhead=2,
          arrowsize=1,
          arrowwidth=2,
          arrowcolor="#d62728",
          ax=0,
          ay=-35,  # 上浮距離
          font=dict(size=12, color="white"),
          bgcolor="#d62728",
          bordercolor="#d62728",
          borderwidth=1,
          borderpad=4,
      )

  fig.update_layout(
      title=f"{stock_title} - 近60日日K線 (含處置當天與區間標記)",
      xaxis_title="日期",
      yaxis_title="價格 (TWD)",
      xaxis_rangeslider_visible=False,
      height=380,
      margin=dict(l=20, r=20, t=40, b=20),
      hovermode="x unified",
  )
  return fig


# ==========================================
# 資料預處理
# ==========================================
df_notice = fetch_notice_data()
df_disp = fetch_disposition_data()

# 模擬/清洗處置股票資料範例數據結構
disp_list = [
    {
        "Code": "6933",
        "Name": "AMAX-KY",
        "start_dt": datetime.now() - timedelta(days=9),
        "end_dt": datetime.now() + timedelta(days=1),
        "status": "即將出關",
        "detail": "第一次處置，每 5 分鐘人工撮合一次",
    },
    {
        "Code": "2330",
        "Name": "台積電",
        "start_dt": datetime.now() - timedelta(days=2),
        "end_dt": datetime.now() + timedelta(days=8),
        "status": "處置中",
        "detail": "第二次處置，每 20 分鐘人工撮合一次",
    },
    {
        "Code": "2454",
        "Name": "聯發科",
        "start_dt": datetime.now() - timedelta(days=1),
        "end_dt": datetime.now() + timedelta(days=9),
        "status": "處置第二天",
        "detail": "第一次處置，每 5 分鐘人工撮合一次",
    },
]
df_disp_demo = pd.DataFrame(disp_list)

# ==========================================
# 主頁面 UI 佈局
# ==========================================
st.title("📈 台股注意股與處置股即時監控儀表板")
st.caption(f"最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

tab1, tab2 = st.tabs(["🔥 今日注意股專區", "🚨 處置股追蹤專區"])

# ------------------------------------------
# TAB 1: 注意股
# ------------------------------------------
with tab1:
  st.subheader("📌 今日經證交所/櫃買中心公告之注意股票")
  if not df_notice.empty:
    st.dataframe(df_notice, use_container_width=True)
  else:
    st.info("目前無最新注意股資料或 API 連結中...")

# ------------------------------------------
# TAB 2: 處置股 (含 K 線處置當天標記)
# ------------------------------------------
with tab2:
  st.subheader("🚨 當前處置股票清單與 K 線追蹤")

  # 1. 總覽資料表
  st.dataframe(
      df_disp_demo[[
          "Code",
          "Name",
          "status",
          "start_dt",
          "end_dt",
          "detail",
      ]],
      use_container_width=True,
  )

  st.divider()

  # 2. 處置股票圖表展演
  st.subheader("📊 處置股票 K 線圖 (已標記處置當天與區間)")

  for _, row in df_disp_demo.iterrows():
    sid = row["Code"]
    sname = row["Name"]
    status_tag = row["status"]

    with st.expander(f"【{status_tag}】{sid} {sname}", expanded=True):
      col_info, col_chart = st.columns([1, 3])

      with col_info:
        st.markdown(f"**股票代號：** `{sid}`")
        st.markdown(f"**股票名稱：** {sname}")
        st.markdown(f"**目前狀態：** `{status_tag}`")
        st.markdown(
            f"**處置期間：**<br>`{row['start_dt'].strftime('%Y-%m-%d')}`<br>至"
            f" `{row['end_dt'].strftime('%Y-%m-%d')}`",
            unsafe_allow_html=True,
        )
        st.info(f"💡 **處置說明：**\n{row['detail']}")

      with col_chart:
        df_stock_k = fetch_kline_data(sid)

        # 👈 正確代入處置開始與結束日期進行當天標記與遮罩
        fig = draw_kline(
            df_stock_k,
            stock_title=f"{sid} {sname}",
            start_dt=row["start_dt"],
            end_dt=row["end_dt"],
        )
        st.plotly_chart(fig, use_container_width=True)
