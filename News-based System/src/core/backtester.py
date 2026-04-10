import pandas as pd
import numpy as np
import datetime
import os
from src.data.news_loader import _auto_detect_csv_path, _load_csv_frame, _resolve_ticker_columns, _resolve_text_columns

class Backtester:
    def __init__(
        self,
        initial_capital=100000.0,
        risk_free_rate=0.02,
    ):
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate

    def _extract_price_series(self, stock_data, price_col="Close"):
        if stock_data is None or stock_data.empty:
            return pd.Series(dtype=float)

        if isinstance(stock_data.columns, pd.MultiIndex):
            if price_col == "Close" and "Adj Close" in stock_data.columns.get_level_values(0):
                price_frame = stock_data.xs("Adj Close", axis=1, level=0)
            elif price_col in stock_data.columns.get_level_values(0):
                price_frame = stock_data.xs(price_col, axis=1, level=0)
            else:
                price_frame = stock_data.copy()
        else:
            if price_col == "Close" and "Adj Close" in stock_data.columns:
                price_frame = stock_data[["Adj Close"]]
            elif price_col in stock_data.columns:
                price_frame = stock_data[[price_col]]
            else:
                price_frame = stock_data.copy()

        if isinstance(price_frame, pd.Series):
            close_series = price_frame.astype(float)
        else:
            close_series = price_frame.iloc[:, 0].astype(float)

        close_series.name = price_col
        return close_series

    def calculate_metrics(self, portfolio_values, trades, price_data):
        if len(portfolio_values) < 2:
            return {}

        initial_value = self.initial_capital
        final_value = portfolio_values.iloc[-1]
        cum_returns_pct = (final_value - initial_value) / initial_value * 100
        cum_returns_decimal = cum_returns_pct / 100.0

        n_trading = len(portfolio_values)
        if n_trading == 0:
            n_trading = 1

        annualized_returns = ((1 + cum_returns_decimal) ** (252.0 / n_trading)) - 1

        daily_returns = portfolio_values.pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() != 0:
            daily_risk_free = self.risk_free_rate / 252
            sharpe_ratio = (daily_returns.mean() - daily_risk_free) / daily_returns.std()
            sharpe_ratio *= np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        rolling_max = portfolio_values.cummax()
        drawdown = (rolling_max - portfolio_values) / rolling_max
        max_drawdown = drawdown.max()

        if max_drawdown != 0:
            calmar_ratio = annualized_returns / max_drawdown
        else:
            calmar_ratio = np.nan

        winning_trades = 0
        total_closed_trades = 0
        for trade in trades:
            if trade['type'] == 'sell' and 'profit' in trade:
                total_closed_trades += 1
                if trade['profit'] > 0:
                    winning_trades += 1
        accuracy = (winning_trades / total_closed_trades * 100) if total_closed_trades > 0 else 0.0

        return {
            "Accuracy (%)": round(accuracy, 2),
            "Cumulative Returns (%)": round(cum_returns_pct, 2),
            "Annualized Returns (%)": round(annualized_returns * 100, 2),
            "Sharpe Ratio": round(sharpe_ratio, 4),
            "Maximum Drawdown (%)": round(max_drawdown * 100, 2),
            "Calmar Ratio": round(calmar_ratio, 4) if not np.isnan(calmar_ratio) else "N/A",
            "Initial Value": round(initial_value, 2),
            "Final Value": round(final_value, 2),
            "Total Trades": total_closed_trades
        }

    def _fetch_price_data(self, ticker, start_date, end_date):
        try:
            csv_file = _auto_detect_csv_path()
            df = _load_csv_frame(csv_file)
            ticker_col, _ = _resolve_ticker_columns(df)
            _, _, date_col, _ = _resolve_text_columns(df)
            
            if ticker_col:
                df = df[df[ticker_col].astype(str).str.upper() == ticker.upper()].copy()
                
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                df = df.dropna(subset=[date_col])
                df = df[(df[date_col] >= pd.to_datetime(start_date)) & (df[date_col] <= pd.to_datetime(end_date) + datetime.timedelta(days=1))]
                
                price_cols = {}
                for c in df.columns:
                    c_lower = c.lower()
                    if c_lower in ['open']:
                        price_cols['Open'] = c
                    elif c_lower in ['close', 'adjclose', 'adj close']:
                        price_cols['Close'] = c
                
                if 'Open' in price_cols and 'Close' in price_cols:
                    df['date_only'] = df[date_col].dt.date
                    df = df.sort_values(date_col)
                    daily_prices = df.groupby('date_only').last()
                    if daily_prices.empty:
                        return pd.Series(dtype=float), pd.Series(dtype=float)
                    
                    daily_prices.index = pd.to_datetime(daily_prices.index)
                    
                    open_series = daily_prices[price_cols['Open']].astype(float)
                    close_series = daily_prices[price_cols['Close']].astype(float)

                    full_index = pd.date_range(
                        start=pd.to_datetime(start_date).normalize(),
                        end=pd.to_datetime(end_date).normalize(),
                        freq="B",
                    )
                    open_series = open_series.reindex(full_index).ffill().bfill()
                    close_series = close_series.reindex(full_index).ffill().bfill()
                    open_series = open_series.dropna()
                    close_series = close_series.dropna()
                    
                    return open_series, close_series
                    
        except Exception as e:
            print(f"Error extracting prices from CSV: {e}")
            
        return pd.Series(dtype=float), pd.Series(dtype=float)

    def run_backtest(self, ticker, signals, period_label=None, start_date=None, end_date=None):
        if not signals:
            print("No signals provided for backtest.")
            return None

        signals = sorted(signals, key=lambda x: x['date'])
        
        backtest_start_date = start_date if start_date else signals[0]['date']
        final_date = end_date or min(datetime.datetime.now(), signals[-1]['date'] + datetime.timedelta(days=30))

        period_text = f" ({period_label})" if period_label else ""
        print(f"Fetching historical data for {ticker}{period_text} from {backtest_start_date.date()} to {final_date.date()} from local dataset...")
        
        open_prices, close_prices = self._fetch_price_data(ticker, backtest_start_date, final_date)

        if close_prices.empty or open_prices.empty:
            print("No price data found in local dataset for this period.")
            return None

        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []

        signal_idx = 0
        num_signals = len(signals)

        portfolio_dates = []
        portfolio_vals = []

        for date, current_close in close_prices.items():
            current_close = float(current_close)
            current_open = float(open_prices.loc[date])

            while signal_idx < num_signals and signals[signal_idx]['date'].date() <= date.date():
                signal = signals[signal_idx]
                prediction = signal['prediction']
                
                if prediction == 'rise' and position == 0:
                    shares_to_buy = int(capital // current_open)
                    if shares_to_buy > 0:
                        position = shares_to_buy
                        capital -= position * current_open
                        entry_price = current_open
                        trades.append({
                            'date': date,
                            'type': 'buy',
                            'price': current_open,
                            'shares': position,
                            'reason': signal.get('reason', 'rise_signal')
                        })
                        print(
                            f"[{date.date()}] BUY  {position} shares at {current_open:.2f} (OPEN) | "
                            f"Reason: {signal.get('reason', 'rise_signal')}"
                        )
                
                elif prediction == 'fall' and position > 0:
                    profit = (current_open - entry_price) * position
                    capital += position * current_open
                    print(
                        f"[{date.date()}] SELL {position} shares at {current_open:.2f} (OPEN) | "
                        f"Profit: {profit:.2f} | Reason: next_sell_signal"
                    )
                    trades.append({
                        'date': date,
                        'type': 'sell',
                        'price': current_open,
                        'shares': position,
                        'profit': profit,
                        'reason': 'next_sell_signal'
                    })
                    position = 0
                    entry_price = 0
                    
                signal_idx += 1

            portfolio_dates.append(date)
            portfolio_vals.append(capital + (position * current_close))

        portfolio_values = pd.Series(portfolio_vals, index=portfolio_dates, dtype=float)

        if position > 0:
            last_date = close_prices.index[-1]
            last_price = float(close_prices.iloc[-1])
            profit = (last_price - entry_price) * position
            capital += position * last_price
            print(f"[{last_date.date()}] CLOSE {position} shares at {last_price:.2f} | Profit: {profit:.2f} | Reason: period_end")
            trades.append({
                'date': last_date,
                'type': 'sell',
                'price': last_price,
                'shares': position,
                'profit': profit,
                'reason': 'period_end'
            })
            position = 0
            portfolio_values.loc[last_date] = capital

        portfolio_values.ffill(inplace=True)

        metrics = self.calculate_metrics(portfolio_values, trades, close_prices)
        return metrics
