import json
from stock_selection_agent.services.screener import rank_momentum_stocks
from stock_selection_agent.services.signal import evaluate_buy_signal


def _safe_load_json(raw_text):
    if isinstance(raw_text, dict):
        return raw_text
    try:
        return json.loads(raw_text)
    except Exception:
        return None


def _candidate_sort_key(item):
    signal_strength = item.get("signal_strength")
    signal_strength = signal_strength if isinstance(signal_strength, (int, float)) else -1
    return (
        -int(item.get("momentum_score", 0)),
        -int(item.get("absolute_score", 0)),
        -float(signal_strength)
    )


def generate_momentum_report(tickers=None, period="3mo", top_n=10, eval_top_k=3):
    target_count = max(0, int(top_n))
    screening_count = max(target_count * 3, target_count, 30)
    screened_raw = rank_momentum_stocks(tickers=tickers, period=period, top_n=screening_count)
    screened = _safe_load_json(screened_raw)
    if not isinstance(screened, list) or len(screened) == 0:
        return json.dumps({
            "period": period,
            "top_n": top_n,
            "candidates": [],
            "report_markdown": "## Momentum Stocks Screening Report\n\nNo valid momentum candidates were found in this run."
        }, ensure_ascii=False)

    eval_count = len(screened)
    for idx in range(eval_count):
        ticker = screened[idx].get("ticker")
        signal_raw = evaluate_buy_signal(ticker=ticker, period=period)
        signal = _safe_load_json(signal_raw)
        if isinstance(signal, dict):
            screened[idx]["fuzzy_recommendation"] = signal.get("recommendation")
            screened[idx]["signal_strength"] = signal.get("momentum_strength")
        else:
            screened[idx]["fuzzy_recommendation"] = "N/A"
            screened[idx]["signal_strength"] = None

    buy_candidates = [
        item for item in screened
        if str(item.get("fuzzy_recommendation", "")).strip().lower() == "buy"
    ]
    buy_candidates = sorted(buy_candidates, key=_candidate_sort_key)
    screened = buy_candidates[:target_count]
    buy_count = len(screened)

    lines = []
    lines.append("## Momentum Stocks Screening Report")
    lines.append("")
    lines.append(f"**Timeframe**: {period}")
    lines.append(f"**Candidates Returned**: {len(screened)}")
    lines.append(f"**Buy Candidates**: {buy_count}")
    lines.append("")
    lines.append("| Rank | Symbol | Name | Relative Momentum | Absolute Score | Fuzzy Recommendation | Key Reasons |")
    lines.append("|------|--------|------|-------------------|----------------|----------------------|-------------|")
    for i, item in enumerate(screened, start=1):
        rel_score = item.get("momentum_score", 0)
        abs_score = item.get("absolute_score", 0)
        rec = item.get("fuzzy_recommendation", "Not Evaluated")
        reasons = item.get("reasons", "")
        symbol = item.get("ticker", "")
        name = item.get("name", "")
        lines.append(f"| {i} | {symbol} | {name} | {rel_score}/100 | {abs_score}/100 | {rec} | {reasons} |")
    lines.append("")
    lines.append("### Notes")
    lines.append("- Output is strictly Buy-only and sorted by momentum score, absolute score, then signal strength.")
    lines.append("- Relative Momentum is normalized within current screening universe.")
    lines.append("- Absolute Score reflects raw rule-based scoring before normalization.")
    lines.append(f"- Fuzzy recommendations are evaluated for all {eval_count} screened symbols in this run.")
    if buy_count == 0:
        lines.append("- No Buy candidates met fuzzy rules in this run.")
    report_markdown = "\n".join(lines)

    return json.dumps({
        "period": period,
        "top_n": top_n,
        "candidates": screened,
        "report_markdown": report_markdown
    }, ensure_ascii=False)
