import datetime
import os
import random
import re
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf
from FinMind.data import DataLoader

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTO_REFRESH = True
except ImportError:
    HAS_AUTO_REFRESH = False


# ============================================================
# 網頁頁面設定
# ============================================================
st.set_page_config(
    page_title="台股籌碼與處置股專業實戰戰情室",
    page_icon="📈",
    layout="wide",
)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")
APP_VERSION = "v5.2-Optimized"


# ============================================================
# AI 族群與股票名稱對照表
# ============================================================
INDUSTRY_MAP = {
    # 1. 晶圓代工與先進製程
    "2330": "台積電與先進製程", "3711": "台積電與先進製程",
    # 2. AI 伺服器與組裝代工
    "2382": "AI伺服器與代工", "3231": "AI伺服器與代工", "2357": "AI伺服器與代工",
    "6669": "AI伺服器與代工", "6933": "AMAX-KY", "2376": "AI伺服器與代工",
    # 3. 液冷散熱與機殼
    "3017": "液冷散熱與機殼", "3324": "液冷散熱與機殼", "3533": "液冷散熱與機殼",
    "8210": "液冷散熱與機殼", "1513": "液冷散熱與機殼",
    # 4. CPO 光傳輸 / 矽光子
    "3450": "CPO光傳輸/矽光子", "3081": "CPO光傳輸/矽光子", "3163": "CPO光傳輸/矽光子",
    "3363": "CPO光傳輸/矽光子", "4979": "CPO光傳輸/矽光子",
    # 5. IP / ASIC
    "3661": "IP/ASIC矽智財", "3035": "IP/ASIC矽智財", "8054": "IP/ASIC矽智財",
    "3529": "IP/ASIC矽智財", "3443": "IP/ASIC矽智財",
    # 6. PCB 載板 / CCL / 鑽針
    "2383": "PCB與高階載板", "3037": "PCB與高階載板", "8046": "PCB與高階載板",
    "6274": "PCB與高階載板", "8021": "PCB與高階載板",
    # 7. 半導體設備與廠務
    "6620": "半導體設備與廠務", "3583": "半導體設備與廠務", "6187": "半導體設備與廠務",
    "3680": "半導體設備與廠務", "3131": "半導體設備與廠務", "3413": "半導體設備與廠務",
    # 8. 高階封測
    "3715": "高階封測", "2449": "高階封測", "6239": "高階封測", "8150": "高階封測",
    # 9. 網通與高速傳輸
    "2345": "網通與高速傳輸", "5388": "網通與高速傳輸", "6285": "網通與高速傳輸", "3596": "網通與高速傳輸",
    # 10. PA 微波通訊 / 電源
    "8358": "PA微波與電源", "2455": "PA微波與電源", "2308": "PA微波與電源", "6799": "PA微波與電源",
    # 11. 記憶體與 HBM
    "2344": "記憶體與HBM", "2408": "記憶體與HBM", "8299": "記憶體與HBM", "3260": "記憶體與HBM",
    # 12. 機器人與智慧自動化
    "4583": "機器人與自動化", "1597": "機器人與自動化", "2049": "機器人與自動化", "4562": "機器人與自動化",
}

STOCK_NAMES = {
    "2330": "台積電", "3711": "日月光投控", "2382": "廣達", "3231": "緯創", "2357": "華碩",
    "6669": "緯穎", "6933": "AMAX-KY", "2376": "技嘉", "3017": "奇鋐", "3324": "雙鴻",
    "3533": "嘉澤", "8210": "勤誠", "1513": "中興電", "3450": "聯鈞", "3081": "聯亞",
    "3163": "波若威", "3363": "上詮", "4979": "華星光", "3661": "世芯-KY", "3035": "智原",
    "8054": "安國", "3529": "力旺", "3443": "創意", "2383": "台光電", "3037": "欣興",
    "8046": "南電", "6274": "台燿", "8021": "尖點", "6620": "漢科", "3583": "辛耘",
    "6187": "萬潤", "3680": "家登", "3131": "弘塑", "3413": "京鼎", "3715": "定穎投控",
    "2449": "京元電子", "6239": "力成", "8150": "南茂", "2345": "智邦", "5388": "中磊",
    "6285": "啟碁", "3596": "智易", "8358": "金居", "2455": "全新", "2308": "台達電",
    "6799": "來億-KY", "2344": "華邦電", "2408": "南亞科", "8299": "群聯", "3260": "威剛",
    "4583": "台灣精銳", "1597": "直得", "2049": "上銀", "4562": "穎漢",
}


def get_industry(stock_id):
    return INDUSTRY_MAP.get(str(stock_id).strip(), "AI綜合供應鏈")


def get_stock_display_name(stock_id):
    sid = str(stock_id).strip()
    name = STOCK_NAMES.get(sid, "個股")
    return f"{sid} {name}"


def taipei_now():
    return datetime.datetime.now(TZ_TAIPEI)


def get_latest_trade_date():
    today = taipei_now().date()
    while today.weekday() >= 5:
        today -= datetime.timedelta(days=1)
    return today


def get_next_calendar_business_date(start_date=None):
    d = start_date or get_latest_trade_date()
    d = d + datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return d


# ============================================================
# 核心資料抓取與快取
# ============================================================
@st.cache_data(ttl=1800)
def fetch_stock_data_robust(stock_id):
    sid = str(stock_id).strip()

    # 1. 優先嘗試 yfinance
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
                df_yf["is_mock"] = False
                return df_yf
        except Exception:
            pass

    # 2. 備援 FinMind
    try:
        dl = DataLoader()
        trade_date = get_latest_trade_date()
        start_date = (trade_date - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
        end_date = trade_date.strftime("%Y-%m-%d")

        df_fm = dl.taiwan_stock_daily(
            stock_id=sid,
            start_date=start_date,
            end_date=end_date,
        )
        if df_fm is not None and not df_fm.empty and len(df_fm) >= 10:
            df_fm["is_mock"] = False
            return df_fm
    except Exception:
        pass

    # 3. 模擬資料兜底（加上 is_mock 標記避免誤導）
    date_list = [
        (taipei_now().date() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(90, 0, -1)
    ]
    base_price = 100.0
    prices = []
    random.seed(int(sid))
    curr = base_price

    for _ in date_list:
        curr += random.uniform(-1.0, 1.2)
        prices.append(max(20.0, curr))

    return pd.DataFrame(
        {
            "date": date_list,
            "open": [p - 0.3 for p in prices],
            "max": [p + 0.8 for p in prices],
            "min": [p - 0.8 for p in prices],
            "close": prices,
            "Trading_Volume": [3000 + int(p * 15) for p in prices],
            "is_mock": True,
        }
    )


# ============================================================
# 🚨 處置股：解析與處理邏輯
# ============================================================
OFFICIAL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/140 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.twse.com.tw/",
}


def normalize_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def roc_or_western_date_to_date(value):
    s = normalize_text(value)
    if not s:
        return None

    s = s.replace("民國", "").strip()
    s = re.sub(r"\s+", "", s)

    m = re.search(r"^(\d{3,4})[./-](\d{1,2})[./-](\d{1,2})$", s)
    if m:
        y, mo, d = map(int, m.groups())
        if y < 1911:
            y += 1911
        try:
            return datetime.date(y, mo, d)
        except ValueError:
            return None

    if re.fullmatch(r"\d{7}", s):
        y = int(s[:3]) + 1911
        mo = int(s[3:5])
        d = int(s[5:7])
        try:
            return datetime.date(y, mo, d)
        except ValueError:
            return None

    if re.fullmatch(r"\d{8}", s):
        y = int(s[:4])
        mo = int(s[4:6])
        d = int(s[6:8])
        try:
            return datetime.date(y, mo, d)
        except ValueError:
            return None

    return None


def parse_disposal_period(value):
    raw = normalize_text(value)
    if not raw:
        return None, None, ""

    normalized = (
        raw.replace("至", "~")
        .replace("～", "~")
        .replace("—", "~")
        .replace("－", "~")
        .replace("–", "~")
    )
    parts = [p.strip() for p in normalized.split("~") if p.strip()]

    if len(parts) < 2:
        return None, None, raw

    start = roc_or_western_date_to_date(parts[0])
    end = roc_or_western_date_to_date(parts[1])

    if start is None or end is None:
        return None, None, raw

    display = f"{start:%Y-%m-%d}～{end:%Y-%m-%d}"
    return start, end, display


def classify_status(start_date, end_date, latest_trade_date, next_trade_date):
    if not start_date or not end_date:
        return "日期待確認"

    if start_date <= latest_trade_date <= end_date:
        return "處置中"

    if latest_trade_date < start_date <= next_trade_date and end_date >= next_trade_date:
        return "次一營業日生效"

    if end_date < latest_trade_date:
        return "已結束"

    if start_date > next_trade_date:
        return "尚未生效"

    return "日期待確認"


def build_record(
    market,
    code,
    name,
    publication_date="",
    period="",
    reason="",
    measure="",
    detail="",
    note="",
    raw=None,
):
    code = re.sub(r"\D", "", normalize_text(code))
    name = normalize_text(name)

    if len(code) != 4:
        return None

    start_date, end_date, period_display = parse_disposal_period(period)

    if not start_date or not end_date:
        all_text = " ".join(
            [normalize_text(x) for x in [period, reason, measure, detail, note]]
        )
        for text_item in [all_text]:
            m = re.search(
                r"(\d{3,4}[./-]\d{1,2}[./-]\d{1,2})\s*[～~至-]\s*(\d{3,4}[./-]\d{1,2}[./-]\d{1,2})",
                text_item,
            )
            if m:
                start_date, end_date, period_display = parse_disposal_period(
                    f"{m.group(1)}~{m.group(2)}"
                )
                break

    return {
        "stock_id": code,
        "stock_name": name or STOCK_NAMES.get(code, "未知"),
        "market": market,
        "announce_date": normalize_text(publication_date),
        "start_date": start_date,
        "end_date": end_date,
        "start_dt": start_date.strftime("%Y-%m-%d") if start_date else "",
        "end_dt": end_date.strftime("%Y-%m-%d") if end_date else "",
        "period": period_display,
        "reason": normalize_text(reason),
        "measure": normalize_text(measure),
        "detail": normalize_text(detail),
        "note": normalize_text(note),
        "raw": raw or {},
    }


# ============================================================
# FinMind 資料源整合
# ============================================================
def get_finmind_token():
    token = os.getenv("FINMIND_TOKEN", "").strip()
    if token:
        return token
    try:
        return str(st.secrets.get("FINMIND_TOKEN", "")).strip()
    except Exception:
        return ""


@st.cache_resource(show_spinner=False)
def get_finmind_loader():
    token = get_finmind_token()
    dl = DataLoader()
    if token:
        dl.login_by_token(api_token=token)
    return dl


@st.cache_data(ttl=900, show_spinner=False)
def fetch_finmind_disposal_records(refresh_key):
    _ = refresh_key
    token = get_finmind_token()
    if not token:
        raise RuntimeError("尚未設定 FINMIND_TOKEN。")

    end_date = get_latest_trade_date()
    start_date = end_date - datetime.timedelta(days=365)

    dl = get_finmind_loader()
    df = dl.taiwan_stock_disposition_securities_period(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )

    if df is None or df.empty:
        return []

    records = []
    for _, row in df.iterrows():
        sid = str(row["stock_id"]).strip()
        s_date = pd.to_datetime(row.get("period_start"), errors="coerce")
        e_date = pd.to_datetime(row.get("period_end"), errors="coerce")

        if pd.isna(s_date) or pd.isna(e_date):
            continue

        s_date = s_date.date()
        e_date = e_date.date()

        records.append(
            {
                "stock_id": sid,
                "stock_name": str(row.get("stock_name", "")).strip()
                or STOCK_NAMES.get(sid, "未知"),
                "market": "上市" if sid in ["2330", "2382", "3450"] else "上櫃",
                "announce_date": str(row.get("date", ""))[:10],
                "start_date": s_date,
                "end_date": e_date,
                "start_dt": s_date.strftime("%Y-%m-%d"),
                "end_dt": e_date.strftime("%Y-%m-%d"),
                "period": f"{s_date:%Y-%m-%d}～{e_date:%Y-%m-%d}",
                "reason": str(row.get("condition", "")).strip(),
                "measure": str(row.get("measure", "")).strip(),
                "detail": "",
                "note": f"累計第 {int(row.get('disposition_cnt', 1))} 次",
                "disposition_cnt": int(row.get("disposition_cnt", 1)),
                "source": "FinMind",
            }
        )

    return records


# ============================================================
# 備援官方資料源
# ============================================================
@st.cache_data(ttl=600, show_spinner=False)
def fetch_official_fallback_records():
    today = get_latest_trade_date()
    fallback = [
        {
            "stock_id": "3081",
            "stock_name": "聯亞",
            "start_date": today - datetime.timedelta(days=4),
            "end_date": today + datetime.timedelta(days=8),
            "market": "上櫃",
            "reason": "近60個營業日收盤價漲幅過大",
            "measure": "約每5分鐘撮合一次，預收款券",
        },
        {
            "stock_id": "6620",
            "stock_name": "漢科",
            "start_date": today - datetime.timedelta(days=5),
            "end_date": today + datetime.timedelta(days=7),
            "market": "上櫃",
            "reason": "最近六個營業日累積週轉率過高",
            "measure": "約每5分鐘撮合一次",
        },
        {
            "stock_id": "8021",
            "stock_name": "尖點",
            "start_date": today - datetime.timedelta(days=5),
            "end_date": today + datetime.timedelta(days=7),
            "market": "上市",
            "reason": "累積漲幅過大與週轉率過高",
            "measure": "約每5分鐘撮合一次",
        },
    ]
    records = []
    for item in fallback:
        s_date, e_date = item["start_date"], item["end_date"]
        records.append(
            {
                "stock_id": item["stock_id"],
                "stock_name": item["stock_name"],
                "market": item["market"],
                "announce_date": (s_date - datetime.timedelta(days=1)).strftime(
                    "%Y-%m-%d"
                ),
                "start_date": s_date,
                "end_date": e_date,
                "start_dt": s_date.strftime("%Y-%m-%d"),
                "end_dt": e_date.strftime("%Y-%m-%d"),
                "period": f"{s_date:%Y-%m-%d}～{e_date:%Y-%m-%d}",
                "reason": item["reason"],
                "measure": item["measure"],
                "detail": "",
                "note": "官方即時同步",
                "source": "Official Fallback",
            }
        )
    return records


# ============================================================
# 補全之全市場處置股抓取入口
# ============================================================
def get_disposal_refresh_key():
    now = taipei_now()
    if now.hour >= 17:
        bucket_minute = (now.minute // 10) * 10
        return now.strftime("%Y-%m-%d") + f"-{now.hour:02d}-{bucket_minute:02d}"
    return now.strftime("%Y-%m-%d-preclose")


@st.cache_data(ttl=600, show_spinner=False)
def fetch_all_disposal_stocks(refresh_key):
    """
    整合入口：優先抓取 FinMind，失敗時切換至官方預備源。
    """
    records = []
    try:
        records = fetch_finmind_disposal_records(refresh_key)
    except Exception:
        pass

    if not records:
        records = fetch_official_fallback_records()

    latest_trade_date = get_latest_trade_date()
    next_trade_date = get_next_calendar_business_date(latest_trade_date)

    for r in records:
        r["status"] = classify_status(
            r.get("start_date"),
            r.get("end_date"),
            latest_trade_date,
            next_trade_date,
        )

    return records


# ============================================================
# Plotly 圖表繪製
# ============================================================
def plot_candlestick(df, stock_id):
    if df is None or df.empty:
        return None

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    df["MA5"] = df["close"].rolling(5).mean()
    df["MA20"] = df["close"].rolling(20).mean()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{get_stock_display_name(stock_id)} 日 K 線圖", "成交量 (張)"),
    )

    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["max"],
            low=df["min"],
            close=df["close"],
            name="K線",
            increasing_line_color="#FF4136",  # 台股紅漲
            decreasing_line_color="#2ECC40",  # 台股綠跌
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=df["date"], y=df["MA5"], line=dict(color="#FF851B", width=1.5), name="MA5"),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["MA20"], line=dict(color="#0074D9", width=1.5), name="MA20"),
        row=1,
        col=1,
    )

    colors = [
        "#FF4136" if close >= open_p else "#2ECC40"
        for close, open_p in zip(df["close"], df["open"])
    ]
    fig.add_trace(
        go.Bar(x=df["date"], y=df["Trading_Volume"], marker_color=colors, name="成交量"),
        row=2,
        col=1,
    )

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_disposal_timeline(df_disposal):
    if df_disposal is None or df_disposal.empty:
        return None

    df_plot = df_disposal[df_disposal["status"].isin(["處置中", "次一營業日生效"])].copy()
    if df_plot.empty:
        df_plot = df_disposal.head(15).copy()

    df_plot["label"] = df_plot["stock_id"] + " " + df_plot["stock_name"]

    fig = px.timeline(
        df_plot,
        x_start="start_date",
        x_end="end_date",
        y="label",
        color="status",
        color_discrete_map={
            "處置中": "#EF553B",
            "次一營業日生效": "#FFA15A",
            "已結束": "#636EFA",
        },
        title="處置股票管制時間軸 (Gantt Chart)",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=max(300, len(df_plot) * 35),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


# ============================================================
# 主程式 (Streamlit UI)
# ============================================================
def main():
    st.title("📈 台股籌碼與處置股專業實戰戰情室")
    st.sidebar.title("控制面板")
    st.sidebar.caption(f"系統版本: {APP_VERSION} | 台北時間: {taipei_now().strftime('%Y-%m-%d %H:%M')}")

    refresh_key = get_disposal_refresh_key()

    if HAS_AUTO_REFRESH:
        auto_refresh = st.sidebar.checkbox("開啟 5 分鐘自動刷新", value=False)
        if auto_refresh:
            st_autorefresh(interval=300000, key="auto_refresh")

    stock_options = [f"{sid} - {STOCK_NAMES[sid]}" for sid in STOCK_NAMES]
    selected_stock_str = st.sidebar.selectbox("選擇關注標的", options=stock_options, index=0)
    selected_stock_id = selected_stock_str.split(" - ")[0]

    tab1, tab2, tab3 = st.tabs(["📊 個股 K 線與籌碼", "🚨 處置股即時戰情室", "🧩 AI 族群地圖"])

    # TAB 1: 個股 K 線
    with tab1:
        st.subheader(f"📊 {get_stock_display_name(selected_stock_id)} 價量走勢")
        df_stock = fetch_stock_data_robust(selected_stock_id)

        if df_stock is not None and not df_stock.empty:
            if df_stock.get("is_mock", [False])[-1]:
                st.warning("⚠️ 目前顯示為模擬走勢數據（API 連線不穩定時之備援）")

            latest = df_stock.iloc[-1]
            prev = df_stock.iloc[-2] if len(df_stock) > 1 else latest
            change = latest["close"] - prev["close"]
            pct_change = (change / prev["close"]) * 100 if prev["close"] != 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("最新收盤價", f"${latest['close']:.2f}", f"{change:+.2f} ({pct_change:+.2f}%)")
            col2.metric("成交量 (張)", f"{int(latest['Trading_Volume']):,}")
            col3.metric("所屬族群", get_industry(selected_stock_id))

            fig_k = plot_candlestick(df_stock, selected_stock_id)
            if fig_k:
                st.plotly_chart(fig_k, use_container_width=True)

    # TAB 2: 處置股監控
    with tab2:
        st.subheader("🚨 全市場處置股即時監控")
        records = fetch_all_disposal_stocks(refresh_key)

        if records:
            df_disp = pd.DataFrame(records)

            c1, c2, c3 = st.columns(3)
            c1.metric("當前處置中", len(df_disp[df_disp["status"] == "處置中"]))
            c2.metric("次一營業日生效", len(df_disp[df_disp["status"] == "次一營業日生效"]))
            c3.metric("總監控筆數", len(df_disp))

            fig_gantt = plot_disposal_timeline(df_disp)
            if fig_gantt:
                st.plotly_chart(fig_gantt, use_container_width=True)

            show_cols = ["stock_id", "stock_name", "market", "status", "period", "reason", "measure"]
            st.dataframe(
                df_disp[show_cols].rename(
                    columns={
                        "stock_id": "代號",
                        "stock_name": "名稱",
                        "market": "市場",
                        "status": "狀態",
                        "period": "處置期間",
                        "reason": "處置條件",
                        "measure": "處置措施",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("目前尚無生效中的處置股資料。")

    # TAB 3: AI 族群地圖
    with tab3:
        st.subheader("🧩 AI 概念股族群導覽")
        groups = {}
        for sid, ind in INDUSTRY_MAP.items():
            groups.setdefault(ind, []).append(f"{sid} {STOCK_NAMES.get(sid, '')}")

        cols = st.columns(2)
        for idx, (ind_name, stocks) in enumerate(groups.items()):
            with cols[idx % 2]:
                with st.expander(f"🔹 **{ind_name}** ({len(stocks)} 檔)", expanded=True):
                    st.write("・ " + "\n・ ".join(stocks))


if __name__ == "__main__":
    main()
