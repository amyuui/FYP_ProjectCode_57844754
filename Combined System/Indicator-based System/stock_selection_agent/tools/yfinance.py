import yfinance as yf
import json
from datetime import datetime
from stock_selection_agent.data.market import fetch_stock_data
from stock_selection_agent.services.indicator import get_indicator_snapshot
from stock_selection_agent.services.screener import rank_momentum_stocks
from stock_selection_agent.services.signal import evaluate_buy_signal as evaluate_buy_signal_service
from stock_selection_agent.services.backtest import run_fuzzy_backtest
from stock_selection_agent.services.analysis import generate_investment_report as generate_investment_report_service
from stock_selection_agent.services.momentum import generate_momentum_report as generate_momentum_report_service
from stock_selection_agent.services.news_momentum import recommend_momentum_stocks_by_news, analyze_stock_events


def get_current_time():
    now = datetime.now().astimezone()
    result = {
        "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "timezone": str(now.tzinfo),
        "unix_timestamp": int(now.timestamp())
    }
    return json.dumps(result, ensure_ascii=False)

def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        result = {
            "symbol": ticker,
            "longName": info.get("longName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "marketCap": info.get("marketCap", None),
            "peRatio": info.get("trailingPE", None),
            "dividendYield": info.get("dividendYield", None),
            "52WeekHigh": info.get("fiftyTwoWeekHigh", None),
            "52WeekLow": info.get("fiftyTwoWeekLow", None),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"Error fetching info for {ticker}: {str(e)}"

def get_historical_data(ticker, period="6mo", interval="1d"):
    df = fetch_stock_data(ticker, period, interval)
    if df is None:
        return f"No data found for {ticker}"
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    return df.to_json(orient="records", date_format="iso")

def calculate_technical_indicators(ticker, period="6mo"):
    return get_indicator_snapshot(ticker=ticker, period=period, tail_size=30)

def find_momentum_stocks(tickers=None, period="3mo", top_n=10):
    return rank_momentum_stocks(tickers=tickers, period=period, top_n=top_n)

def generate_momentum_report(tickers=None, period="3mo", top_n=10, eval_top_k=3):
    return generate_momentum_report_service(
        tickers=tickers,
        period=period,
        top_n=top_n,
        eval_top_k=eval_top_k
    )

def evaluate_buy_signal(ticker, period="6mo"):
    return evaluate_buy_signal_service(ticker=ticker, period=period)

def run_backtest(ticker, start_date=None, end_date=None, initial_capital=100000, commission=0.0003, rsi_period=14):
    return run_fuzzy_backtest(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        commission=commission,
        rsi_period=rsi_period
    )

def generate_investment_report(ticker, signal_period="6mo", start_date=None, end_date=None):
    return generate_investment_report_service(
        ticker=ticker,
        signal_period=signal_period,
        start_date=start_date,
        end_date=end_date
    )

TOOL_REGISTRY = {
    "get_current_time": get_current_time,
    "get_stock_info": get_stock_info,
    "get_historical_data": get_historical_data,
    "calculate_technical_indicators": calculate_technical_indicators,
    "find_momentum_stocks": find_momentum_stocks,
    "generate_momentum_report": generate_momentum_report,
    "evaluate_buy_signal": evaluate_buy_signal,
    "run_backtest": run_backtest,
    "generate_investment_report": generate_investment_report,
    "recommend_momentum_stocks_by_news": recommend_momentum_stocks_by_news,
    "analyze_stock_events": analyze_stock_events,
}


def _parse_arguments(arguments):
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        if not arguments.strip():
            return {}
        return json.loads(arguments)
    raise ValueError("Arguments must be a JSON string or object.")


def execute_tool_call(tool_name, arguments):
    tool_fn = TOOL_REGISTRY.get(tool_name)
    if not tool_fn:
        return f"Error: Unknown tool '{tool_name}'"
    try:
        parsed_arguments = _parse_arguments(arguments)
    except Exception:
        return "Error: Invalid JSON arguments."
    return tool_fn(**parsed_arguments)
