import pandas as pd
from stock_selection_agent.data.market import fetch_stock_data
from stock_selection_agent.indicators.calculation import calculate_rsi, calculate_macd, calculate_so


def get_indicator_snapshot(ticker, period="6mo", tail_size=30):
    df = fetch_stock_data(ticker, period=period, interval="1d")
    if df is None:
        return f"No data for {ticker}"
    df["Close"] = pd.to_numeric(df["Close"])
    df["Volume"] = pd.to_numeric(df["Volume"])
    df["High"] = pd.to_numeric(df["High"])
    df["Low"] = pd.to_numeric(df["Low"])
    df = calculate_rsi(df, period=14)
    df = calculate_macd(df)
    df = calculate_so(df, k_period=14, d_period=3)
    result_df = df[["Date", "Close", "Volume", "RSI", "MACD", "MACD_signal", "MACD_hist", "SO_K", "SO_D"]].tail(tail_size).copy()
    result_df["Date"] = pd.to_datetime(result_df["Date"]).dt.strftime("%Y-%m-%d")
    result_df = result_df.round(2)
    return result_df.to_json(orient="records", date_format="iso")
