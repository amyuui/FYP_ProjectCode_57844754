import json
from datetime import datetime, timedelta
from stock_selection_agent.backtest.engine import BacktestEngine


def run_fuzzy_backtest(
    ticker,
    start_date=None,
    end_date=None,
    initial_capital=100000,
    commission=0.0003,
    rsi_period=14
):
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    engine = BacktestEngine(initial_capital=initial_capital, commission=commission)
    strategy_config = {
        "type": "fuzzy",
        "rsi_period": int(rsi_period)
    }
    result = engine.run(ticker, start_date, end_date, strategy_config)
    return json.dumps(result, ensure_ascii=False, indent=2)
