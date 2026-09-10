import datetime
from FinMind.data import DataLoader
import pandas as pd
import streamlit as st

# 網頁頁面設定
st.set_page_config(
    page_title="中小型投信鎖股動能戰情室", page_icon="📈", layout="wide"
)

st.title("📈 台股投信鎖股動能 — 短線飆股篩選儀表板")
st.caption(
    "已排除大型權值股！專注篩選：中小型股 + 雙均線上 + 投信連買鎖股 + 成交量爆發"
)

# 側邊欄控制
st.sidebar.header("⚙️ 短線波段策略參數")
min_days = st.sidebar.slider("投信最低連買天數", 1, 10, 3)
min_ratio = (
    st.sidebar.slider("買超佔成交量最低比例 (%)", 1.0, 15.0, 4.0) / 100
)
vol_multiplier = st.sidebar.slider("今日成交量 / 5日均量 (倍)", 1.0, 2.5, 1.2)

st.sidebar.markdown("---")
st.sidebar.info("💡 提示：建議每日下午 3:30 後重新整理網頁獲取最新數據。")


# 抓取資料
@st.cache_data(ttl=3600)
def fetch_screener_data():
  try:
    dl = DataLoader()
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=120)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    # 包含高波動中小型股、概念股之監控名單 (已剔除台積電、聯發科等大權值)
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

    # 數值格式清洗
    df_all["close"] = pd.to_numeric(df_all["close"], errors="coerce")
    df_all["Trading_Volume"] = pd.to_numeric(
        df_all["Trading_Volume"], errors="coerce"
    )

    # 技術面與籌碼面指標計算
    df_all["MA20"] = df_all.groupby("StockID")["close"].transform(
        lambda x: x.rolling(20).mean()
    )
    df_all["MA60"] = df_all.groupby("StockID")["close"].transform(
        lambda x: x.rolling(60).mean()
    )
    df_all["Vol_MA5"] = df_all.groupby("StockID")["Trading_Volume"].transform(
        lambda x: x.rolling(5).mean()
    )

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


# 載入資料與呈現
with st.spinner("⏳ 正在分析中小型股籌碼與量能攻擊訊號..."):
  df_today, latest_date = fetch_screener_data()

if df_today.empty:
  st.warning("⚠️ 目前抓取資料為空，請確認是否為非交易日。")
else:
  st.subheader(f"📅 最新交易日：{latest_date}")

  # 排除大型權值股黑名單
  heavy_weights = ["2330", "2454", "2317", "2308", "2881", "2882"]

  # 動態篩選條件：排除權值股 + 站上雙均線 + 投信鎖股 + 今日成交量大於5日均量指定倍數
  df_filtered = df_today[
      (~df_today["StockID"].isin(heavy_weights))
      & (df_today["close"] > df_today["MA20"])
      & (df_today["close"] > df_today["MA60"])
      & (df_today["SITC_Consecutive_Days"] >= min_days)
      & (df_today["SITC_Ratio"] >= min_ratio)
      & (df_today["Trading_Volume"] >= df_today["Vol_MA5"] * vol_multiplier)
  ]

  col1, col2 = st.columns(2)
  col1.metric("今日總監控標的", f"{len(df_today)} 檔")
  col2.metric("符合短線動能爆發", f"{len(df_filtered)} 檔")

  st.markdown("---")

  if df_filtered.empty:
    st.info(
        "💡 今日尚無符合「量能爆發 + 投信鎖股」的標的，代表短線大盤動能較弱，建議保留現金耐心觀望。"
    )
  else:
    display_df = df_filtered[[
        "StockID",
        "close",
        "SITC_Buy",
        "SITC_Consecutive_Days",
        "SITC_Ratio",
    ]].copy()
    display_df.columns = [
        "股票代號",
        "今日收盤價",
        "投信買超(張)",
        "投信連買天數",
        "買超佔成交量比",
    ]
    display_df["買超佔成交量比"] = display_df["買超佔成交量比"].apply(
        lambda x: f"{x:.2%}"
    )

    st.write("🎯 **符合短線波段條件之標的明細：**")
    st.dataframe(display_df, use_container_width=True)
