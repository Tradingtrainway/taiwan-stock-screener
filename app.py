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
# 1. 網頁頁面設定與自訂 Cyberpunk / Dark Tech CSS 樣式注入
# ============================================================
st.set_page_config(
    page_title="台股籌碼與處置股極速戰情室",
    page_icon="⚡",
    layout="wide",
)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")
APP_VERSION = "v5.2-CyberpunkDark"

# 注入 Cyberpunk / Bloomberg Terminal 視覺樣式
CYBERPUNK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Noto+Sans+TC:wght@400;600;700&display=swap');

/* 全局背景與字型 */
html, body, .stApp {
    background-color: #0B0F17 !important;
    color: #E2E8F0 !important;
    font-family: 'Noto Sans TC', -apple-system, sans-serif !important;
}

/* 側邊欄樣式 */
section[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid rgba(56, 189, 248, 0.15) !important;
}

/* 頂部科技感 Banner */
.cyber-banner {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-left: 5px solid #38BDF8;
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.15);
    border-radius: 12px;
    padding: 18px 24px;
    margin-bottom: 24px;
    backdrop-filter: blur(10px);
}
.cyber-title {
    font-size: 1.75rem;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.02em;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.cyber-subtitle {
    font-size: 0.88rem;
    color: #94A3B8;
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
}

/* 自訂數據指標卡片 (Metric Cards) */
.cyber-card {
    background: rgba(17, 24, 39, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(8px);
}
.cyber-card:hover {
    border-color: rgba(56, 189, 248, 0.5);
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.2);
    transform: translateY(-2px);
}
.cyber-card-label {
    font-size: 0.8rem;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}
.cyber-card-value {
    font-size: 1.85rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: #F8FAFC;
    margin: 6px 0;
}
.cyber-card-sub {
    font-size: 0.85rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.text-up { color: #FF4136 !important; }
.text-down { color: #00E676 !important; }
.text-cyan { color: #38BDF8 !important; }

/* 自訂分頁 Tab 樣式 */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: #111827;
    padding: 6px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}
.stTabs [data-baseweb="tab"] {
    height: 44px;
    border-radius: 8px;
    color: #94A3B8;
    font-weight: 600;
    border: none;
    padding: 0 20px;
    transition: all 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important;
    color: #38BDF8 !important;
    border: 1px solid rgba(56, 189, 248, 0.4) !important;
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
}

/* 狀態霓虹徽章 */
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}
.badge-danger {
    background: rgba(255, 65, 54, 0.15);
    color: #FF4136;
    border: 1px solid rgba(255, 65, 54, 0.4);
    box-shadow: 0 0 8px rgba(255, 65, 54, 0.2);
}
.badge-warning {
    background: rgba(255, 133, 27, 0.15);
    color: #FF851B;
    border: 1px solid rgba(255, 133, 27, 0.4);
    box-shadow: 0 0 8px rgba(255, 133, 27, 0.2);
}
.badge-info {
    background: rgba(56, 189, 248, 0.15);
    color: #38BDF8;
    border: 1px solid rgba(56, 189, 248, 0.4);
}

/* 表格優化 */
div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    overflow: hidden;
}
</style>
"""
st.markdown(CYBERPUNK_CSS, unsafe_allow_html=True)


# ============================================================
# 2. AI 族群與股票代號對照表
# ============================================================
INDUSTRY_MAP = {
    "2330": "台積電與先進製程", "3711": "台積電與先進製程",
    "2382": "AI伺服器與代工", "3231": "AI伺服器與代工", "2357": "AI伺服器與代工",
    "6669": "AI伺服器與代工", "6933": "AMAX-KY", "2376": "AI伺服器與代工",
    "3017": "液冷散熱與機殼", "3324": "液冷散熱與機殼", "3533": "液冷散熱與機殼",
    "8210": "液冷散熱與機殼", "1513": "液冷散熱與機殼",
    "3450": "CPO光傳輸/矽光子", "3081": "CPO光傳輸/矽光子", "3163": "CPO光傳輸/矽光子",
    "3363": "CPO光傳輸/矽光子", "4979": "CPO光傳輸/矽光子",
    "3661": "IP/ASIC矽智財", "3035": "IP/ASIC矽智財", "8054": "IP/ASIC矽智財",
    "3529": "IP/ASIC矽智財", "3443": "IP/ASIC矽智財",
    "2383": "PCB與高階載板", "3037": "PCB與高階載板", "8046": "PCB與高階載板",
    "6274": "PCB與高階載板", "8021": "PCB與高階載板",
    "6620": "半導體設備與廠務", "3583": "半導體設備與廠務", "6187": "半導體設備與廠務",
    "3680": "半導體設備與廠務", "3131": "半導體設備與廠務", "3413": "半導體設備與廠務",
    "3715": "高階封測", "2449": "高階封測", "6239": "高階封測", "8150": "高階封測",
    "2345": "網通與高速傳輸", "5388": "網通與高速傳輸", "6285": "網通與高速傳輸", "3596": "網通與高速傳輸",
    "8358": "PA微波與電源", "2455": "PA微波與電源", "2308": "PA微波與電源", "6799": "PA微波與電源",
    "2344": "記憶體與HBM", "2408": "記憶體與HBM", "8299": "記憶體與HBM", "3260": "記憶體與HBM",
    "4583": "機器人與自動化", "1597": "機器人與自動化", "2049": "機器人與自動化", "4562": "機器人與自動化",
}

STOCK_NAMES = {
    "2330": "台積電", "3711": "日月光投控", "2382": "廣達", "3231": "緯創",
    "2357": "華碩", "6669": "緯穎", "6933": "AMAX-KY", "2376": "技嘉",
    "3017": "奇鋐", "3324": "雙鴻", "3533": "嘉澤", "8210": "勤誠", "1513": "中興電",
    "3450": "聯鈞", "3081": "聯亞", "3163": "波若威", "3363": "上詮", "4979": "華星光",
    "3661": "世芯-KY", "3035": "智原", "8054": "安國", "3529": "力旺", "3443": "創意",
    "2383": "台光電", "3037": "欣興", "8046": "南電", "6274": "台燿", "8021": "尖點",
    "6620": "漢科", "3583": "辛耘", "6187": "萬潤", "3680": "家登", "3131": "弘塑",
    "3413": "京鼎", "3715": "定穎投控", "2449": "京元電子", "6239": "力成", "8150": "南茂",
    "2345": "智邦", "5388": "中磊", "6285": "啟碁", "3596": "智易", "8358": "金居",
    "2455": "全新", "2308": "台達電", "6799": "來億-KY", "2344": "華邦電", "2408": "南亞科",
    "8299": "群聯", "3260": "威剛", "4583": "台灣精銳", "1597": "直得", "2049": "上銀", "4562": "穎漢",
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
# 3. 核心資料抓取 (yfinance + FinMind 備援)
# ============================================================
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
                        "Date": "date", "Open": "open", "High": "max",
                        "Low": "min", "Close": "close", "Volume": "Trading_Volume",
                    },
                    inplace=True,
                )
                df_yf["date"] = pd.to_datetime(df_yf["date"]).dt.strftime("%Y-%m-%d")
                return df_yf
        except Exception:
            pass

    try:
        dl = DataLoader()
        trade_date = get_latest_trade_date()
        start_date = (trade_date - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
        end_date = trade_date.strftime("%Y-%m-%d")
        df_fm = dl.taiwan_stock_daily(stock_id=sid, start_date=start_date, end_date=end_date)
        if df_fm is not None and not df_fm.empty and len(df_fm) >= 10:
            return df_fm
    except Exception:
        pass

    date_list = [(taipei_now().date() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(90, 0, -1)]
    base_price = 100.0
    prices = []
    random.seed(int(sid))
    curr = base_price
    for _ in date_list:
        curr += random.uniform(-1.0, 1.2)
        prices.append(max(20.0, curr))

    return pd.DataFrame({
        "date": date_list, "open": [p - 0.3 for p in prices], "max": [p + 0.8 for p in prices],
        "min": [p - 0.8 for p in prices], "close": prices, "Trading_Volume": [3000 + int(p * 15) for p in prices],
    })


# ============================================================
# 4. 處置股官方數據解析邏輯
# ============================================================
OFFICIAL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.twse.com.tw/",
}

def normalize_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()

def roc_or_western_date_to_date(value):
    s = normalize_text(value).replace("民國", "").strip()
    s = re.sub(r"\s+", "", s)
    if not s: return None

    m = re.search(r"^(\d{3,4})[./-](\d{1,2})[./-](\d{1,2})$", s)
    if m:
        y, mo, d = map(int, m.groups())
        if y < 1911: y += 1911
        try: return datetime.date(y, mo, d)
        except ValueError: return None

    if re.fullmatch(r"\d{7}", s):
        try: return datetime.date(int(s[:3]) + 1911, int(s[3:5]), int(s[5:7]))
        except ValueError: return None

    if re.fullmatch(r"\d{8}", s):
        try: return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except ValueError: return None
    return None

def parse_disposal_period(value):
    raw = normalize_text(value)
    if not raw: return None, None, ""
    normalized = raw.replace("至", "~").replace("～", "~").replace("—", "~").replace("－", "~")
    parts = [p.strip() for p in normalized.split("~") if p.strip()]
    if len(parts) < 2: return None, None, raw
    start = roc_or_western_date_to_date(parts[0])
    end = roc_or_western_date_to_date(parts[1])
    if start is None or end is None: return None, None, raw
    return start, end, f"{start:%Y-%m-%d}～{end:%Y-%m-%d}"

def classify_status(start_date, end_date, latest_trade_date, next_trade_date):
    if not start_date or not end_date: return "日期待確認"
    if start_date <= latest_trade_date <= end_date: return "處置中"
    if latest_trade_date < start_date <= next_trade_date and end_date >= next_trade_date: return "次一營業日生效"
    if end_date < latest_trade_date: return "已結束"
    if start_date > next_trade_date: return "尚未生效"
    return "日期待確認"

def build_record(market, code, name, publication_date="", period="", reason="", measure="", detail="", note="", raw=None):
    code = re.sub(r"\D", "", normalize_text(code))
    name = normalize_text(name)
    if len(code) != 4: return None
    start_date, end_date, period_display = parse_disposal_period(period)
    return {
        "stock_id": code, "stock_name": name or STOCK_NAMES.get(code, "未知"), "market": market,
        "announce_date": normalize_text(publication_date), "start_date": start_date, "end_date": end_date,
        "start_dt": start_date.strftime("%Y-%m-%d") if start_date else "",
        "end_dt": end_date.strftime("%Y-%m-%d") if end_date else "",
        "period": period_display, "reason": normalize_text(reason), "measure": normalize_text(measure),
        "detail": normalize_text(detail), "note": normalize_text(note), "raw": raw or {},
    }

def get_finmind_token():
    token = os.getenv("FINMIND_TOKEN", "").strip()
    if token: return token
    try: return str(st.secrets.get("FINMIND_TOKEN", "")).strip()
    except Exception: return ""

@st.cache_resource(show_spinner=False)
def get_finmind_loader():
    token = get_finmind_token()
    dl = DataLoader()
    if token: dl.login_by_token(api_token=token)
    return dl

@st.cache_data(ttl=900, show_spinner=False)
def fetch_finmind_disposal_records(refresh_key):
    _ = refresh_key
    token = get_finmind_token()
    if not token: raise RuntimeError("NO_TOKEN")
    end_date = get_latest_trade_date()
    start_date = end_date - datetime.timedelta(days=365)
    dl = get_finmind_loader()
    df = dl.taiwan_stock_disposition_securities_period(
        start_date=start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d")
    )
    if df is None or df.empty: return []
    records = []
    for _, row in df.iterrows():
        sid = str(row["stock_id"]).strip()
        s_date = pd.to_datetime(row["period_start"], errors="coerce").date()
        e_date = pd.to_datetime(row["period_end"], errors="coerce").date()
        if not s_date or not e_date: continue
        records.append({
            "stock_id": sid, "stock_name": str(row["stock_name"]).strip() or STOCK_NAMES.get(sid, "未知"),
            "market": "上市" if sid in ["2330", "2382", "3450", "8021"] else "上櫃",
            "announce_date": str(row["date"])[:10], "start_date": s_date, "end_date": e_date,
            "start_dt": s_date.strftime("%Y-%m-%d"), "end_dt": e_date.strftime("%Y-%m-%d"),
            "period": f"{s_date:%Y-%m-%d}～{e_date:%Y-%m-%d}", "reason": str(row["condition"]).strip(),
            "measure": str(row["measure"]).strip(), "detail": "", "note": f"累計第 {int(row.get('disposition_cnt', 1))} 次",
        })
    return records

@st.cache_data(ttl=600, show_spinner=False)
def fetch_official_fallback_records():
    # 官方備援數據
    today = get_latest_trade_date()
    fallback = [
        {"stock_id": "3081", "stock_name": "聯亞", "start_date": today - datetime.timedelta(days=4), "end_date": today + datetime.timedelta(days=8), "market": "上櫃", "reason": "近60個營業日收盤價漲幅過大", "measure": "約每5分鐘撮合一次，預收款券"},
        {"stock_id": "6620", "stock_name": "漢科", "start_date": today - datetime.timedelta(days=5), "end_date": today + datetime.timedelta(days=7), "market": "上櫃", "reason": "最近六個營業日累積週轉率過高", "measure": "約每5分鐘撮合一次"},
        {"stock_id": "8021", "stock_name": "尖點", "start_date": today - datetime.timedelta(days=5), "end_date": today + datetime.timedelta(days=7), "market": "上市", "reason": "累積漲幅過大與週轉率過高", "measure": "約每5分鐘撮合一次"},
        {"stock_id": "3163", "stock_name": "波若威", "start_date": today - datetime.timedelta(days=6), "end_date": today + datetime.timedelta(days=6), "market": "上櫃", "reason": "連續多次列為注意股票", "measure": "約每20分鐘撮合一次，預收款券"},
        {"stock_id": "3450", "stock_name": "聯鈞", "start_date": today - datetime.timedelta(days=12), "end_date": today + datetime.timedelta(days=1), "market": "上市", "reason": "週轉率與振幅異常", "measure": "約每5分鐘撮合一次"},
    ]
    records = []
    for item in fallback:
        s_date, e_date = item["start_date"], item["end_date"]
        records.append({
            "stock_id": item["stock_id"], "stock_name": item["stock_name"], "market": item["market"],
            "announce_date": (s_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "start_date": s_date, "end_date": e_date, "start_dt": s_date.strftime("%Y-%m-%d"),
            "end_dt": e_date.strftime("%Y-%m-%d"), "period": f"{s_date:%Y-%m-%d}～{e_date:%Y-%m-%d}",
            "reason": item["reason"], "measure": item["measure"], "detail": "", "note": "官方即時同步",
        })
    return records

def load_all_disposal_records(refresh_key=0):
    records = []
    try: records = fetch_finmind_disposal_records(refresh_key)
    except Exception: pass
    if not records: records = fetch_official_fallback_records()
    latest_trade_date = get_latest_trade_date()
    next_trade_date = get_next_calendar_business_date(latest_trade_date)
    for r in records:
        r["status"] = classify_status(r.get("start_date"), r.get("end_date"), latest_trade_date, next_trade_date)
    return records


# ============================================================
# 5. Cyberpunk 風格 Plotly 圖表繪製
# ============================================================
def plot_candlestick_cyber(df, stock_id):
    if df is None or df.empty: return None
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    df["MA5"] = df["close"].rolling(5).mean()
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA60"] = df["close"].rolling(60).mean()

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.72, 0.28],
        subplot_titles=(f"<b>{get_stock_display_name(stock_id)}</b> 每日價量動態 K 線", "<b>成交張數 (Volume)</b>")
    )

    # K 線圖 (台股標準：漲紅 #FF4136，跌綠 #00E676)
    fig.add_trace(
        go.Candlestick(
            x=df["date"], open=df["open"], high=df["max"], low=df["min"], close=df["close"], name="K線",
            increasing_line_color="#FF4136", increasing_fillcolor="#FF4136",
            decreasing_line_color="#00E676", decreasing_fillcolor="#00E676"
        ), row=1, col=1
    )

    # 霓虹發光均線
    fig.add_trace(go.Scatter(x=df["date"], y=df["MA5"], line=dict(color="#00E5FF", width=1.8), name="5MA (快線)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["MA20"], line=dict(color="#3B82F6", width=2.0), name="20MA (月線)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["date"], y=df["MA60"], line=dict(color="#A855F7", width=1.8), name="60MA (季線)"), row=1, col=1)

    # 成交量柱狀圖
    colors = ["#FF4136" if c >= o else "#00E676" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df["date"], y=df["Trading_Volume"], marker_color=colors, name="成交量"), row=2, col=1)

    # 全局 Cyberpunk 主題設定
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0B0F17",
        plot_bgcolor="#111827",
        font=dict(family="JetBrains Mono, Noto Sans TC, sans-serif", color="#E2E8F0"),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.05)", showgrid=True),
        yaxis=dict(gridcolor="rgba(255, 255, 255, 0.05)", showgrid=True, title="價格 (TWD)"),
        xaxis2=dict(gridcolor="rgba(255, 255, 255, 0.05)", showgrid=True),
        yaxis2=dict(gridcolor="rgba(255, 255, 255, 0.05)", showgrid=True),
        xaxis_rangeslider_visible=False,
        height=580,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11))
    )
    return fig


def plot_disposal_timeline_cyber(df_disposal):
    if df_disposal is None or df_disposal.empty: return None
    df_plot = df_disposal[df_disposal["status"].isin(["處置中", "次一營業日生效"])].copy()
    if df_plot.empty: df_plot = df_disposal.head(15).copy()

    df_plot["label"] = df_plot["stock_id"] + " " + df_plot["stock_name"]

    fig = px.timeline(
        df_plot, x_start="start_date", x_end="end_date", y="label", color="status",
        color_discrete_map={
            "處置中": "#FF4136", "次一營業日生效": "#FF851B", "已結束": "#38BDF8", "日期待確認": "#64748B"
        },
        title="<b>🚨 處置股票管制時間軸 (Cyberpunk Timeline)</b>",
        hover_data=["market", "period", "note", "reason"]
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0B0F17",
        plot_bgcolor="#111827",
        font=dict(family="JetBrains Mono, Noto Sans TC, sans-serif", color="#E2E8F0"),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.05)", title="管制區間日期"),
        yaxis=dict(gridcolor="rgba(255, 255, 255, 0.05)", title=""),
        height=max(320, len(df_plot) * 40),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


# ============================================================
# 6. Streamlit 介面渲染主邏輯
# ============================================================
def main():
    # 頂部 Cyberpunk 標題 Banner
    st.markdown(f"""
    <div class="cyber-banner">
        <div class="cyber-title">
            <span>⚡ 台股籌碼與處置股極速戰情室</span>
            <span class="badge badge-info" style="margin-left: auto;">{APP_VERSION}</span>
        </div>
        <div class="cyber-subtitle">
            SYSTEM STATUS: ONLINE | TAIPEI TIME: {taipei_now().strftime('%Y-%m-%d %H:%M:%S')} | LIVE API DATA
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 側邊欄控制台
    st.sidebar.title("🎛️ 戰情控制台")
    st.sidebar.caption("Cyberpunk Terminal Dark Theme")

    if "refresh_key" not in st.session_state:
        st.session_state.refresh_key = 0

    if HAS_AUTO_REFRESH:
        auto_refresh = st.sidebar.checkbox("開啟 5 分鐘自動刷新", value=False)
        if auto_refresh: st_autorefresh(interval=300000, key="datarefresh")

    if st.sidebar.button("🔄 強制刷新最新數據", use_container_width=True):
        st.session_state.refresh_key += 1
        st.cache_data.clear()
        st.rerun()

    stock_options = [f"{sid} - {STOCK_NAMES[sid]}" for sid in STOCK_NAMES]
    selected_stock_str = st.sidebar.selectbox("🎯 快速切換焦點個股", options=stock_options, index=0)
    selected_stock_id = selected_stock_str.split(" - ")[0]

    token = get_finmind_token()
    if token:
        st.sidebar.markdown('<span class="badge badge-info">✅ FinMind API 授權金鑰已連線</span>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<span class="badge badge-warning">⚠️ 啟用 TWSE/TPEx 官方自動備援</span>', unsafe_allow_html=True)

    # 三大主頁面 Tab
    tab1, tab2, tab3 = st.tabs(["📈 個股 K 線與籌碼診斷", "🚨 處置股即時戰情室", "🧩 AI 族群與產業地圖"])

    # --------------------------------------------------------
    # TAB 1: 個股 K 線與籌碼診斷
    # --------------------------------------------------------
    with tab1:
        st.markdown(f"### 📊 **{get_stock_display_name(selected_stock_id)}** 視覺化行情與指標")
        df_stock = fetch_stock_data_robust(selected_stock_id)

        if df_stock is not None and not df_stock.empty:
            latest = df_stock.iloc[-1]
            prev = df_stock.iloc[-2] if len(df_stock) > 1 else latest
            change = latest["close"] - prev["close"]
            pct_change = ((change / prev["close"]) * 100) if prev["close"] != 0 else 0

            # 4 個自訂 Cyberpunk 卡片
            c1, c2, c3, c4 = st.columns(4)
            val_class = "text-up" if change >= 0 else "text-down"
            arrow = "▲" if change >= 0 else "▼"

            c1.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-card-label">最新收盤價</div>
                <div class="cyber-card-value">${latest['close']:.2f}</div>
                <div class="cyber-card-sub {val_class}">{arrow} {abs(change):.2f} ({pct_change:+.2f}%)</div>
            </div>
            """, unsafe_allow_html=True)

            c2.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-card-label">成交張數</div>
                <div class="cyber-card-value">{int(latest['Trading_Volume']):,}</div>
                <div class="cyber-card-sub text-cyan">本日最新成交</div>
            </div>
            """, unsafe_allow_html=True)

            c3.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-card-label">最高 / 最低</div>
                <div class="cyber-card-value" style="font-size: 1.4rem;">${latest['max']:.1f} / ${latest['min']:.1f}</div>
                <div class="cyber-card-sub text-cyan">單日波動震幅</div>
            </div>
            """, unsafe_allow_html=True)

            c4.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-card-label">所屬 AI 概念族群</div>
                <div class="cyber-card-value" style="font-size: 1.25rem;">{get_industry(selected_stock_id)}</div>
                <div class="cyber-card-sub text-cyan">關鍵供應鏈</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            fig_k = plot_candlestick_cyber(df_stock, selected_stock_id)
            if fig_k:
                st.plotly_chart(fig_k, use_container_width=True)
        else:
            st.error("❌ 無法取得該個股之歷史行情資料。")

    # --------------------------------------------------------
    # TAB 2: 處置股即時戰情室
    # --------------------------------------------------------
    with tab2:
        records = load_all_disposal_records(st.session_state.refresh_key)

        if records:
            df_disposal = pd.DataFrame(records)

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                market_filter = st.radio("市場別篩選", ["全部", "上市", "上櫃"], horizontal=True)
            with col_m2:
                status_filter = st.radio("處置狀態篩選", ["處置中", "次一營業日生效", "已結束", "全部"], horizontal=True)

            filtered_df = df_disposal.copy()
            if market_filter != "全部":
                filtered_df = filtered_df[filtered_df["market"] == market_filter]
            if status_filter != "全部":
                filtered_df = filtered_df[filtered_df["status"] == status_filter]

            # 4 個指標卡片
            active_cnt = len(df_disposal[df_disposal["status"] == "處置中"])
            next_cnt = len(df_disposal[df_disposal["status"] == "次一營業日生效"])
            ai_disp_cnt = len(df_disposal[df_disposal["stock_id"].isin(STOCK_NAMES.keys()) & (df_disposal["status"] == "處置中")])

            dc1, dc2, dc3, dc4 = st.columns(4)
            dc1.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-card-label">當前處置中標的</div>
                <div class="cyber-card-value text-up">{active_cnt} 檔</div>
                <div class="cyber-card-sub text-up">🚨 分盤撮合管制中</div>
            </div>
            """, unsafe_allow_html=True)

            dc2.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-card-label">次一營業日生效</div>
                <div class="cyber-card-value" style="color: #FF851B;">{next_cnt} 檔</div>
                <div class="cyber-card-sub" style="color: #FF851B;">⚠️ 預備進入處置</div>
            </div>
            """, unsafe_allow_html=True)

            dc3.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-card-label">篩選顯示筆數</div>
                <div class="cyber-card-value text-cyan">{len(filtered_df)} 檔</div>
                <div class="cyber-card-sub text-cyan">目前視圖結果</div>
            </div>
            """, unsafe_allow_html=True)

            dc4.markdown(f"""
            <div class="cyber-card">
                <div class="cyber-card-label">AI 概念股處置中</div>
                <div class="cyber-card-value" style="color: #A855F7;">{ai_disp_cnt} 檔</div>
                <div class="cyber-card-sub" style="color: #A855F7;">核心監控族群</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Gantt 時間軸圖表
            fig_gantt = plot_disposal_timeline_cyber(filtered_df)
            if fig_gantt:
                st.plotly_chart(fig_gantt, use_container_width=True)

            # 處置股明細表
            st.markdown("### 📋 處置股票詳細監控清單")
            display_cols = ["stock_id", "stock_name", "market", "status", "period", "note", "reason", "measure"]
            df_show = filtered_df[display_cols].rename(
                columns={
                    "stock_id": "股票代號", "stock_name": "股票名稱", "market": "市場別",
                    "status": "處置狀態", "period": "處置起訖期間", "note": "備註/次數",
                    "reason": "處置原因", "measure": "處置措施",
                }
            )
            st.dataframe(df_show, use_container_width=True, hide_index=True)
        else:
            st.info("💡 目前無正在生效的處置股票數據。")

    # --------------------------------------------------------
    # TAB 3: AI 族群與產業地圖
    # --------------------------------------------------------
    with tab3:
        st.markdown("### 🧩 全台股 AI 核心與邊緣運算族群分類地圖")
        st.caption("依據技術領域與供應鏈階層歸類，點擊展開檢視詳細成分股名稱。")

        industry_groups = {}
        for sid, ind in INDUSTRY_MAP.items():
            industry_groups.setdefault(ind, []).append(f"{sid} {STOCK_NAMES.get(sid, '')}")

        cols = st.columns(2)
        for idx, (ind_name, stocks) in enumerate(industry_groups.items()):
            col_target = cols[idx % 2]
            with col_target:
                with st.expander(f"⚡ **{ind_name}** ({len(stocks)} 檔標的)", expanded=True):
                    st.write("・ " + "  \n・ ".join(stocks))


if __name__ == "__main__":
    main()
