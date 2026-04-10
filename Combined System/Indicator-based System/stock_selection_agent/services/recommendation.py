import json
from stock_selection_agent.llm.deepseek import DeepSeekClient


def _fallback_recommendation(action, condition):
    mapping = {
        "Buy": 80,
        "Hold": 55,
        "Sell": 25
    }
    strength = mapping.get(action, 50)
    return {
        "recommendation": action,
        "momentum_strength": strength,
        "reasoning": f"Fuzzy condition={condition} matched rule result={action}."
    }


def llm_defuzzify_recommendation(ticker, condition, action, indicators, timeframe="6mo"):
    client = DeepSeekClient()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict defuzzification engine. "
                "Output ONLY valid JSON with exactly these keys: "
                "recommendation(string), momentum_strength(int 0-100), reasoning(string)."
            )
        },
        {
            "role": "user",
            "content": (
                f"Ticker={ticker}, timeframe={timeframe}, fuzzy_condition={condition}, "
                f"rule_action={action}, indicators={indicators}. "
                "Convert this to the final JSON output."
            )
        }
    ]
    try:
        response = client.chat(messages, stream=False)
        content = response.content if hasattr(response, "content") else str(response)
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return _fallback_recommendation(action, condition)
        required = {"recommendation", "momentum_strength", "reasoning"}
        if not required.issubset(set(parsed.keys())):
            return _fallback_recommendation(action, condition)
        parsed["momentum_strength"] = int(max(0, min(100, int(parsed["momentum_strength"]))))
        parsed["recommendation"] = str(parsed["recommendation"])
        parsed["reasoning"] = str(parsed["reasoning"])
        return parsed
    except Exception:
        return _fallback_recommendation(action, condition)
