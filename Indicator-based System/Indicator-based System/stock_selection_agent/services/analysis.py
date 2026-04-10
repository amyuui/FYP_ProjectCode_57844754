import json
from stock_selection_agent.services.signal import evaluate_buy_signal
from stock_selection_agent.services.backtest import run_fuzzy_backtest
from stock_selection_agent.services.report import build_investment_report


def generate_investment_report(ticker, signal_period="6mo", start_date=None, end_date=None):
    signal_raw = evaluate_buy_signal(ticker=ticker, period=signal_period)
    signal_data = json.loads(signal_raw) if isinstance(signal_raw, str) else signal_raw
    backtest_raw = run_fuzzy_backtest(ticker=ticker, start_date=start_date, end_date=end_date)
    backtest_data = json.loads(backtest_raw) if isinstance(backtest_raw, str) else backtest_raw
    if not isinstance(signal_data, dict):
        return json.dumps({"error": f"Invalid signal output for {ticker}"}, ensure_ascii=False)
    if not isinstance(backtest_data, dict) or "annualized_return" not in backtest_data:
        return json.dumps({"error": f"Invalid backtest output for {ticker}", "raw": backtest_raw}, ensure_ascii=False)
    recommendation_json = {
        "recommendation": signal_data["recommendation"],
        "momentum_strength": signal_data["momentum_strength"],
        "reasoning": signal_data["reasoning"]
    }
    report = build_investment_report(
        ticker=ticker,
        recommendation_json=recommendation_json,
        backtest_json=backtest_data,
        backtest_period="1Y"
    )
    result = {
        "ticker": ticker,
        "recommendation_json": recommendation_json,
        "backtest": backtest_data,
        "report_markdown": report
    }
    return json.dumps(result, ensure_ascii=False)
