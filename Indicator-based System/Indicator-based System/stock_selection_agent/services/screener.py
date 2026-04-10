import json
import pandas as pd
import yfinance as yf
from stock_selection_agent.data.market import fetch_stock_data
from stock_selection_agent.indicators.calculation import calculate_rsi, calculate_macd

DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "NFLX", "AVGO",
    "JPM", "BAC", "WFC", "GS", "MS", "V", "MA",
    "JNJ", "PFE", "MRK", "LLY", "UNH",
    "XOM", "CVX", "COP",
    "HD", "COST", "WMT", "TGT",
    "ORCL", "CRM", "ADBE", "INTC", "QCOM",
    "SPY", "QQQ", "IWM", "DIA", "SOXX"
]

def rank_momentum_stocks(tickers=None, period="3mo", top_n=10):
    if tickers is None:
        tickers = DEFAULT_TICKERS
    results = []
    for ticker in tickers:
        try:
            df = fetch_stock_data(ticker, period=period, interval="1d")
        except Exception:
            continue
        if df is None or len(df) < 50:
            continue
        df["Close"] = pd.to_numeric(df["Close"])
        df = calculate_rsi(df, period=14)
        df = calculate_macd(df)
        df["SMA_20"] = df["Close"].rolling(20).mean()
        df["SMA_50"] = df["Close"].rolling(50).mean()
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        score = 0
        reasons = []
        rsi = latest["RSI"]
        if pd.notna(rsi):
            if rsi > 70:
                score += 30
                reasons.append("RSI overbought (strong)")
            elif rsi > 50:
                score += 20
                reasons.append("RSI bullish")
            elif rsi > 30:
                score += 10
                reasons.append("RSI neutral")
            else:
                score -= 10
                reasons.append("RSI oversold (weak)")
        macd = latest["MACD"]
        signal = latest["MACD_signal"]
        if pd.notna(macd) and pd.notna(signal):
            if macd > signal and prev["MACD"] <= prev["MACD_signal"]:
                score += 30
                reasons.append("MACD golden cross")
            elif macd > signal:
                score += 20
                reasons.append("MACD bullish")
            elif macd < signal:
                score -= 10
                reasons.append("MACD bearish")
        close = latest["Close"]
        sma20 = latest["SMA_20"]
        sma50 = latest["SMA_50"]
        if pd.notna(sma20):
            if close > sma20:
                score += 15
                reasons.append("Price above SMA20")
            else:
                score -= 5
        if pd.notna(sma50):
            if close > sma50:
                score += 15
                reasons.append("Price above SMA50")
            else:
                score -= 5
        if len(df) >= 5:
            pct_change = (close / df.iloc[-5]["Close"] - 1) * 100
            if pct_change > 10:
                score += 20
                reasons.append(f"5-day gain {pct_change:.1f}%")
            elif pct_change > 5:
                score += 10
                reasons.append(f"5-day gain {pct_change:.1f}%")
            elif pct_change < -5:
                score -= 10
        results.append({
            "ticker": ticker,
            "name": yf.Ticker(ticker).info.get("longName", ticker),
            "raw_score": score,
            "reasons": ", ".join(reasons[:3])
        })

    if not results:
        return json.dumps([], ensure_ascii=False)

    raw_scores = [item["raw_score"] for item in results]
    min_raw = min(raw_scores)
    max_raw = max(raw_scores)
    for item in results:
        if max_raw == min_raw:
            normalized = 50
        else:
            normalized = round((item["raw_score"] - min_raw) * 100 / (max_raw - min_raw))
        item["momentum_score"] = int(max(0, min(100, normalized)))
        item["absolute_score"] = int(max(0, min(100, item["raw_score"])))
        del item["raw_score"]

    results.sort(key=lambda x: (x["momentum_score"], x["absolute_score"]), reverse=True)
    return json.dumps(results[:top_n], ensure_ascii=False)
