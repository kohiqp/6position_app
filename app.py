# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 00:26:58 2026

@author: fujikake
"""

import streamlit as st
import yfinance as yf
import talib as ta
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# ---------------------------------------------------------
#  CSVから銘柄リストを読み込む
# ---------------------------------------------------------
@st.cache_data
def load_stock_list(csv_path):
    df = pd.read_csv(csv_path)
    return df


# ---------------------------------------------------------
#  ポジション2判定ロジック（あなたの条件そのまま）
# ---------------------------------------------------------
def is_position2(df):
    latest = df.iloc[-1]

    open_ = latest["Open"]
    close_ = latest["Close"]
    ma5 = latest["ma5"]
    ma25 = latest["ma25"]

    # ポジション2条件
    return ((open_ > ma25) or (close_ > ma25)) and (ma25 > ma5)


# ---------------------------------------------------------
#  直近5日間でポジション2判定する関数
# ---------------------------------------------------------
def became_position2_recently(df, days=5):
    recent = df.tail(days)

    for i in range(len(recent)):
        row = recent.iloc[i]
        open_ = row["Open"]
        close_ = row["Close"]
        ma5 = row["ma5"]
        ma25 = row["ma25"]

        # MAが計算できていない日はスキップ
        if pd.isna(ma5) or pd.isna(ma25):
            continue

        # ポジション2条件
        if ((open_ > ma25) or (close_ > ma25)) and (ma25 > ma5):
            return True

    return False


# ---------------------------------------------------------
#  銘柄ごとにポジション2か判定
# ---------------------------------------------------------
def get_position2_stocks(stock_list, df_master):
    pos2 = []

    for code in stock_list:
        try:
            df = yf.download(code, period="6mo")
            df.columns = df.columns.droplevel(1)
            close = df["Close"].squeeze()

            df["ma5"] = ta.SMA(close, timeperiod=5)
            df["ma25"] = ta.SMA(close, timeperiod=25)

            recent = df.tail(5)

            pos2_day_close = None
            pos2_day_ma25 = None

            # 直近5日でポジション2になった日を探す
            for i in range(len(recent)):
                row = recent.iloc[i]
                open_ = row["Open"]
                close_ = row["Close"]
                ma5 = row["ma5"]
                ma25 = row["ma25"]

                if pd.isna(ma5) or pd.isna(ma25):
                    continue

                if ((open_ > ma25) or (close_ > ma25)) and (ma25 > ma5):
                    pos2_day_close = close_
                    pos2_day_ma25 = ma25
                    break

            # ポジション2になっていない銘柄はスキップ
            if pos2_day_close is None:
                continue

            # 乖離率計算
            kairi = (pos2_day_close - pos2_day_ma25) / pos2_day_ma25 * 100

            brand = df_master[df_master["ticker"] == code]["brand"].values[0]

            pos2.append((code, brand, kairi))

        except:
            pass

    # 乖離率降順に並べ替え
    pos2_sorted = sorted(pos2, key=lambda x: x[2], reverse=True)

    return pos2_sorted


# ---------------------------------------------------------
#  6ポジション判定ロジック（あなたのコードを完全移植）
# ---------------------------------------------------------
def calc_positions(df):
    positions = []

    for i in range(len(df)):
        open_ = df["Open"].iloc[i]
        close_ = df["Close"].iloc[i]
        ma5 = df["ma5"].iloc[i]
        ma25 = df["ma25"].iloc[i]

        pos = None

        # ポジション1
        if (open_ > ma5) and (close_ > ma5) and (ma5 > ma25):
            pos = 1

        # ポジション2
        elif ((open_ > ma25) or (close_ > ma25)) and (ma25 > ma5):
            pos = 2

        # ポジション3
        elif ((ma25 > open_ > ma5) or (ma25 > close_ > ma5)):
            pos = 3

        # ポジション4
        elif (ma25 > ma5) and (open_ < ma5) and (close_ < ma5):
            pos = 4

        # ポジション5
        elif ((open_ < ma25) or (close_ < ma25)) and (ma5 > ma25):
            pos = 5

        # ポジション6
        elif ((ma5 > open_ > ma25) or (ma5 > close_ > ma25)):
            pos = 6

        else:
            pos = 0  # 判定不能

        positions.append(pos)

    df["position"] = positions
    return df


# ---------------------------------------------------------
#  グラフ描画（あなたのPlotly構成を忠実に再現）
# ---------------------------------------------------------
def plot_6_positions(code):
    end = datetime.datetime.today()
    start = end - datetime.timedelta(days=180)

    df = yf.download(code, start=start, end=end)
    df.columns = df.columns.droplevel(1)
    close = df["Close"].squeeze()

    df["ma5"] = ta.SMA(close, timeperiod=5)
    df["ma25"] = ta.SMA(close, timeperiod=25)

    df = calc_positions(df)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )

    # --- 上段：ローソク足 ---
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Candlestick"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["ma5"],
        mode="lines",
        line=dict(color="blue", width=1.5),
        name="MA5"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["ma25"],
        mode="lines",
        line=dict(color="red", width=1.5),
        name="MA25"
    ), row=1, col=1)

    # --- 下段：ポジション番号 ---
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["position"],
        mode="lines+markers",
        line=dict(color="green", width=2),
        name="Position"
    ), row=2, col=1)

    fig.update_layout(
        title=f"{code} 6ポジショングラフ",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=800,
    )

    return fig


# ---------------------------------------------------------
#  Streamlit UI
# ---------------------------------------------------------
st.title("📈 6ポジション分析アプリ")

#csv_path = st.text_input("銘柄リストCSVのパス", "paypay_japan_stocks_ticker.csv")
csv_path = st.selectbox(
    "銘柄リストを選択",
    ["paypay_japan_stocks_ticker.csv", "paypay_us_stocks_ticker.csv"]
)

# 銘柄リスト読み込み
if st.button("銘柄リストを読み込む"):
    df = load_stock_list(csv_path)   # ← DataFrame のまま返す
    st.success(f"{len(df)} 銘柄を読み込みました。（{csv_path}）")
    st.session_state["stock_list"] = df

# 銘柄リストが読み込まれている場合
if "stock_list" in st.session_state:

    df = st.session_state["stock_list"]

    # ポジション2抽出
    if st.button("ポジション2の銘柄を抽出"):
        pos2_list = get_position2_stocks(df["ticker"].tolist(), df)
        #pos2_codes = get_position2_stocks(df["ticker"].tolist())

        # ticker → brand に変換
        pos2_df = pd.DataFrame(pos2_list, columns=["ticker", "brand", "kairi"])
        #pos2_df = df[df["ticker"].isin(pos2_codes)][["ticker", "brand"]]

        st.write("### ポジション2の銘柄一覧（乖離率順）")
        st.dataframe(pos2_df)
        st.session_state["pos2"] = pos2_df

    # 銘柄選択（brand で選択）
    selected_brand = st.selectbox(
        "銘柄を選択",
        df["brand"].tolist()
    )

    # 選択された brand → ticker に変換
    selected_code = df[df["brand"] == selected_brand]["ticker"].iloc[0]

    # グラフ表示
    if st.button("グラフ表示"):
        fig = plot_6_positions(selected_code)
        st.plotly_chart(fig, use_container_width=True)
        
    # ★ 追加：ポジション2一覧を常に表示
    if "pos2" in st.session_state:
        st.write("### ポジション2の銘柄一覧（保持）")
        st.dataframe(st.session_state["pos2"])
        