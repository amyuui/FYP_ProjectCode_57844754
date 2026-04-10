import json
import pandas as pd
from stock_selection_agent.data.market import fetch_stock_data
from stock_selection_agent.indicators.calculation import calculate_rsi, calculate_macd, calculate_so
from stock_selection_agent.strategy.fuzzy import normalize_series_to_100, fuzzify_condition, action_from_condition
from stock_selection_agent.services.recommendation import llm_defuzzify_recommendation


def evaluate_buy_signal(ticker, period="6mo"):
    df = fetch_stock_data(ticker, period=period, interval="1d")
    if df is None or df.empty:
        return f"No data for {ticker}"
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
    df["High"] = pd.to_numeric(df["High"], errors="coerce")
    df["Low"] = pd.to_numeric(df["Low"], errors="coerce")
    df = calculate_rsi(df, period=14)
    df = calculate_macd(df)
    df = calculate_so(df, k_period=14, d_period=3)
    latest = df.iloc[-1]
    df["macd_norm"] = normalize_series_to_100(df["MACD"])
    df["rsi_norm"] = pd.to_numeric(df["RSI"], errors="coerce").clip(lower=0, upper=100)
    df["so_norm"] = pd.to_numeric(df["SO_K"], errors="coerce").clip(lower=0, upper=100)
    latest_norm = df.iloc[-1]
    condition, memberships = fuzzify_condition(
        latest_norm["macd_norm"],
        latest_norm["rsi_norm"],
        latest_norm["so_norm"]
    )
    action = action_from_condition(condition)
    indicators = {
        "RSI": round(float(latest["RSI"]), 2) if pd.notna(latest["RSI"]) else None,
        "MACD": round(float(latest["MACD"]), 4) if pd.notna(latest["MACD"]) else None,
        "MACD_signal": round(float(latest["MACD_signal"]), 4) if pd.notna(latest["MACD_signal"]) else None,
        "SO_K": round(float(latest["SO_K"]), 2) if pd.notna(latest["SO_K"]) else None,
        "SO_D": round(float(latest["SO_D"]), 2) if pd.notna(latest["SO_D"]) else None
    }
    recommendation = llm_defuzzify_recommendation(
        ticker=ticker,
        condition=condition,
        action=action,
        indicators=indicators,
        timeframe=period
    )
    result = {
        "ticker": ticker,
        "timeframe": period,
        "strategy": "fuzzy_momentum",
        "condition": condition,
        "memberships": memberships,
        "rule_action": action,
        "recommendation": recommendation["recommendation"],
        "momentum_strength": recommendation["momentum_strength"],
        "reasoning": recommendation["reasoning"],
        "indicators": indicators
    }
    return json.dumps(result, ensure_ascii=False)
