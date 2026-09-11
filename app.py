import datetime
from FinMind.data import DataLoader
import pandas as pd
import streamlit as st

# 網頁頁面設定
st.set_page_config(
    page_title='低檔打底+投信鎖股戰情室', page_icon='📈', layout='wide'
)

st.title('📈 台股投信鎖股 — 低檔打底突破選股儀表板')
st.caption(
    '專注篩選：低檔盤整打底 + 投信積極買進 + K線突破 + 均線多頭排列 (Close > 5MA >'
    ' 10MA > 20MA)'
)

# 側邊欄控制
st.sidebar.header('⚙️ 策略參數設定')
min_days = st.sidebar.slider('投信最低連買天數', 1, 10, 2)
min_ratio = (
    st.sidebar.slider('買超佔成交量最低比例 (%)', 1.0, 10.0, 2.5) / 100
)
max_cons_range = (
    st.sidebar.slider('近20日高低價波幅上限 (%)', 10.0, 35.0, 25.0) / 100
)

st.sidebar.markdown('---')
st.sidebar.info(
    '💡 策略邏輯：尋找股價經歷打底盤整、投信在低位默默佈局，且今日K線強勢突破，均線呈現完美多頭排列'
    ' (Close > 5MA > 10MA > 20MA) 的轉強標的。'
)


# 抓取資料
@st.cache_data(ttl=3600)
def fetch_screener_data():
  try:
    dl = DataLoader()
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=120)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')

    # 熱門中小型股、概念股監控清單
    watch_list = [
        '3081',
        '3450',
        '3163',
        '8358',
        '3035',
        '3661',
        '2349',
        '8046',
        '6451',
        '2455',
        '3017',
        '2383',
        '6274',
        '3231',
        '6669',
        '3583',
        '6187',
        '3680',
        '1519',
        '1513',
        '1504',
        '3324',
        '3533',
        '8054',
        '6176',
        '3363',
        '6223',
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
            df_inst[df_inst['name'] == 'Investment_Trust']
            .groupby('date')['buy']
            .sum()
            .reset_index()
        )
        df_sitc.rename(
            columns={'date': 'date', 'buy': 'SITC_Buy'}, inplace=True
        )

        df_merged = pd.merge(df_price, df_sitc, on='date', how='left')
        df_merged['SITC_Buy'] = df_merged['SITC_Buy'].fillna(0)
        df_merged['StockID'] = stock_id
        all_data.append(df_merged)
      except Exception:
        continue

    if not all_data:
      return pd.DataFrame(), ''

    df_all = pd.concat(all_data, ignore_index=True)

    # 數值格式清洗
    df_all['close'] = pd.to_numeric(df_all['close'], errors='coerce')
    df_all['high'] = (
        pd.to_numeric(df_all['max'], errors='coerce')
        if 'max' in df_all.columns
        else df_all['close']
    )
    df_all['low'] = (
        pd.to_numeric(df_all['min'], errors='coerce')
        if 'min' in df_all.columns
        else df_all['close']
    )
    df_all['Trading_Volume'] = pd.to_numeric(
        df_all['Trading_Volume'], errors='coerce'
    )

    # 技術指標計算 (5MA, 10MA, 20MA)
    df_all['MA5'] = df_all.groupby('StockID')['close'].transform(
        lambda x: x.rolling(5).mean()
    )
    df_all['MA10'] = df_all.groupby('StockID')['close'].transform(
        lambda x: x.rolling(10).mean()
    )
    df_all['MA20'] = df_all.groupby('StockID')['close'].transform(
        lambda x: x.rolling(20).mean()
    )

    # 計算近20日高低點盤整區間波幅
    df_all['High_20'] = df_all.groupby('StockID')['high'].transform(
        lambda x: x.rolling(20).max()
    )
    df_all['Low_20'] = df_all.groupby('StockID')['low'].transform(
        lambda x: x.rolling(20).min()
    )
    df_all['Consolidation_Range'] = (
        df_all['High_20'] - df_all['Low_20']
    ) / df_all['Low_20']

    # 籌碼指標
    df_all['SITC_Is_Buy'] = df_all['SITC_Buy'] > 0
    df_all['SITC_Consecutive_Days'] = df_all.groupby('StockID')[
        'SITC_Is_Buy'
    ].transform(lambda x: x.groupby((~x).cumsum()).cumsum())
    df_all['SITC_Ratio'] = df_all['SITC_Buy'] / (
        df_all['Trading_Volume'] / 1000
    )

    latest_date = df_all['date'].max()
    df_today = df_all[df_all['date'] == latest_date].copy()

    return df_today, latest_date
  except Exception as e:
    st.error(f"資料計算過程出錯: {e}")
    return pd.DataFrame(), ''


# 載入資料與呈現
with st.spinner('⏳ 正在分析盤整打底與均線多頭排列標的...'):
  df_today, latest_date = fetch_screener_data()

if df_today.empty:
  st.warning('⚠️ 目前抓取資料為空，請確認是否為非交易日。')
else:
  st.subheader(f'📅 最新交易日：{latest_date}')

  # 排除大型權值股黑名單
  heavy_weights = ['2330', '2454', '2317', '2308', '2881', '2882']

  # 核心篩選邏輯：
  # 1. 非權值股
  # 2. 均線按順序多頭排列： Close > 5MA > 10MA > 20MA
  # 3. 低檔盤整型態：近20日高低波幅小於指定上限
  # 4. 投信佈局：連買天數 + 買超佔比
  df_filtered = df_today[
      (~df_today['StockID'].isin(heavy_weights))
      & (df_today['close'] > df_today['MA5'])
      & (df_today['MA5'] > df_today['MA10'])
      & (df_today['MA10'] > df_today['MA20'])
      & (df_today['Consolidation_Range'] <= max_cons_range)
      & (df_today['SITC_Consecutive_Days'] >= min_days)
      & (df_today['SITC_Ratio'] >= min_ratio)
  ]

  col1, col2 = st.columns(2)
  col1.metric('今日總監控標的', f'{len(df_today)} 檔')
  col2.metric('符合打底突破+多頭排列', f'{len(df_filtered)} 檔')

  st.markdown('---')

  if df_filtered.empty:
    st.info(
        '💡 今日尚無同時符合「低檔打底 + 均線多頭排列 (Close > 5MA > 10MA > 20MA) +'
        ' 投信鎖股」的標的。您可以嘗試放寬側邊欄的波幅上限或連買天數。'
    )
  else:
    display_df = df_filtered[[
        'StockID',
        'close',
        'SITC_Buy',
        'SITC_Consecutive_Days',
        'SITC_Ratio',
        'Consolidation_Range',
    ]].copy()
    display_df.columns = [
        '股票代號',
        '今日收盤價',
        '投信買超(張)',
        '投信連買天數',
        '買超佔成交量比',
        '近20日高低波幅',
    ]
    display_df['買超佔成交量比'] = display_df['買超佔成交量比'].apply(
        lambda x: f'{x:.2%}'
    )
    display_df['近20日高低波幅'] = display_df['近20日高低波幅'].apply(
        lambda x: f'{x:.1%}'
    )

    st.write(
        '🎯 **符合「低檔打底盤整 + 均線多頭順序排列 + 投信進場」之標的明細：**'
    )
    st.dataframe(display_df, use_container_width=True)
