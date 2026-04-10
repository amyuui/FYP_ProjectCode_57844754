import pandas as pd
from stock_selection_agent.strategy.rules import FUZZY_RULES, MACD_MF, RSI_MF, SO_MF


def _triangular_membership(x, left_foot, peak, right_foot):
    if pd.isna(x):
        return 0.0
    x = float(x)
    if x <= left_foot or x >= right_foot:
        if peak == left_foot and x == peak:
            return 1.0
        if peak == right_foot and x == peak:
            return 1.0
        return 0.0
    if x == peak:
        return 1.0
    if x < peak:
        return (x - left_foot) / (peak - left_foot) if peak != left_foot else 1.0
    return (right_foot - x) / (right_foot - peak) if right_foot != peak else 1.0


def normalize_series_to_100(series):
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.Series([50.0] * len(numeric), index=numeric.index)
    min_val = valid.min()
    max_val = valid.max()
    if max_val == min_val:
        return pd.Series([50.0] * len(numeric), index=numeric.index)
    normalized = (numeric - min_val) / (max_val - min_val) * 100.0
    return normalized.clip(lower=0, upper=100)


def fuzzify_value(value, mf_definition):
    memberships = {}
    for label, (left_foot, peak, right_foot) in mf_definition.items():
        memberships[label] = _triangular_membership(value, left_foot, peak, right_foot)
    best_label = max(memberships, key=memberships.get)
    return best_label, memberships


def fuzzify_condition(macd_norm, rsi_norm, so_norm):
    macd_label, macd_memberships = fuzzify_value(macd_norm, MACD_MF)
    rsi_label, rsi_memberships = fuzzify_value(rsi_norm, RSI_MF)
    so_label, so_memberships = fuzzify_value(so_norm, SO_MF)
    condition = {
        "macd": macd_label,
        "rsi": rsi_label,
        "so": so_label
    }
    memberships = {
        "macd": macd_memberships,
        "rsi": rsi_memberships,
        "so": so_memberships
    }
    return condition, memberships


def action_from_condition(condition):
    for rule in FUZZY_RULES:
        if rule["if"] == condition:
            return rule["then"]
    return "Hold"


def signal_from_row(row):
    condition, _ = fuzzify_condition(
        row["macd_norm"],
        row["rsi_norm"],
        row["so_norm"]
    )
    action = action_from_condition(condition)
    if action == "Buy":
        return 1
    if action == "Sell":
        return -1
    return 0
