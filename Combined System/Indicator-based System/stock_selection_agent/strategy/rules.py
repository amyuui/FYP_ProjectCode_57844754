MACD_MF = {
    "Low": (0, 33, 50),
    "Medium": (33, 50, 66),
    "High": (50, 66, 100)
}

RSI_MF = {
    "Low": (0, 20, 40),
    "Medium": (30, 50, 70),
    "High": (60, 80, 100)
}

SO_MF = {
    "Low": (0, 33, 50),
    "Medium": (33, 50, 66),
    "High": (50, 66, 100)
}

FUZZY_RULES = [
    {"if": {"macd": "High", "rsi": "Medium", "so": "High"}, "then": "Buy"},
    {"if": {"macd": "High", "rsi": "Low", "so": "High"}, "then": "Buy"},
    {"if": {"macd": "Medium", "rsi": "Low", "so": "High"}, "then": "Buy"},
    {"if": {"macd": "High", "rsi": "High", "so": "High"}, "then": "Hold"},
    {"if": {"macd": "Medium", "rsi": "Medium", "so": "Medium"}, "then": "Hold"},
    {"if": {"macd": "Low", "rsi": "Low", "so": "Low"}, "then": "Hold"},
    {"if": {"macd": "Low", "rsi": "High", "so": "Low"}, "then": "Sell"},
    {"if": {"macd": "Low", "rsi": "Medium", "so": "Low"}, "then": "Sell"},
    {"if": {"macd": "Medium", "rsi": "High", "so": "Low"}, "then": "Sell"}
]
