# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 00:26:58 2026

@author: fujikake
"""

# 直近2日間で、ボリンジャーバンド±2σ越えした銘柄を抽出するアプリ

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import datetime

# =========================================================
# 設定値
# =========================================================
BB_PERIOD = 25
BB_SIGMA = 2
CHECK_DAYS = 2

# =========================================================
# CSV読み込み
# =========================================================
@st.cache_data
def load_stock_list(csv_path):
    return pd.read_csv(csv_path)

# =========================================================
# ボリンジャーバンド計算
# =========================================================
def calc_bollinger(df):

    close = df["Close"].squeeze()

    df["middle"] = close.rolling(BB_PERIOD).mean()

    df["std"] = close.rolling(BB_PERIOD).std()

    df["upper"] = (
        df["middle"]
        + BB_SIGMA * df["std"]
    )

    df["lower"] = (
        df["middle"]
        - BB_SIGMA * df["std"]
    )

    return df


# =========================================================
# ボリンジャーバンド突破銘柄抽出
# =========================================================
def get_bollinger_break_stocks(stock_list, df_master):

    results = []

    for code in stock_list:

        try:

            df = yf.download(
                code,
                period="6mo",
                progress=False
            )

            if len(df) < BB_PERIOD:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            df = calc_bollinger(df)

            recent = df.tail(CHECK_DAYS)

            for idx, row in recent.iterrows():

                if pd.isna(row["upper"]):
                    continue

                close_price = float(row["Close"])

                sigma = None

                std = row["std"]

                if pd.isna(std) or std == 0:
                    continue

                # +2σ超え
                if close_price > row["upper"]:

                    sigma = (
                        close_price - row["middle"]
                    ) / std

                # -2σ割れ
                elif close_price < row["lower"]:

                    sigma = (
                        close_price - row["middle"]
                    ) / std

                if sigma is not None:

                    brand_row = df_master[
                        df_master["ticker"] == code
                    ]

                    if len(brand_row) == 0:
                        brand = code
                    else:
                        brand = brand_row["brand"].iloc[0]

                    results.append({
                        "brand": brand,
                        "ticker": code,
                        "date": idx.strftime("%Y-%m-%d"),
                        "sigma": round(float(sigma), 2)
                    })

        except Exception as e:
            st.write(code, e)

    results = sorted(
        results,
        key=lambda x: abs(x["sigma"]),
        reverse=True
    )

    return results


# =========================================================
# ボリンジャーバンドグラフ
# =========================================================
def plot_bollinger(code):

    end = datetime.datetime.today()
    start = end - datetime.timedelta(days=90)

    df = yf.download(
        code,
        start=start,
        end=end,
        progress=False
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)

    df = calc_bollinger(df)

    break_up = df["Close"] > df["upper"]
    break_down = df["Close"] < df["lower"]

    fig = go.Figure()

    # Close
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name="Close",
            line=dict(
                color="black",
                width=2
            )
        )
    )

    # +2σ
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["upper"],
            mode="lines",
            name="+2σ",
            line=dict(
                color="red",
                width=1
            )
        )
    )

    # MA
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["middle"],
            mode="lines",
            name=f"MA{BB_PERIOD}",
            line=dict(
                color="blue",
                width=1
            )
        )
    )

    # -2σ
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["lower"],
            mode="lines",
            name="-2σ",
            line=dict(
                color="red",
                width=1
            )
        )
    )

    # +2σ突破
    fig.add_trace(
        go.Scatter(
            x=df.index[break_up],
            y=df["Close"][break_up],
            mode="markers",
            name="+2σ突破",
            marker=dict(
                color="red",
                size=10
            )
        )
    )

    # -2σ突破
    fig.add_trace(
        go.Scatter(
            x=df.index[break_down],
            y=df["Close"][break_down],
            mode="markers",
            name="-2σ突破",
            marker=dict(
                color="blue",
                size=10
            )
        )
    )

    fig.update_layout(
        title=f"{code} ボリンジャーバンド",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=700,
        hovermode="x unified"
    )

    return fig


# =========================================================
# Streamlit UI
# =========================================================
st.title("📈 ボリンジャーバンド ±2σ 抽出アプリ")

csv_path = st.selectbox(
    "銘柄リストを選択",
    [
        "paypay_japan_stocks_ticker.csv",
        "paypay_us_stocks_ticker.csv"
    ]
)

# =========================================================
# CSV読み込み
# =========================================================
if st.button("銘柄リストを読み込む"):

    df = load_stock_list(csv_path)

    st.success(
        f"{len(df)} 銘柄を読み込みました"
    )

    st.session_state["stock_list"] = df

# =========================================================
# 抽出
# =========================================================
if "stock_list" in st.session_state:

    df = st.session_state["stock_list"]

    if st.button("±2σ突破銘柄を抽出"):

        bb_list = get_bollinger_break_stocks(
            df["ticker"].tolist(),
            df
        )

        bb_df = pd.DataFrame(bb_list)

        if len(bb_df) > 0:

            st.write(
                "### 直近2営業日で±2σ突破した銘柄"
            )

            st.dataframe(
                bb_df,
                use_container_width=True
            )

            st.write("### 一覧")

            for _, row in bb_df.iterrows():

                sign = "+" if row["sigma"] > 0 else ""

                st.text(
                    f"{row['brand']} "
                    f"{row['ticker']} "
                    f"{sign}{row['sigma']}σ "
                    f"{row['date']}"
                )

            st.session_state["bb"] = bb_df

        else:

            st.warning(
                "直近2日で±2σを突破した銘柄はありません。"
            )

    # --------------------------------------------------
    # 銘柄選択
    # --------------------------------------------------
    selected_brand = st.selectbox(
        "銘柄を選択",
        df["brand"].tolist()
    )

    selected_code = df[
        df["brand"] == selected_brand
    ]["ticker"].iloc[0]

    # --------------------------------------------------
    # グラフ表示
    # --------------------------------------------------
    if st.button("グラフ表示"):

        fig = plot_bollinger(selected_code)

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------
    # 抽出結果保持
    # --------------------------------------------------
    if "bb" in st.session_state:

        st.write("### ±2σ突破銘柄（保持）")

        st.dataframe(
            st.session_state["bb"],
            use_container_width=True
        )