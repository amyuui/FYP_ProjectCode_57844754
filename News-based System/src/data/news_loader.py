from pathlib import Path
import pandas as pd
import re

DEFAULT_KAGGLE_FILENAMES = [
    "NEWS_YAHOO_stock_prediction.csv",
    "news_yahoo_stock_prediction.csv",
]

COMPANY_ALIASES = {
    "AAPL": {"AAPL", "APPLE"},
    "AMZN": {"AMZN", "AMAZON"},
    "GOOG": {"GOOG", "GOOGLE", "ALPHABET"},
    "GOOGL": {"GOOGL", "GOOGLE", "ALPHABET"},
    "META": {"META", "FACEBOOK", "META PLATFORMS"},
    "NFLX": {"NFLX", "NETFLIX"},
    "NVDA": {"NVDA", "NVIDIA"},
}

def _normalize_label(value):
    if pd.isna(value):
        return ""
    return str(value).strip().lower()

def _find_column(columns, candidates):
    normalized_map = {_normalize_label(column): column for column in columns}
    for candidate in candidates:
        match = normalized_map.get(_normalize_label(candidate))
        if match:
            return match
    return None

def _auto_detect_csv_path(csv_path=None):
    if csv_path:
        path = Path(csv_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Kaggle CSV not found: {path}")

    # Search in project root (parent of src/data)
    project_root = Path(__file__).resolve().parent.parent.parent

    for filename in DEFAULT_KAGGLE_FILENAMES:
        candidate = project_root / filename
        if candidate.exists():
            return candidate

    matches = sorted(project_root.glob("*stock*prediction*.csv"))
    if matches:
        return matches[0]

    raise FileNotFoundError(
        "Kaggle CSV not found. Place NEWS_YAHOO_stock_prediction.csv in the project folder "
        "or pass a csv_path explicitly."
    )

def _load_csv_frame(csv_path):
    try:
        return pd.read_csv(csv_path)
    except UnicodeDecodeError:
        return pd.read_csv(csv_path, encoding="latin1")

def _resolve_ticker_columns(dataframe):
    ticker_column = _find_column(
        dataframe.columns,
        ["ticker", "symbol", "stock_code", "stock", "stock_symbol"],
    )
    stock_name_column = _find_column(
        dataframe.columns,
        ["stock_name", "company", "company_name", "name"],
    )
    return ticker_column, stock_name_column

def _resolve_text_columns(dataframe):
    title_column = _find_column(
        dataframe.columns,
        ["event_title", "title", "headline", "news_title", "subject"],
    )
    content_column = _find_column(
        dataframe.columns,
        ["event_content", "content", "news", "description", "article", "body", "text", "summary"],
    )
    date_column = _find_column(
        dataframe.columns,
        ["event_date", "date", "datetime", "publish_date", "published_at", "timestamp"],
    )
    url_column = _find_column(
        dataframe.columns,
        ["url", "link", "source_url"],
    )
    return title_column, content_column, date_column, url_column

def _get_company_aliases(ticker):
    normalized_ticker = str(ticker).strip().upper()
    return COMPANY_ALIASES.get(normalized_ticker, {normalized_ticker})

def _contains_company_alias(text, aliases):
    if not text:
        return False

    normalized_text = str(text).upper()
    for alias in aliases:
        pattern = rf"(?<![A-Z0-9]){re.escape(alias.upper())}(?![A-Z0-9])"
        if re.search(pattern, normalized_text):
            return True
    return False

def _is_target_relevant_news(row, ticker, title_column, content_column):
    aliases = _get_company_aliases(ticker)
    title = ""
    content = ""

    if title_column and not pd.isna(row[title_column]):
        title = str(row[title_column]).strip()
    if content_column and not pd.isna(row[content_column]):
        content = str(row[content_column]).strip()

    if _contains_company_alias(title, aliases):
        return True

    leading_content = content[:400]
    return _contains_company_alias(leading_content, aliases)

def _row_matches_ticker(row, ticker, ticker_column, stock_name_column):
    ticker = str(ticker).strip().upper()
    possible_values = []

    if ticker_column:
        possible_values.append(str(row[ticker_column]).strip().upper())
    if stock_name_column:
        possible_values.append(str(row[stock_name_column]).strip().upper())

    allowed_values = _get_company_aliases(ticker)
    return any(value in allowed_values for value in possible_values if value and value != "NAN")

def _build_event_content(row, title_column, content_column, reserved_columns):
    parts = []

    if title_column and not pd.isna(row[title_column]):
        parts.append(str(row[title_column]).strip())

    if content_column and not pd.isna(row[content_column]):
        parts.append(str(row[content_column]).strip())

    if not parts:
        for column in row.index:
            if column in reserved_columns:
                continue
            value = row[column]
            if pd.isna(value):
                continue
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())

    content = " ".join(part for part in parts if part)
    return content[:8000]

def load_kaggle_historical_news(ticker, csv_path=None):
    csv_file = _auto_detect_csv_path(csv_path)
    dataframe = _load_csv_frame(csv_file)

    ticker_column, stock_name_column = _resolve_ticker_columns(dataframe)
    title_column, content_column, date_column, url_column = _resolve_text_columns(dataframe)

    if date_column is None:
        raise ValueError("Unable to find a date column in the Kaggle CSV.")

    if ticker_column is None and stock_name_column is None:
        raise ValueError("Unable to find ticker or company name columns in the Kaggle CSV.")

    filtered_rows = dataframe[
        dataframe.apply(
            lambda row: _row_matches_ticker(row, ticker, ticker_column, stock_name_column),
            axis=1,
        )
    ].copy()

    if filtered_rows.empty:
        return []

    filtered_rows = filtered_rows[
        filtered_rows.apply(
            lambda row: _is_target_relevant_news(row, ticker, title_column, content_column),
            axis=1,
        )
    ].copy()

    if filtered_rows.empty:
        return []

    filtered_rows[date_column] = pd.to_datetime(filtered_rows[date_column], errors="coerce")
    filtered_rows = filtered_rows.dropna(subset=[date_column]).sort_values(date_column)

    reserved_columns = {
        column
        for column in [ticker_column, stock_name_column, title_column, content_column, date_column, url_column]
        if column is not None
    }

    events = []
    for _, row in filtered_rows.iterrows():
        stock_code = ticker
        if ticker_column and not pd.isna(row[ticker_column]):
            stock_code = str(row[ticker_column]).strip().upper()

        stock_name = stock_code
        if stock_name_column and not pd.isna(row[stock_name_column]):
            stock_name = str(row[stock_name_column]).strip()

        title = ""
        if title_column and not pd.isna(row[title_column]):
            title = str(row[title_column]).strip()
        if not title:
            title = f"{stock_name} historical news"

        event_content = _build_event_content(row, title_column, content_column, reserved_columns)
        if not event_content:
            continue

        url = ""
        if url_column and not pd.isna(row[url_column]):
            url = str(row[url_column]).strip()

        events.append(
            {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "event_title": title,
                "event_content": event_content,
                "event_date": row[date_column].strftime("%Y-%m-%d %H:%M:%S"),
                "url": url,
            }
        )

    return events
