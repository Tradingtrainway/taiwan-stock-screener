import datetime
from FinMind.data import DataLoader
import pandas as pd
import streamlit as st

# 網頁頁面設定
st.set_page_config(
    page_title='投信鎖股動能戰情室', page_icon='📈', layout='wide'
)

st.title('📈 台股投信鎖股動能 — 每日自動選股儀表板')
st.caption('自動抓取盤後資料，篩選符合：雙均線上 + 投信連買 + 籌碼集中之標的')

# 側邊欄控制
st.sidebar.header('⚙️ 策略參數篩選')
min_days = st.sidebar.slider('投信最低連買天數', 1, 10, 3)
min_ratio = (
    st.sidebar.slider('買超佔成交量最低比例 (%)', 1.0, 10.0, 3.0) / 100
)

st.sidebar.markdown('---')
st.sidebar.info('💡 提示：建議每日下午 3:30 後重新整理網頁獲取最新數據。')


# 快取資料，避免重複讀取 (設定 1 小時過期)
@st.cache_data(ttl=3600)
def fetch_screener_data():
  dl = DataLoader()
  today = datetime.date.today()
  start_date = (today - datetime.timedelta(days=120)).strftime('%Y-%m-%d')
  end_date = today.strftime('%Y-%m-%d')

  # 觀察個股清單 (可自行增加或擴充)
  watch_list = [
      '2330',
      '2454',
      '3035',
      '3661',
      '3450',
      '3081',
      '2349',
      '8046',
      '8358',
      '3163',
      '6451',
      '2455',
      '3017',
      '2383',
      '6274',
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

      if df_price.empty or df_inst.empty:
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
    except:
      continue

  if not all_data:
    return pd.DataFrame(), ''

  df_all = pd.concat(all_data, ignore_index=True)

  # 指標計算
  df_all['MA20'] = df_all.groupby('StockID')['close'].transform(
      lambda x: x.rolling(20).mean()
  )
  df_all['MA60'] = df_all.groupby('StockID')['close'].transform(
      lambda x: x.rolling(60).mean()
  )
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


# 載入資料
with st.spinner('⏳ 正在向雲端抓取最新盤後籌碼與 K 線資料...'):
  df_today, latest_date = fetch_screener_data()

if df_today.empty:
  st.error('目前無法讀取資料，請稍後再試。')
else:
  st.subheader(f'📅 最新交易日：{latest_date}')

  # 依側邊欄條件動態篩選
  df_filtered = df_today[
      (df_today['close'] > df_today['MA20'])
      & (df_today['close'] > df_today['MA60'])
      & (df_today['SITC_Consecutive_Days'] >= min_days)
      & (df_today['SITC_Ratio'] >= min_ratio)
  ]

  col1, col2 = st.columns(2)
  col1.metric('今日總監控股票', f'{len(df_today)} 檔')
  col2.metric('符合鎖股條件', f'{len(df_filtered)} 檔')

  st.markdown('---')

  if df_filtered.empty:
    st.info('💡 今日尚無符合您設定條件的標的，請嘗試放寬側邊欄條件或保持耐性等待。')
  else:
    display_df = df_filtered[[
        'StockID',
        'close',
        'SITC_Buy',
        'SITC_Consecutive_Days',
        'SITC_Ratio',
    ]].copy()
    display_df.columns = [
        '股票代號',
        '今日收盤價',
        '投信買超(張)',
        '投信連買天數',
        '買超佔成交量比',
    ]
    display_df['買超佔成交量比'] = display_df['買超佔成交量比'].apply(
        lambda x: f'{x:.2%}'
    )

    st.write('🎯 **符合條件之標的明細：**')
    st.dataframe(display_df, use_container_width=True)
