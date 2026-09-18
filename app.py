import datetime
import re
import pandas as pd
import requests
import streamlit as st

# 設定 Streamlit 頁面標題與佈局
st.set_page_config(
    page_title="台股即時處置股追蹤系統", page_icon="📈", layout="wide"
)

# 請求標頭 (模擬真實 HTTP 連線)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# -----------------------------------------------------------------------------
# 1. 工具函式：民國年日期轉換與解析
# -----------------------------------------------------------------------------
def roc_to_ad_date(roc_str):
    """將民國年月日 (如 113/09/18, 113.09.18, 1130918) 轉為 datetime.date 物件"""
    if not roc_str:
        return None

    nums = re.findall(r"\d+", str(roc_str))
    if len(nums) >= 3:
        year = int(nums[0]) + 1911
        month = int(nums[1])
        day = int(nums[2])
        try:
            return datetime.date(year, month, day)
        except ValueError:
            return None
    elif len(nums) == 1 and len(nums[0]) in (6, 7):
        s = nums[0]
        day = int(s[-2:])
        month = int(s[-4:-2])
        year = int(s[:-4]) + 1911
        try:
            return datetime.date(year, month, day)
        except ValueError:
            return None
    return None


def parse_date_range(period_str):
    """從處置區間字串中解析出 (start_date, end_date)"""
    if not period_str:
        return None, None

    # 搜尋字串中的日期模式 (例如 113/09/10 ~ 113/09/23)
    dates = re.findall(r"\d{2,3}[\/\.\年]\d{1,2}[\/\.\月]\d{1,2}", str(period_str))
    if len(dates) >= 2:
        start_d = roc_to_ad_date(dates[0])
        end_d = roc_to_ad_date(dates[1])
        return start_d, end_d
    elif len(dates) == 1:
        start_d = roc_to_ad_date(dates[0])
        return start_d, None

    return None, None


# -----------------------------------------------------------------------------
# 2. 數據抓取：官方 Open API (免被擋 IP)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=1800)  # 自動快取 30 分鐘，避免頻繁請求
def fetch_twse_disposal():
    """抓取臺灣證券交易所 (上市) 處置股資料"""
    url = "https://openapi.twse.com.tw/v1/announcement/notice3"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                code = (
                    item.get("Code", "")
                    or item.get("證券代號", "")
                    or item.get("a1", "")
                )
                name = (
                    item.get("Name", "")
                    or item.get("證券名稱", "")
                    or item.get("a2", "")
                )
                period = (
                    item.get("DispositionPeriod", "")
                    or item.get("處置起迄時間", "")
                    or item.get("a3", "")
                )
                measures = (
                    item.get("DispositionMeasures", "")
                    or item.get("處置措施", "")
                    or item.get("a4", "")
                )
                reason = (
                    item.get("Reason", "")
                    or item.get("處置原因", "")
                    or item.get("a5", "")
                )

                start_d, end_d = parse_date_range(period)

                results.append(
                    {
                        "市場": "上市",
                        "代號": str(code).strip(),
                        "名稱": str(name).strip(),
                        "處置區間": str(period).strip(),
                        "開始日期": start_d,
                        "結束日期": end_d,
                        "處置措施": str(measures).strip(),
                        "處置原因": str(reason).strip(),
                    }
                )
    except Exception as e:
        st.warning(f"上市處置股連線警示: {e}")
    return results


@st.cache_data(ttl=1800)
def fetch_tpex_disposal():
    """抓取櫃買中心 (上櫃) 處置股資料"""
    url = "https://www.tpex.org.tw/web/bulletin/disposal/disposal_result.php?l=zh-tw"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            aa_data = data.get("aaData", [])
            for row in aa_data:
                if len(row) >= 5:
                    code = row[1]
                    name = row[2]
                    period = row[3]
                    measures = row[4]
                    reason = row[5] if len(row) > 5 else ""

                    start_d, end_d = parse_date_range(period)

                    results.append(
                        {
                            "市場": "上櫃",
                            "代號": str(code).strip(),
                            "名稱": str(name).strip(),
                            "處置區間": str(period).strip(),
                            "開始日期": start_d,
                            "結束日期": end_d,
                            "處置措施": str(measures).strip(),
                            "處置原因": str(reason).strip(),
                        }
                    )
    except Exception as e:
        st.warning(f"上櫃處置股連線警示: {e}")
    return results


# -----------------------------------------------------------------------------
# 3. 邏輯處理：篩選當日生效處置股 & 出關計算
# -----------------------------------------------------------------------------
def process_active_stocks(all_stocks):
    today = datetime.date.today()
    active_list = []

    for stock in all_stocks:
        start_d = stock["開始日期"]
        end_d = stock["結束日期"]

        # 預設狀態
        is_active = True
        remaining_days = None
        status = "🔵 處置中"

        # 判斷今日是否在處置區間內
        if start_d and end_d:
            if start_d <= today <= end_d:
                is_active = True
                remaining_days = (end_d - today).days
                if start_d == today:
                    status = "🟢 今日新進處置"
                elif remaining_days == 0:
                    status = "🔴 今日最後一天"
                elif remaining_days <= 2:
                    status = "🟡 即將出關"
                else:
                    status = "🔵 處置中"
            else:
                is_active = False
        elif start_d and not end_d:
            if start_d <= today:
                is_active = True
            else:
                is_active = False

        if is_active:
            # 分盤類別判斷
            measures = stock["處置措施"]
            if "20分" in measures or "預收" in measures:
                match_type = "20分鐘/預收款券"
            elif "5分" in measures:
                match_type = "5分鐘分盤"
            else:
                match_type = "分盤處置"

            active_list.append(
                {
                    "狀態": status,
                    "市場": stock["市場"],
                    "代號": stock["代號"],
                    "名稱": stock["名稱"],
                    "撮合方式": match_type,
                    "剩餘日曆天": (
                        f"{remaining_days} 天"
                        if remaining_days is not None
                        else "計算中"
                    ),
                    "開始日期": (
                        start_d.strftime("%Y-%m-%d") if start_d else "未解析"
                    ),
                    "結束日期": (
                        end_d.strftime("%Y-%m-%d") if end_d else "未解析"
                    ),
                    "處置區間": stock["處置區間"],
                    "詳細處置措施": stock["處置措施"],
                    "處置原因": stock["處置原因"],
                }
            )

    return active_list


# -----------------------------------------------------------------------------
# 4. Streamlit 主介面渲染
# -----------------------------------------------------------------------------
st.title("📈 台灣股市「今日生效」處置股即時看板")
st.caption(
    f"數據來源：臺灣證券交易所 (TWSE) & 櫃買中心 (TPEx) 官方數據網口 | 系統日期：{datetime.date.today()}"
)

# 重新整理按鈕
col_btn, _ = st.columns([1, 5])
with col_btn:
    if st.button("🔄 重新載入最新數據"):
        st.cache_data.clear()
        st.rerun()

# 抓取並整合資料
with st.spinner("正連線至證交所與櫃買中心取得今日最新資料..."):
    raw_twse = fetch_twse_disposal()
    raw_tpex = fetch_tpex_disposal()
    all_raw = raw_twse + raw_tpex
    active_stocks = process_active_stocks(all_raw)

# 轉換為 DataFrame
df = pd.DataFrame(active_stocks)

if df.empty:
    st.info("💡 目前官方 API 回傳無正在生效的處置股票資料，或非營業日。")
else:
    # 頂部關鍵指標 (Metrics)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("今日生效總數", f"{len(df)} 檔")
    m2.metric("上市處置股", f"{len(df[df['市場'] == '上市'])} 檔")
    m3.metric("上櫃處置股", f"{len(df[df['市場'] == '上櫃'])} 檔")
    m4.metric(
        "20分撮合/預收款券",
        f"{len(df[df['撮合方式'] == '20分鐘/預收款券'])} 檔",
    )

    st.markdown("---")

    # 搜尋與篩選區域
    f1, f2 = st.columns([1, 2])
    with f1:
        market_filter = st.multiselect(
            "篩選市場",
            options=["上市", "上櫃"],
            default=["上市", "上櫃"],
        )
    with f2:
        search_query = st.text_input(
            "搜尋股票代號或名稱", placeholder="輸入如：2330 或 台積電"
        )

    # 執行過濾
    filtered_df = df[df["市場"].isin(market_filter)]
    if search_query:
        filtered_df = filtered_df[
            filtered_df["代號"].str.contains(search_query, case=False)
            | filtered_df["名稱"].str.contains(search_query, case=False)
        ]

    # 展示主數據表格
    st.subheader(f"📊 處置股票清單 ({len(filtered_df)} 檔)")

    display_cols = [
        "狀態",
        "市場",
        "代號",
        "名稱",
        "撮合方式",
        "剩餘日曆天",
        "開始日期",
        "結束日期",
        "詳細處置措施",
    ]

    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "代號": st.column_config.TextColumn("股票代號"),
            "名稱": st.column_config.TextColumn("股票名稱"),
            "詳細處置措施": st.column_config.TextColumn("處置內容", width="large"),
        },
    )

    # 下載 CSV 功能
    csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 下載今日處置股清單 (CSV)",
        data=csv_data,
        file_name=f"disposal_stocks_{datetime.date.today()}.csv",
        mime="text/csv",
    )
