TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current local system date and time for time-sensitive requests.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_info",
            "description": "Get basic information about a stock (name, sector, market cap, PE, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL)."}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_data",
            "description": "Get historical daily price and volume data for a stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "period": {"type": "string", "description": "Period like '1mo', '3mo', '6mo', '1y'", "default": "6mo"},
                    "interval": {"type": "string", "description": "Data interval: 1d, 1wk, 1mo", "default": "1d"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_technical_indicators",
            "description": "Calculate technical indicators (RSI, MACD, SO) for a stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "period": {"type": "string", "default": "6mo"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_momentum_stocks",
            "description": "Find stocks with strong momentum based on RSI, MACD, and price trends. Uses fuzzy logic to assign a momentum score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {"type": "array", "items": {"type": "string"}, "description": "List of tickers to screen (optional)."},
                    "period": {"type": "string", "default": "3mo"},
                    "top_n": {"type": "integer", "default": 10}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_momentum_report",
            "description": "Generate a unified momentum screening report with relative momentum, absolute score, and fuzzy recommendation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {"type": "array", "items": {"type": "string"}, "description": "Optional list of tickers to screen."},
                    "period": {"type": "string", "default": "3mo"},
                    "top_n": {"type": "integer", "default": 10},
                    "eval_top_k": {"type": "integer", "default": 3}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_buy_signal",
            "description": "Evaluate whether a stock is Buy/Hold/Sell now using the predefined fuzzy momentum strategy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "period": {"type": "string", "default": "6mo"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_backtest",
            "description": "Run backtest using the predefined fuzzy logic strategy based on MACD, RSI and SO rules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "start_date": {"type": "string", "description": "Start date in YYYYMMDD or YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "End date in YYYYMMDD or YYYY-MM-DD"},
                    "initial_capital": {"type": "number", "default": 100000},
                    "commission": {"type": "number", "default": 0.0003},
                    "rsi_period": {"type": "integer", "default": 14}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_investment_report",
            "description": "Generate structured investment recommendation report including fuzzy recommendation and 1-year backtest metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "signal_period": {"type": "string", "default": "6mo"},
                    "start_date": {"type": "string", "description": "Optional start date in YYYYMMDD or YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "Optional end date in YYYYMMDD or YYYY-MM-DD"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_momentum_stocks_by_news",
            "description": "Recommend momentum stocks by analyzing the latest news of 52-week gainers. Returns stocks with strong positive momentum events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of stocks to recommend", "default": 5},
                    "news_limit": {"type": "integer", "description": "Number of news articles to check per stock", "default": 3},
                    "days": {"type": "integer", "description": "Number of past days to fetch news for", "default": 3}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_stock_events",
            "description": "Fetch and analyze recent news events for a specific stock to find momentum drivers and sentiment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string", "description": "Stock ticker symbol"},
                    "limit": {"type": "integer", "description": "Number of events to analyze", "default": 5},
                    "days": {"type": "integer", "description": "Number of past days to fetch news for", "default": 3}
                },
                "required": ["stock_code"]
            }
        }
    }
]
