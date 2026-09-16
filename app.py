import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# ==========================================
# 1. 頁面基本設定
# ==========================================
st.set_page_config(
    page_title="高階資產管理 - 五維量化選股系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. 模擬股票清單與產業資料庫
# ==========================================
STOCK_NAMES = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
    "2382": "廣達", "3231": "緯創", "6669": "緯穎", "2356": "英業達",
    "3017": "奇鋐", "3324": "雙鴻", "3443": "創意", "3661": "世芯-KY",
    "2379": "瑞昱", "3034": "聯詠", "2303": "聯電", "3037": "欣興"
}

INDUSTRY_MAP = {
    "2330": "半導體", "2317": "鴻海家族", "2454": "IC設計", "2308": "電源/電源供應器",
    "2382": "AI伺服器", "3231": "AI伺服器", "6669": "AI伺服器", "2356": "代工/組裝",
    "3017": "液冷/散熱", "3324": "液冷/散熱", "3443": "IP矽智財", "3661": "IP矽智財",
    "2379": "IC設計", "3034": "IC設計", "2303": "半導體晶圓", "3037": "ABF載板"
}

def get_industry(sid):
    return INDUSTRY_MAP.get(sid, "其他")

# ==========================================
# 3. 模擬 K 線歷史數據生成器
# ==========================================
@st.cache_data(ttl=3600)
def fetch_stock_data_robust(sid):
    """模擬生成該股票近 60 天的價格與成交量數據"""
    random.seed(int(sid))
    np.random.seed(int(sid))
    
    dates = [datetime.now() - timedelta(days=i) for i in range(60)]
    dates.reverse()
    
    base_price = random.uniform(50, 800)
    returns = np.random.normal(0.001, 0.02, size=60)
    price_path = base_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        "date": dates,
        "close": price_path,
        "Trading_Volume": np.random.randint(2000, 50000, size=60)
    })
    return df

# ==========================================
# 4. 五維一體量化篩選核心邏輯
# ==========================================
@st.cache_data(ttl=3600)
def fetch_smart_screening_results_five_dimensions(bias_min, bias_max, rev_min):
    watch_list = list(INDUSTRY_MAP.keys())
    results = []
    
    for sid in watch_list:
        sname = STOCK_NAMES.get(sid, "個股")
        ind = get_industry(sid)
        df_s = fetch_stock_data_robust(sid)
        
        if df_s is not None and len(df_s) >= 20:
            df_s = df_s.sort_values("date")
            close_price = df_s["close"].iloc[-1]
            c_prev = df_s["close"].iloc[-2]
            pct_chg = (close_price - c_prev) / c_prev * 100
            
            ma5 = df_s["close"].tail(5).mean()
            ma10 = df_s["close"].tail(10).mean()
            ma20 = df_s["close"].tail(20).mean()
            vol_mean = df_s["Trading_Volume"].tail(20).mean()
            curr_vol = df_s["Trading_Volume"].iloc[-1]
            
            # 計算月線乖離率 (BIAS_20MA %)
            bias_20 = ((close_price - ma20) / ma20) * 100
            
            # 建立種子確保每次資料擬真且固定
            random.seed(int(sid) + 88)
            
            # 1. 基本面: 近月營收年增率 > 門檻
            revenue_yoy = round(random.uniform(-5.0, 35.0), 1)
            cond_fundamental = revenue_yoy >= rev_min
            
            # 2. 籌碼面: 法人買超 + 融資沉澱
            inst_net_buy = random.choice([True, True, False])
            margin_ratio_low = random.choice([True, False, True])
            cond_chip_quality = inst_net_buy and margin_ratio_low
            
            # 3. 技術面多頭: Close > 5MA > 10MA > 20MA
            cond_tech_ma = (close_price > ma5) and (ma5 > ma10) and (ma10 > ma20)
            
            # 4. 健康量價配合: 當日量 > 20日均量 * 1.1 且 漲幅 > 1.0%
            cond_healthy_volume = (curr_vol > vol_mean * 1.1) and (pct_chg > 1.0)
            
            # 5. 🔥 第五個濾網【安全邊界/防追高】: 月線乖離率在設定的安全區間內
            cond_safety_margin = (bias_min <= bias_20 <= bias_max)
            
            matched_count = sum([cond_fundamental, cond_chip_quality, cond_tech_ma, cond_healthy_volume, cond_safety_margin])
            
            results.append({
                "股票代碼": sid,
                "股票名稱": sname,
                "產業類別": ind,
                "收盤價": round(close_price, 2),
                "漲跌幅(%)": round(pct_chg, 2),
                "營收YoY(%)": revenue_yoy,
                "月線乖離率(%)": round(bias_20, 2),
                "法人動向": "買超" if inst_net_buy else "賣超/觀望",
                "融資籌碼": "沉澱" if margin_ratio_low else "暴增",
                "1.基本面": "✅" if cond_fundamental else "❌",
                "2.籌碼面": "✅" if cond_chip_quality else "❌",
                "3.技術面": "✅" if cond_tech_ma else "❌",
                "4.量價面": "✅" if cond_healthy_volume else "❌",
                "5.安全邊界": "✅" if cond_safety_margin else "❌",
                "符合條件數": matched_count
            })
            
    return pd.DataFrame(results)

# ==========================================
# 5. Streamlit 主介面渲染
# ==========================================
def main():
    st.title("🛡️ 五維一體法人級量化篩選系統")
    st.caption("基本面 × 籌碼質化 × 技術多頭 × 量價攻擊 × 安全邊界防追高")
    st.markdown("---")

    # 側邊欄控制選單
    st.sidebar.header("🎛️ 濾網參數設定")
    
    st.sidebar.subheader("5. 安全邊界濾網 (防追高)")
    bias_range = st.sidebar.slider(
        "月線乖離率 (BIAS 20MA %) 容許區間",
        min_value=-5.0,
        max_value=20.0,
        value=(0.0, 8.5),
        step=0.5,
        help="控制在 0%~8.5% 代表只挑選『剛突破起漲』或『拉回月線尋求支撐成功』的個股，剔除過熱追高標的。"
    )
    
    st.sidebar.subheader("1. 基本面門檻")
    rev_min = st.sidebar.number_input("營收年增率 (YoY %) 下限", value=8.0, step=1.0)

    # 載入五維數據
    df_results = fetch_smart_screening_results_five_dimensions(bias_range[0], bias_range[1], rev_min)

    # 關鍵指標 KPI 區塊
    total_stocks = len(df_results)
    full_match = df_results[df_results["符合條件數"] == 5]
    four_match = df_results[df_results["符合條件數"] == 4]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("觀察池標的總數", f"{total_stocks} 檔")
    col2.metric("🏆 五維全滿貫標的", f"{len(full_match)} 檔", delta="核心精選")
    col3.metric("⭐ 符合 4 項強勢標的", f"{len(four_match)} 檔")
    col4.metric("設定乖離率上限", f"{bias_range[1]} %", delta="防追高門檻")

    st.markdown("---")

    # 篩選標準說明卡片
    with st.expander("📌 點擊檢視「五維量化濾網」檢驗標準說明", expanded=False):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown("**1. 基本面**\n營收 YoY > " + str(rev_min) + "%")
        c2.markdown("**2. 籌碼面**\n三大法人買超 + 融資沉澱")
        c3.markdown("**3. 技術面**\n多頭排列 (C > 5 > 10 > 20MA)")
        c4.markdown("**4. 量價面**\n攻擊量增 (量 > 1.1倍 且 漲 > 1%)")
        c5.markdown("**5. 安全邊界**\n月線乖離率 " + str(bias_range[0]) + "% ~ " + str(bias_range[1]) + "%")

    # 篩選頁籤
    tab1, tab2, tab3 = st.tabs(["🔥 完整結果清單", "🏆 5維精選 (全滿貫)", "📊 產業分佈與分析"])

    with tab1:
        st.subheader("全標的篩選矩陣")
        
        # 可依據符合條件數篩選
        min_match = st.radio("篩選符合條件數：", options=[0, 3, 4, 5], index=0, horizontal=True)
        filtered_df = df_results[df_results["符合條件數"] >= min_match].sort_values(
            by=["符合條件數", "月線乖離率(%)"], ascending=[False, True]
        )
        
        st.dataframe(
            filtered_df,
            column_config={
                "股票代碼": st.column_config.TextColumn("代碼"),
                "漲跌幅(%)": st.column_config.NumberColumn("漲跌幅%", format="%.2f%%"),
                "營收YoY(%)": st.column_config.NumberColumn("營收YoY%", format="%.1f%%"),
                "月線乖離率(%)": st.column_config.NumberColumn("月線乖離率%", format="%.2f%%"),
                "符合條件數": st.column_config.ProgressColumn("條件匹配度", min_value=0, max_value=5, format="%d / 5")
            },
            hide_index=True,
            use_container_width=True
        )

    with tab2:
        st.subheader("🏆 五維一體黃金標的 (完美符合 5/5 條件)")
        if len(full_match) > 0:
            for _, row in full_match.iterrows():
                with st.container():
                    st.success(f"### **{row['股票代碼']} {row['股票名稱']}** ({row['產業類別']})")
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    mc1.metric("收盤價", f"{row['收盤價']} 元", f"{row['漲跌幅(%)']}%")
                    mc2.metric("營收 YoY", f"{row['營收YoY(%)']}%")
                    mc3.metric("月線乖離率", f"{row['月線乖離率(%)']}%", "安全起漲區")
                    mc4.metric("籌碼狀態", f"{row['法人動向']} / 融資{row['融資籌碼']}")
                    st.markdown("---")
        else:
            st.warning("當前篩選條件下，暫無完美符合 5 項條件的標的，建議可微調左側乖離率區間。")

    with tab3:
        st.subheader("符合 4 項以上標的之產業分佈")
        high_quality_df = df_results[df_results["符合條件數"] >= 4]
        if len(high_quality_df) > 0:
            ind_counts = high_quality_df["產業類別"].value_counts()
            st.bar_chart(ind_counts)
        else:
            st.info("尚無足夠的高品質標的供產業統計。")

if __name__ == "__main__":
    main()
