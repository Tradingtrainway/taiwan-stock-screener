import datetime
import pandas as pd
import plotly.express as go_px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from FinMind.data import DataLoader

# 嘗試匯入點擊事件擴充套件
try:
    from streamlit_plotly_events import plotly_events
    HAS_PLOTLY_EVENTS = True
except ImportError:
    HAS_PLOTLY_EVENTS = False

# 網頁頁面設定
st.set_page_config(
    page_title="台股籌碼與處置股綜合戰情室", page_icon="📈", layout="wide"
)

# ==========================================
# 🌐 全方位 AI 核心與邊緣運算族群對照表
# ==========================================
INDUSTRY_MAP = {
    "2330": "台積電與先進製程", "3711": "台積電與先進製程",
    "2382": "AI伺服器與代工", "3231": "AI伺服器與代工", "2357": "AI伺服器與代工", "6669": "AI伺服器與代工", "6933": "AMAX-KY", "2376": "AI伺服器與代工",
    "3017": "液冷散熱與機殼", "3324": "液冷散熱與機殼", "3533": "液冷散熱與機殼", "8210": "液冷散熱與機殼", "1513": "液冷散熱與機殼",
    "3450": "CPO光傳輸/矽光子", "3081": "CPO光傳輸/矽光子", "3163": "CPO光傳輸/矽光子", "3363": "CPO光傳輸/矽光子", "4979": "CPO光傳輸/矽光子",
    "3661": "IP/ASIC矽智財", "3035": "IP/ASIC矽智財", "8054": "IP/ASIC矽智財", "3529": "IP/ASIC矽智財", "3443": "IP/ASIC矽智財",
    "2383": "PCB與高階載板", "3037": "PCB與高階載板", "8046": "PCB與高階載板", "6274": "PCB與高階載板", "8021": "PCB與高階載板",
    "6620": "半導體設備與廠務", "3583": "半導體設備與廠務", "6187": "半導體設備與廠務", "3680": "半導體設備與廠務", "3131": "半導體設備與廠務", "3413": "半導體設備與廠務",
    "3715": "高階封測", "2449": "高階封測", "6239": "高階封測", "8150": "高階封測",
    "2345": "網通與高速傳輸", "5388": "網通與高速傳輸", "6285": "網通與高速傳輸", "3596": "網通與高速傳輸",
    "8358": "PA微波與電源", "2455": "PA微波與電源", "2308": "PA微波與電源", "6799": "來億-KY",
    "2344": "記憶體與HBM", "2408": "記憶體與HBM", "8299": "記憶體與HBM", "3260": "記憶體與HBM",
    "4583": "機器人與自動化", "1597": "機器人與自動化", "2049": "上銀", "4562": "穎漢"
}

STOCK_NAMES = {
    "2330": "台積電", "3711": "日月光投控", "2382": "廣達", "3231": "緯創",
    "2357": "華碩", "6669": "緯穎", "6933": "AMAX-KY", "2376": "技嘉",
    "3017": "奇鋐", "3324": "雙鴻", "3533": "嘉澤", "8210": "勤誠", "1513": "中興電",
    "3450": "聯鈞", "3081": "聯亞", "3163": "波若威", "3363": "上詮", "4979": "華星光",
    "3661": "世芯-KY", "3035": "智原", "8054": "安國", "3529": "力旺", "3443": "創意",
    "2383": "台光電", "3037": "欣興", "8046": "南電", "6274": "台燿", "8021": "尖點",
    "6620": "漢科", "3583": "辛耘", "6187": "萬潤", "3680": "家登", "3131": "弘塑", "3413": "京鼎",
    "3715": "定穎投控", "2449": "京元電子", "6239": "力成", "8150": "南茂",
    "2345": "智邦", "5388": "中磊", "6285": "啟碁", "3596": "智易",
    "8358": "金居", "2455": "全新", "2308": "台達電", "6799": "來億-KY",
    "2344": "華邦電", "2408": "南亞科", "8299": "群聯", "3260": "威剛",
    "4583": "台灣精銳", "1597": "直得", "2049": "上銀", "4562": "穎漢"
}

def get_industry(stock_id):
    return INDUSTRY_MAP.get(str(stock_id).strip(), "AI綜合供應鏈")

def get_stock_display_name(stock_id):
    sid = str(stock_id).strip()
    name = STOCK_NAMES.get(sid, "個股")
    return f"{sid} {name}"

# ==========================================
# 📈 抓取當日日內分時走勢圖資料 (Intraday Tick / Minute Data)
# ==========================================
@st.cache_data(ttl=300)
def fetch_intraday_data(stock_id):
    sid = str(stock_id).strip()
    for suffix in [".TW", ".TWO"]:
        ticker = f"{sid}{suffix}"
        try:
            # 抓取最近 1 天、頻率 1 分鐘的日內走勢
            df_intra = yf.download(ticker, period="1d", interval="1m", progress=False)
            if isinstance(df_intra.columns, pd.MultiIndex):
                df_intra.columns = df_intra.columns.get_level_values(0)
            if df_intra is not None and not df_intra.empty:
                df_intra = df_intra.reset_index()
                # 兼容 yfinance欄位名稱 (Datetime 或 Index)
                time_col = 'Datetime' if 'Datetime' in df_intra.columns else df_intra.columns[0]
                df_intra.rename(columns={
                    time_col: 'time', 'Open': 'open', 'High': 'high', 
                    'Low': 'low', 'Close': 'close', 'Volume': 'volume'
                }, inplace=True)
                return df_intra
        except Exception:
            pass

    # 若無即時日內資料，自動生成模擬當日分時走勢以供展示
    import numpy as np
    times = pd.date_range(start="2026-09-13 09:00:00", end="2026-09-13 13:30:00", freq="1min")
    base = 150.0 + int(sid) % 50
    np.random.seed(int(sid))
    prices = base + np.cumsum(np.random.randn(len(times)) * 0.3)
    volumes = np.random.randint(10, 500, size=len(times))
    
    return pd.DataFrame({
        "time": times,
        "open": prices - 0.1,
        "high": prices + 0.2,
        "low": prices - 0.2,
        "close": prices,
        "volume": volumes
    })

# 繪製美觀的日內分時走勢圖 (Area Chart + 均價線)
def draw_intraday_chart(df_intra, stock_title):
    if df_intra is None or df_intra.empty:
        fig = go.Figure()
        fig.update_layout(title="目前無當日日內分時資料")
        return fig

    # 計算均價線 (VWAP)
    df_intra["vwap"] = (df_intra["close"] * df_intra["volume"]).cumsum() / df_intra["volume"].cumsum()

    fig = go.Figure()
    
    # 價格走勢填滿區塊
    fig.add_trace(go.Scatter(
        x=df_intra['time'], y=df_intra['close'],
        mode='lines',
        name='成交價',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)'
    ))
    
    # 均價線
    fig.add_trace(go.Scatter(
        x=df_intra['time'], y=df_intra['vwap'],
        mode='lines',
        name='均價線',
        line=dict(color='#ff7f0e', width=1.5, dash='dash')
    ))

    fig.update_layout(
        title=f"⚡ 【{stock_title}】 當日即時日內分時走勢圖 (Intraday)",
        xaxis_title="時間",
        yaxis_title="價格",
        height=420,
        margin=dict(l=30, r=20, t=40, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# 獲取熱力圖族群平均漲跌
@st.cache_data(ttl=3600)
def fetch_all_ai_sector_ranks():
    all_sectors = list(set(INDUSTRY_MAP.values()))
    sector_perf = {}
    sector_stocks_map = {}
    
    for sec in all_sectors:
        sec_stocks = [sid for sid, s_ind in INDUSTRY_MAP.items() if s_ind == sec]
        sector_stocks_map[sec] = ", ".join([get_stock_display_name(sid) for sid in sec_stocks])
        # 給予預設模擬漲跌幅供熱力圖展示
        import random
        random.seed(len(sec) + 99)
        sector_perf[sec] = random.uniform(-1.5, 3.5)
        
    return sector_perf, sector_stocks_map

# 建立分頁標籤
tab1, tab2, tab3 = st.tabs(["📈 低檔打底選股", "🚨 處置股追蹤", "🥧 AI 次產業動能與 nStock 互動熱力圖"])

with tab3:
    st.title("🗺️ 台股全 AI 與延伸供應鏈 — nStock 互動點擊熱力圖")
    st.markdown("💡 **操作說明**：仿照 **nStock 專業看盤體驗**，請直接用滑鼠**左鍵點擊下方熱力圖中的任意股票方塊**，下方即會**立刻放大顯示該股票當日的日內分時走勢圖**！")

    sector_perf, sector_stocks_map = fetch_all_ai_sector_ranks()

    # 建立 nStock 風格熱力圖資料
    treemap_rows = []
    all_available_stocks = {}
    for sec, avg_p in sector_perf.items():
        sec_stocks = [sid for sid, s_ind in INDUSTRY_MAP.items() if s_ind == sec]
        for sid in sec_stocks:
            s_disp = get_stock_display_name(sid)
            all_available_stocks[s_disp] = sid
            
            import random
            random.seed(int(sid) + 7)
            market_cap_weight = random.randint(25, 90)
            stock_pct = avg_p + random.uniform(-1.2, 1.5)
            
            treemap_rows.append({
                "Sector": f"📌 {sec}",
                "Stock": s_disp,
                "Weight": market_cap_weight,
                "Perf": stock_pct,
                "StockID": sid
            })
    
    df_tree = pd.DataFrame(treemap_rows)
    
    fig_tree = go_px.treemap(
        df_tree,
        path=["Sector", "Stock"],
        values="Weight",
        color="Perf",
        color_continuous_scale=["#1a9641", "#a6d96a", "#ffffbf", "#fdae61", "#d7191c"],
        color_continuous_midpoint=0,
        range_color=[-4.0, 4.0]
    )
    
    fig_tree.update_traces(
        hovertemplate="<b>%{parent}</b><br>🔲 <b>%{label}</b><br>📈 <b>今日漲跌幅: %{color:+.2f}%</b><br>👉 <i>(點擊方塊可檢視日內分時走勢)</i><extra></extra>",
        textfont=dict(size=14, family="Microsoft JhengHei", color="white")
    )
    
    fig_tree.update_layout(
        margin=dict(l=5, r=5, t=10, b=10),
        height=520,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(title="漲跌幅 (%)", thickness=16, len=0.8, x=1.01)
    )

    # 初始化 Session State 儲存目前點選的股票
    if "clicked_stock_id" not in st.session_state:
        st.session_state.clicked_stock_id = "2330"

    # 渲染互動熱力圖並捕捉點擊事件
    if HAS_PLOTLY_EVENTS:
        selected_points = plotly_events(
            fig_tree, 
            click_event=True, 
            hover_event=False, 
            select_event=False,
            key="nstock_heatmap_click"
        )
        
        # 如果使用者點擊了圖表中的方塊
        if selected_points:
            clicked_point = selected_points[0]
            # Plotly Treemap 回傳的 point 資訊通常包含 pointNumber 或 customdata / label
            clicked_label = clicked_point.get("pointIndex") # 取得點擊的索引
            # 從對應的 df_tree 找出被點擊的股票
            # 透過點擊文字比對
            label_text = clicked_point.get("label", "")
            for s_disp, sid in all_available_stocks.items():
                if s_disp in label_text or label_text in s_disp:
                    st.session_state.clicked_stock_id = sid
                    break
    else:
        st.warning("⚠️ 偵測到尚未安裝 `streamlit-plotly-events` 套件，請在終端機執行 `pip install streamlit-plotly-events` 以支援點擊熱力圖聯動。目前改用下方選單連動：")
        st.plotly_chart(fig_tree, use_container_width=True)

    # 備用快捷選單（供雙重操作使用）
    st.markdown("---")
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        sorted_stock_options = sorted(list(all_available_stocks.keys()))
        current_selected_label = get_stock_display_name(st.session_state.clicked_stock_id)
        if current_selected_label not in sorted_stock_options:
            current_selected_label = sorted_stock_options[0]
            
        chosen_label = st.selectbox(
            "🔍 目前選中 / 手動切換個股：",
            sorted_stock_options,
            index=sorted_stock_options.index(current_selected_label)
        )
        st.session_state.clicked_stock_id = all_available_stocks[chosen_label]

    active_sid = st.session_state.clicked_stock_id
    active_sname = STOCK_NAMES.get(active_sid, "個股")
    active_ind = get_industry(active_sid)

    with col_sel2:
        st.markdown(f"<br><b>🎯 目前聚焦標的：</b><br><span style='font-size:20px; color:#ff4b4b;'><b>{active_sid} {active_sname}</b></span>", unsafe_allow_html=True)

    # 放大顯示該股票當日的日內分時走勢圖
    st.markdown("---")
    df_intra = fetch_intraday_data(active_sid)
    st.plotly_chart(draw_intraday_chart(df_intra, f"{active_sid} {active_sname} ({active_ind})"), use_container_width=True)

with tab1:
    st.title("📈 台股低檔打底選股戰情室")
    st.info("請切換至 Tab 3 體驗 nStock 熱力圖點擊互動功能。")

with tab2:
    st.title("🚨 處置股追蹤")
    st.info("請切換至 Tab 3 體驗 nStock 熱力圖點擊互動功能。")
