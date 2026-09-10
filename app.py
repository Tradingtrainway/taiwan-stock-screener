# 1. 定義要排除的「大型權值股/ETF」（這些不適合做短線波段）
heavy_weights = ["2330", "2454", "2317", "2454", "2308", "2881", "2882"]

# 2. 加入短線量能條件 (今日成交量 > 5日均量 1.2 倍)
df_today["Vol_MA5"] = df_all.groupby("StockID")["Trading_Volume"].transform(
    lambda x: x.rolling(5).mean()
)
df_today["Vol_Burst"] = (
    df_today["Trading_Volume"] > df_today["Vol_MA5"] * 1.2
)

# 3. 升級版短線選股條件
df_filtered = df_today[
    (~df_today["StockID"].isin(heavy_weights))  # 條件 A：排除大型權值股
    & (df_today["close"] > df_today["MA20"])  # 條件 B：站上 20MA
    & (df_today["close"] > df_today["MA60"])  # 條件 C：站上 60MA
    & (df_today["SITC_Consecutive_Days"] >= min_days)  # 條件 D：投信連買
    & (df_today["SITC_Ratio"] >= min_ratio)  # 條件 E：投信買超佔比 (建議調高至 5%)
    & (df_today["Vol_Burst"])  # 條件 F：今日有爆量動能
]
