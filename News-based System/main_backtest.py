import datetime
import os
import pandas as pd
from src.utils.config import DEEPSEEK_API_KEY
from src.core.llm_analyzer import LLMAnalyzer
from src.core.fuzzy_trader import FuzzyTrader
from src.core.backtester import Backtester
from src.data.news_loader import load_kaggle_historical_news
from src.processing.signal_processor import aggregate_daily_news, normalize_trading_signals

import os

def run_system_backtest(
    ticker="AAPL",
    historical_csv_path=None,
    start_date=None,
    end_date=None,
):
    api_key = DEEPSEEK_API_KEY or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY not found.")
        return

    analyzer = LLMAnalyzer(api_key)
    fuzzy_trader = FuzzyTrader()
    
    print(f"Loading historical Kaggle news events for {ticker}...")
    try:
        events = load_kaggle_historical_news(ticker, csv_path=historical_csv_path)
    except Exception as error:
        print(f"Failed to load historical Kaggle CSV: {error}")
        return
    
    if not events:
        print(f"No news events found for {ticker}.")
        return

    if not start_date or not end_date:
        print("Error: start_date and end_date are required for backtesting.")
        return

    cutoff_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    reference_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')

    filtered_raw_events = []
    for event in events:
        date_str = event.get('event_date')
        if not date_str or date_str == "Unknown":
            continue
        try:
            event_date = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            if cutoff_date <= event_date <= reference_date:
                filtered_raw_events.append(event)
        except ValueError:
            continue

    if not filtered_raw_events:
        print(f"No news events found for {ticker} within the testing window ({cutoff_date.date()} to {reference_date.date()}).")
        return

    print(f"Analyzing {len(filtered_raw_events)} events to generate trading signals...")
    
    analyzed_events = aggregate_daily_news(
        filtered_raw_events,
        analyzer,
        fuzzy_trader,
        range_start=cutoff_date,
        range_end=reference_date,
        ticker=ticker,
    )

    actionable_events = [event for event in analyzed_events if event['prediction'] in ['rise', 'fall']]
    if not actionable_events:
        print("No actionable signals generated from daily summaries.")
        return

    normalized_events = normalize_trading_signals(actionable_events)
        
    backtester = Backtester(initial_capital=100000)

    signals = []
    for event in normalized_events:
        event_date = datetime.datetime.strptime(event['event_date'], '%Y-%m-%d %H:%M:%S')
        signals.append({
            'date': event_date,
            'prediction': event['prediction'],
            'title': event.get('event_title'),
            'reason': event.get('reason'),
        })

    print("\n" + "=" * 40)
    print(f"📈 BACKTEST PERIOD: {start_date} to {end_date}")
    print("=" * 40)
    if not signals:
        print("No actionable signals in this period.")
        return {}

    metrics = backtester.run_backtest(
        ticker,
        signals,
        period_label=f"{start_date} to {end_date}",
        start_date=cutoff_date,
        end_date=reference_date,
    )
    
    summary_metrics = {}
    if metrics:
        summary_metrics["custom_period"] = metrics
        print(f"\n--- Results for {start_date} to {end_date} ---")
        for metric, value in metrics.items():
            print(f"{metric}: {value}")
    else:
        print(f"\n--- Results for {start_date} to {end_date} ---")
        print("Backtest could not be completed.")

    return summary_metrics

if __name__ == "__main__":
    run_system_backtest(
        "AAPL",
        start_date="2017-01-27",
        end_date="2020-01-27",
    )
