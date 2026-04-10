from datetime import datetime, timedelta
import time
import pandas as pd
import yfinance as yf


def _parse_date(date_value):
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        return date_value
    value = str(date_value).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {date_value}")


def _run_with_retry(fetch_fn, attempts=3):
    last_error = None
    for attempt in range(attempts):
        try:
            return fetch_fn()
        except Exception as error:
            last_error = error
            if attempt < attempts - 1:
                time.sleep(1.2 * (attempt + 1))
    if last_error:
        raise last_error
    return None


def _normalize_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        normalized = []
        for col in df.columns:
            if isinstance(col, tuple):
                normalized.append(col[0])
            else:
                normalized.append(col)
        df.columns = normalized
    return df


def _series_from_column(df, column_name):
    if column_name in df.columns:
        series_or_frame = df[column_name]
        if isinstance(series_or_frame, pd.DataFrame):
            return pd.to_numeric(series_or_frame.iloc[:, 0], errors="coerce")
        return pd.to_numeric(series_or_frame, errors="coerce")
    matched = [col for col in df.columns if str(col).lower() == column_name.lower()]
    if matched:
        return pd.to_numeric(df[matched[0]], errors="coerce")
    return None


def _ensure_date_column(df):
    if "Date" in df.columns:
        return df
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            df = df.rename(columns={column: "Date"})
            return df
    return df


def fetch_stock_data(ticker, period="6mo", interval="1d"):
    def _fetch():
        stock = yf.Ticker(ticker)
        return stock.history(period=period, interval=interval)

    df = _run_with_retry(_fetch, attempts=3)
    if df is None or df.empty:
        return None
    df = _normalize_columns(df)
    df = df.reset_index()
    df = _normalize_columns(df)
    df = _ensure_date_column(df)
    if "Date" not in df.columns:
        return None
    df["Date"] = pd.to_datetime(df["Date"])
    return df

def fetch_backtest_data(ticker, start_date, end_date, warmup_days=60):
    start_dt = _parse_date(start_date)
    end_dt = _parse_date(end_date)
    warmup_start = start_dt - timedelta(days=warmup_days)

    def _fetch():
        return yf.download(
            ticker,
            start=warmup_start.strftime("%Y-%m-%d"),
            end=end_dt.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=False
        )

    df = _run_with_retry(_fetch, attempts=3)
    if df is None:
        raise ValueError(f"No data found for {ticker}")
    if df.empty:
        raise ValueError(f"No data found for {ticker}")
    df = _normalize_columns(df)
    df = df.reset_index()
    df = _normalize_columns(df)
    df = _ensure_date_column(df)
    if "Date" not in df.columns:
        raise ValueError(f"Unexpected data format for {ticker}")
    df["trade_date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y%m%d")
    close_series = _series_from_column(df, "Close")
    if close_series is None:
        raise ValueError(f"Unexpected data format for {ticker}: missing Close")
    high_series = _series_from_column(df, "High")
    if high_series is None:
        raise ValueError(f"Unexpected data format for {ticker}: missing High")
    low_series = _series_from_column(df, "Low")
    if low_series is None:
        raise ValueError(f"Unexpected data format for {ticker}: missing Low")
    df["close"] = close_series
    df["high"] = high_series
    df["low"] = low_series
    volume_series = _series_from_column(df, "Volume")
    if volume_series is not None:
        df["vol"] = volume_series
    else:
        df["vol"] = 0
    df = df[["trade_date", "close", "high", "low", "vol"]].dropna(subset=["close", "high", "low"])
    df = df.sort_values("trade_date", ascending=True).reset_index(drop=True)
    return df
