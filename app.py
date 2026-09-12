import datetime
from FinMind.data import DataLoader
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 網頁頁面設定
st.set_page_config(
    page_title="台股籌碼與處置股綜合戰情室", page_icon="📈", layout="wide"
)

# 建立分頁標籤
tab1, tab2 = st.tabs(
    ["📈 低檔打底 + 投信鎖股選股", "🚨 處置股追蹤 (第二天 & 即將出關)"]
)

# ==========================================
# TAB 1: 低檔打底 + 投信鎖股策略
# ==========================================
with tab1:
  st.title("📈 台股投信鎖股 — 低檔打底突破選股儀表板")
  st.caption(
      "專注篩選：低檔盤整打底 + 投信積極買進 + K線突破 + 均線多頭排列 (Close > 5MA >"
      " 10MA > 20MA)"
  )

  # 側邊欄 controls
  st.sidebar.header("⚙️ 選股策略參數")
  min_days = st.sidebar.slider("投信最低連買天數", 1, 10, 2)
  min_ratio = (
      st.sidebar.slider("買超佔成交量最低比例 (%)", 1.0, 10.0, 2.5) / 100
  )
  max_cons_range = (
      st.sidebar.slider("近20日高低價波幅上限 (%)", 10.0, 35.0, 25.0) / 100
  )

  @st.cache_data(ttl=3600)
  def fetch_screener_data():
    try:
      dl = DataLoader()
      today = datetime.date.today()
      start_date = (today - datetime.timedelta(days=120)).strftime("%Y-%m-%d")
      end_date = today.strftime("%Y-%m-%d")

      watch_list = [
          "3081",
          "3450",
          "3163",
          "8358",
          "3035",
          "3661",
          "2349",
          "8046",
          "6451",
          "2455",
          "3017",
          "2383",
          "6274",
          "3231",
          "6669",
          "3583",
          "6187",
          "3680",
          "1519",
          "1513",
          "1504",
          "3324",
          "3533",
          "8054",
          "6176",
          "3363",
          "6223",
      ]
      all_data = []

      for stock_id in watch_list:
        try:
          df_price = dl.taiwan_stock_daily(
              stock_id=stock_id, start_date=start_date, end_date=end_date
          )
          df_inst = dl.taiwan_stock_institutional_investors(
              stock_id=stock_id, start_date=start_date, end_date=end_date
          )

          if (
              df_price is None
              or df_price.empty
              or df_inst is None
              or df_inst.empty
          ):
            continue

          df_sitc = (
              df_inst[df_inst["name"] == "Investment_Trust"]
              .groupby("date")["buy"]
              .sum()
              .reset_index()
          )
          df_sitc.rename(
              columns={"date": "date", "buy": "SITC_Buy"}, inplace=True
          )

          df_merged = pd.merge(df_price, df_sitc, on="date", how="left")
          df_merged["SITC_Buy"] = df_merged["SITC_Buy"].fillna(0)
          df_merged["StockID"] = stock_id
          all_data.append(df_merged)
        except Exception:
          continue

      if not all_data:
        return pd.DataFrame(), ""

      df_all = pd.concat(all_data, ignore_index=True)
      df_all["close"] = pd.to_numeric(df_all["close"], errors="coerce")
      df_all["high"] = (
          pd.to_numeric(df_all["max"], errors="coerce")
          if "max" in df_all.columns
          else df_all["close"]
      )
      df_all["low"] = (
          pd.to_numeric(df_all["min"], errors="coerce")
          if "min" in df_all.columns
          else df_all["close"]
      )
      df_all["Trading_Volume"] = pd.to_numeric(
          df_all["Trading_Volume"], errors="coerce"
      )

      df_all["MA5"] = df_all.groupby("StockID")["close"].transform(
          lambda x: x.rolling(5).mean()
      )
      df_all["MA10"] = df_all.groupby("StockID")["close"].transform(
          lambda x: x.rolling(10).mean()
      )
      df_all["MA20"] = df_all.groupby("StockID")["close"].transform(
          lambda x: x.rolling(20).mean()
      )

      df_all["High_20"] = df_all.groupby("StockID")["high"].transform(
          lambda x: x.rolling(20).max()
      )
      df_all["Low_20"] = df_all.groupby("StockID")["low"].transform(
          lambda x: x.rolling(20).min()
      )
      df_all["Consolidation_Range"] = (
          df_all["High_20"] - df_all["Low_20"]
      ) / df_all["Low_20"]

      df_all["SITC_Is_Buy"] = df_all["SITC_Buy"] > 0
      df_all["SITC_Consecutive_Days"] = df_all.groupby("StockID")[
          "SITC_Is_Buy"
      ].transform(lambda x: x.groupby((~x).cumsum()).cumsum())
      df_all["SITC_Ratio"] = df_all["SITC_Buy"] / (
          df_all["Trading_Volume"] / 1000
      )

      latest_date = df_all["date"].max()
      df_today = df_all[df_all["date"] == latest_date].copy()

      return df_today, latest_date
    except Exception as e:
      st.error(f"資料計算過程出錯: {e}")
      return pd.DataFrame(), ""

  with st.spinner("⏳ 正在分析盤整打底與均線多頭排列標的..."):
    df_today, latest_date = fetch_screener_data()

  if df_today.empty:
    st.warning("⚠️ 目前抓取資料為空，請確認是否為非交易日。")
  else:
    st.subheader(f"📅 最新交易日：{latest_date}")
    heavy_weights = ["2330", "2454", "2317", "2308", "2881", "2882"]

    df_filtered = df_today[
        (~df_today["StockID"].isin(heavy_weights))
        & (df_today["close"] > df_today["MA5"])
        & (df_today["MA5"] > df_today["MA10"])
        & (df_today["MA10"] > df_today["MA20"])
        & (df_today["Consolidation_Range"] <= max_cons_range)
        & (df_today["SITC_Consecutive_Days"] >= min_days)
        & (df_today["SITC_Ratio"] >= min_ratio)
    ]

    col1, col2 = st.columns(2)
    col1.metric("今日總監控標的", f"{len(df_today)} 檔")
    col2.metric("符合打底突破+多頭排列", f"{len(df_filtered)} 檔")

    st.markdown("---")

    if df_filtered.empty:
      st.info(
          "💡 今日尚無同時符合「低檔打底 + 均線多頭排列 (Close > 5MA > 10MA >"
          " 20MA) + 投信鎖股」的標的。"
      )
    else:
      display_df = df_filtered[[
          "StockID",
          "close",
          "SITC_Buy",
          "SITC_Consecutive_Days",
          "SITC_Ratio",
          "Consolidation_Range",
      ]].copy()
      display_df.columns = [
          "股票代號",
          "今日收盤價",
          "投信買超(張)",
          "投信連買天數",
          "買超佔成交量比",
          "近20日高低波幅",
      ]
      display_df["買超佔成交量比"] = display_df["買超佔成交量比"].apply(
          lambda x: f"{x:.2%}"
      )
      display_df["近20日高低波幅"] = display_df["近20日高低波幅"].apply(
          lambda x: f"{x:.1%}"
      )

      st.write(
          "🎯 **符合「低檔打底盤整 + 均線多頭順序排列 + 投信進場」之標的明細：**"
      )
      st.dataframe(display_df, use_container_width=True)


# ==========================================
# 輔助函式：繪製 K 線圖
# ==========================================
def draw_kline(df_stock, stock_id):
  df_stock = df_stock.sort_values("date")
  fig = go.Figure(
      data=[
          go.Candlestick(
              x=df_stock["date"],
              open=df_stock["open"],
              high=df_stock["max"],
              low=df_stock["min"],
              close=df_stock["close"],
              increasing_line_color="red",
              decreasing_line_color="green",
              name="K線",
          )
      ]
  )
  fig.update_layout(
      title=f"代號：{stock_id} 近60日日K線圖",
      xaxis_title="日期",
      yaxis_title="價格",
      xaxis_rangeslider_visible=False,
      height=350,
      margin=dict(l=20, r=20, t=40, b=20),
  )
  return fig


# ==========================================
# TAB 2: 處置股追蹤 (進處置第二天 & 即將出關)
# ==========================================
with tab2:
  st.title("🚨 處置股精準追蹤戰情室")
  st.caption(
      "自動監控台股交易所公佈之處置股票，追蹤「進處置第二天」與「下個交易日即將出關」之標的與日K型態"
  )

  dl = DataLoader()
  today = datetime.date.today()
  start_date = (today - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
  end_date = today.strftime("%Y-%m-%d")

  @st.cache_data(ttl=3600)
  def get_disposition_data():
    try:
      # 抓取證交所處置股票資訊
      df_disp = dl.taiwan_stock_disposition(
          start_date=start_date, end_date=end_date
      )
      if df_disp is None or df_disp.empty:
        return pd.DataFrame(), pd.DataFrame()

      # 取得股票名稱對照
      df_info = dl.taiwan_stock_info()
      df_disp = pd.merge(
          df_disp, df_info[["stock_id", "stock_name"]], on="stock_id", how="left"
      )

      # 日期轉換與處理
      df_disp["start_date"] = pd.to_datetime(df_disp["disposition_start_date"])
      df_disp["end_date"] = pd.to_datetime(df_disp["disposition_end_date"])

      # 取每檔股票最新的處置紀錄
      df_disp_latest = (
          df_disp.sort_values("start_date")
          .groupby("stock_id")
          .last()
          .reset_index()
      )

      today_dt = pd.to_datetime(today)

      # 1. 進處置第二天 (處置起始日 + 1個交易日左右)
      # 註：此處以曆日第 1~3 天間對應交易日第二天
      df_day2 = df_disp_latest[
          (today_dt - df_disp_latest["start_date"]).dt.days.between(1, 3)
      ].copy()

      # 2. 即將出關 (結束日為今天或下一個交易日)
      df_exiting = df_disp_latest[
          (df_disp_latest["end_date"] - today_dt).dt.days.between(0, 2)
      ].copy()

      return df_day2, df_exiting
    except Exception as e:
      st.error(f"處置股資料抓取失敗: {e}")
      return pd.DataFrame(), pd.DataFrame()

  with st.spinner("⏳ 正在讀取證交所處置公告與 K 線資料..."):
    df_day2, df_exiting = get_disposition_data()

  # 1. 進處置第二天專區
  st.subheader("🔥 1. 今日為「進處置第二天」之股票")
  if df_day2.empty:
    st.info("💡 今日無剛好進入處置第二天的標的。")
  else:
    for idx, row in df_day2.iterrows():
      sid = row["stock_id"]
      sname = row.get("stock_name", "未知")
      st.markdown(
          f"### 📌 **{sid} {sname}** (處置期間：{row['disposition_start_date']} ~"
          f" {row['disposition_end_date']})"
      )

      # 繪製日 K 線
      try:
        df_stock_k = dl.taiwan_stock_daily(
            stock_id=sid,
            start_date=(today - datetime.timedelta(days=90)).strftime(
                "%Y-%m-%d"
            ),
            end_date=end_date,
        )
        if not df_stock_k.empty:
          st.plotly_chart(
              draw_kline(df_stock_k, f"{sid} {sname}"), use_container_width=True
          )
      except Exception:
        st.write("暫無法載入該股 K 線圖。")

  st.markdown("---")

  # 2. 下個交易日即將出關專區
  st.subheader("🔓 2. 下個交易日「即將出關」之股票")
  if df_exiting.empty:
    st.info("💡 近期無即將出關的處置股票。")
  else:
    for idx, row in df_exiting.iterrows():
      sid = row["stock_id"]
      sname = row.get("stock_name", "未知")
      st.markdown(
          f"### 📌 **{sid} {sname}** (處置結束日：{row['disposition_end_date']})"
      )

      # 繪製日 K 線
      try:
        df_stock_k = dl.taiwan_stock_daily(
            stock_id=sid,
            start_date=(today - datetime.timedelta(days=90)).strftime(
                "%Y-%m-%d"
            ),
            end_date=end_date,
        )
        if not df_stock_k.empty:
          st.plotly_chart(
              draw_kline(df_stock_k, f"{sid} {sname}"), use_container_width=True
          )
      except Exception:
        st.write("暫無法載入該股 K 線圖。")
