import pandas as pd
from stock_selection_agent.data.market import fetch_backtest_data
from stock_selection_agent.indicators.calculation import calculate_macd, calculate_rsi, calculate_so
from stock_selection_agent.strategy.fuzzy import normalize_series_to_100, signal_from_row


class BacktestEngine:
    def __init__(self, initial_capital=100000, commission=0.0003):
        self.initial_capital = initial_capital
        self.commission = commission
        self.cash = initial_capital
        self.position = 0
        self.history = []
        self.portfolio_values = []

    def _fetch_data(self, ticker, start_date, end_date):
        return fetch_backtest_data(ticker, start_date, end_date, warmup_days=60)

    def _calculate_indicators(self, df, strategy_config):
        indicator_df = pd.DataFrame({
            "Close": pd.to_numeric(df["close"], errors="coerce"),
            "High": pd.to_numeric(df["high"], errors="coerce"),
            "Low": pd.to_numeric(df["low"], errors="coerce")
        })
        rsi_period = int(strategy_config.get("rsi_period", 14))
        indicator_df = calculate_macd(indicator_df)
        indicator_df = calculate_rsi(indicator_df, period=rsi_period)
        indicator_df = calculate_so(indicator_df, k_period=14, d_period=3)
        df["macd"] = indicator_df["MACD"]
        df["rsi"] = indicator_df["RSI"]
        df["so"] = indicator_df["SO_K"]
        df["macd_norm"] = normalize_series_to_100(df["macd"])
        df["rsi_norm"] = pd.to_numeric(df["rsi"], errors="coerce").clip(lower=0, upper=100)
        df["so_norm"] = pd.to_numeric(df["so"], errors="coerce").clip(lower=0, upper=100)
        return df

    def _generate_signal(self, row, prev_row, strategy_config):
        if prev_row is None:
            return 0
        return signal_from_row(row)

    def _calculate_trade_win_rate(self):
        open_shares = 0
        open_cost_total = 0.0
        closed_trade_pnls = []
        for trade in self.history:
            action = trade.get("action")
            shares = int(trade.get("shares", 0))
            price = float(trade.get("price", 0.0))
            commission = float(trade.get("commission", 0.0))
            if shares <= 0:
                continue
            if action == "BUY":
                open_shares += shares
                open_cost_total += (shares * price) + commission
            elif action == "SELL" and open_shares > 0:
                sell_shares = min(shares, open_shares)
                if sell_shares <= 0:
                    continue
                revenue = (sell_shares * price) - commission
                allocated_cost = open_cost_total * (sell_shares / open_shares)
                pnl = revenue - allocated_cost
                closed_trade_pnls.append(pnl)
                open_cost_total -= allocated_cost
                open_shares -= sell_shares
                if open_shares == 0:
                    open_cost_total = 0.0
        closed_trades = len(closed_trade_pnls)
        if closed_trades == 0:
            return 0.0, 0, 0
        win_trades = sum(1 for pnl in closed_trade_pnls if pnl > 0)
        win_rate = win_trades / closed_trades
        return float(win_rate), int(win_trades), int(closed_trades)

    def run(self, ticker, start_date, end_date, strategy_config):
        df = self._fetch_data(ticker, start_date, end_date)
        df = self._calculate_indicators(df, strategy_config)
        mask = df["trade_date"] >= start_date
        if not mask.any():
            return {"error": "No data in requested date range"}
        start_idx = mask.idxmax()
        if start_idx > 0:
            start_idx -= 1
        prev_row = None
        for _, row in df.iloc[start_idx:].iterrows():
            is_trading_period = row["trade_date"] >= start_date
            current_price = row["close"]
            if is_trading_period:
                total_value = self.cash + (self.position * current_price)
                self.portfolio_values.append({
                    "trade_date": row["trade_date"],
                    "value": total_value
                })
            signal = self._generate_signal(row, prev_row, strategy_config)
            if is_trading_period and signal != 0:
                if signal == 1 and self.cash > 0:
                    max_shares = int(self.cash / (current_price * (1 + self.commission)) / 100) * 100
                    if max_shares > 0:
                        cost = max_shares * current_price
                        comm = cost * self.commission
                        self.cash -= (cost + comm)
                        self.position += max_shares
                        self.history.append({
                            "date": row["trade_date"],
                            "action": "BUY",
                            "price": current_price,
                            "shares": max_shares,
                            "commission": comm
                        })
                elif signal == -1 and self.position > 0:
                    revenue = self.position * current_price
                    comm = revenue * self.commission
                    self.cash += (revenue - comm)
                    self.history.append({
                        "date": row["trade_date"],
                        "action": "SELL",
                        "price": current_price,
                        "shares": self.position,
                        "commission": comm
                    })
                    self.position = 0
            prev_row = row
        final_value = self.cash + (self.position * df.iloc[-1]["close"])
        total_return = (final_value - self.initial_capital) / self.initial_capital if self.initial_capital else 0
        pv_df = pd.DataFrame(self.portfolio_values)
        trade_win_rate, win_trades, closed_trades = self._calculate_trade_win_rate()
        if not pv_df.empty:
            pv_df["cummax"] = pv_df["value"].cummax()
            pv_df["drawdown"] = (pv_df["cummax"] - pv_df["value"]) / pv_df["cummax"]
            max_drawdown = pv_df["drawdown"].max()
            pv_df["returns"] = pv_df["value"].pct_change().fillna(0.0)
            annual_volatility = float(pv_df["returns"].std() * (252 ** 0.5))
            mean_ret = float(pv_df["returns"].mean())
            std_ret = float(pv_df["returns"].std())
            sharpe_ratio = (mean_ret / std_ret) * (252 ** 0.5) if std_ret > 0 else 0.0
            annualized_return = (final_value / self.initial_capital) ** (252 / len(pv_df)) - 1 if len(pv_df) > 0 and self.initial_capital > 0 else 0.0
        else:
            max_drawdown = 0
            annualized_return = 0.0
            annual_volatility = 0.0
            sharpe_ratio = 0.0
        return {
            "ticker": ticker,
            "strategy": strategy_config.get("type", "fuzzy"),
            "initial_capital": self.initial_capital,
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return * 100, 2),
            "max_drawdown_pct": round(max_drawdown * 100, 2),
            "annualized_return": round(annualized_return, 6),
            "annualized_volatility": round(annual_volatility, 6),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "win_rate_trade": round(trade_win_rate, 6),
            "win_trades": win_trades,
            "closed_trades": closed_trades,
            "trades_count": len(self.history),
            "trades": self.history[-5:]
        }
