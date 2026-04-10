import datetime
import pandas as pd

def aggregate_daily_news(events, analyzer, fuzzy_trader, range_start=None, range_end=None, ticker=None):
    if not events:
        return []

    daily_groups = {}
    for event in events:
        date_str = event.get('event_date')
        if not date_str or date_str == "Unknown":
            continue
            
        try:
            event_date = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
            
        day_key = event_date.date()
        daily_groups.setdefault(day_key, []).append(event)

    daily_summaries = []
    
    if range_start and range_end:
        days_to_process = [d.date() for d in pd.date_range(start=range_start, end=range_end, freq="B")]
    else:
        days_to_process = sorted(daily_groups.keys())

    print("\n--- Daily News Summaries ---")
    for day in days_to_process:
        day_events = daily_groups.get(day, [])
        total_events = len(day_events)

        if total_events > 0:
            daily_news_content = "\n\n---\n\n".join(
                [f"Title: {e.get('event_title', '')}\n{e.get('event_content', '')}" for e in day_events]
            )

            daily_analysis = analyzer.analyze_daily_news(daily_news_content, ticker, day)
            sentiment_score = daily_analysis.get("sentiment_score", 0.0)
            conviction_score = daily_analysis.get("conviction_score", 0)
            materiality_score = daily_analysis.get("materiality_score", 0)
            persistence_score = daily_analysis.get("persistence_score", 0)

            trade_signal_strength = fuzzy_trader.get_signal(sentiment_score, conviction_score, materiality_score, persistence_score)

            # Asymmetric Thresholds
            if trade_signal_strength > 4.5:
                daily_prediction = 'rise'
                daily_advice = "BUY"
            elif trade_signal_strength < -6.5:
                daily_prediction = 'fall'
                daily_advice = "SELL"
            else:
                daily_prediction = 'neutral'
                daily_advice = "HOLD"

            reasoning = daily_analysis.get("reasoning", "")

            print(f"\n--- News Analysis for Date: {day} ---")
            print(f"Total News Items: {total_events}")
            print(f"LLM Sentiment Score: {sentiment_score}")
            print(f"LLM Conviction Score: {conviction_score}")
            print(f"LLM Materiality Score: {materiality_score}")
            print(f"LLM Persistence Score: {persistence_score}")
            print(f"Fuzzy Signal Strength: {trade_signal_strength:.2f}")
            print(f"Resulting Advice for Next Trading Day: {daily_advice}")
            print(f"Reasoning: {reasoning}")

        else:
            daily_prediction = 'neutral'
            daily_advice = "HOLD"
            reasoning = "No news for the day."
        
        execution_datetime = datetime.datetime.combine(day + datetime.timedelta(days=1), datetime.time(9, 30))
        
        summary_event = {
            'stock_code': ticker,
            'event_title': f"Daily Summary ({total_events} news items)",
            'event_date': execution_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'analysis_date': day,
            'prediction': daily_prediction,
            'reason': reasoning,
        }
        
        daily_summaries.append(summary_event)
        
    print("----------------------------\n")
    return daily_summaries

def normalize_trading_signals(events):
    if not events:
        return []

    ordered_events = sorted(
        events,
        key=lambda event: datetime.datetime.strptime(event['event_date'], '%Y-%m-%d %H:%M:%S'),
    )

    normalized_events = []
    last_prediction = None
    for event in ordered_events:
        prediction = event.get('prediction')
        if prediction == last_prediction:
            continue
        normalized_events.append(event)
        last_prediction = prediction

    return normalized_events
