import json
import re
from openai import OpenAI
from src.utils.config import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

class LLMAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL,
        )
        self.model = DEEPSEEK_MODEL

    def analyze_event(self, event_data):
        try:
            prompt = f"""
            Please analyze the following stock market event/news for Momentum Trading opportunities.
            
            Stock: {event_data.get('stock_name', 'Unknown')} ({event_data.get('stock_code', 'Unknown')})
            Event Date: {event_data.get('event_date', 'Unknown')}
            Event Content:
            {event_data.get('event_content', '')}

            **Detailed Analysis Instructions:**
            
            Analyze the event based on its category. Here are specific focus areas for common event types:
            
            1.  **Policy Support / Regulatory Changes**:
                *   Focus: Does this policy directly benefit the company's core business? Is it a long-term structural change or a short-term subsidy?
                *   Momentum Driver: Industry-wide re-rating potential.
            
            2.  **Corporate Mergers & Acquisitions (M&A)**:
                *   Focus: Synergy potential, acquisition price (premium/discount), and market reaction. Is it accretive to earnings?
                *   Momentum Driver: Arbitrage opportunities or growth acceleration.
            
            3.  **Product Launches / Technology Breakthroughs**:
                *   Focus: Market size of the new product, competitive advantage, and revenue contribution timeline.
                *   Momentum Driver: Innovation-led growth repricing.
            
            4.  **Earnings / Financial Guidance**:
                *   Focus: Beat/Miss magnitude, forward guidance updates, and operational efficiency.
                *   Momentum Driver: Earnings surprise.
            
            5.  **Contracts / Orders**:
                *   Focus: Contract value relative to annual revenue, client quality, and recurring nature.
                *   Momentum Driver: Revenue visibility.

            **Output Requirements:**
            
            Based on the analysis, provide a structured JSON response with the following fields:
            
            1.  event_type: Classify the event (e.g., Policy Support, M&A, Product Launch, Earnings, Contract Win, etc.).
            2.  sentiment: "Strongly Positive", "Positive", "Neutral", "Negative", or "Strongly Negative".
            3.  sentiment_score: A float from -1.0 (very negative) to 1.0 (very positive).
            4.  materiality_score: An integer from 1 (immaterial/noise) to 10 (highly material/fundamental change).
            5.  impact_duration: Estimated duration of impact (e.g., "Short-term (<1 week)", "Medium-term (1-4 weeks)", "Long-term (>1 month)").
            6.  persistence_score: An integer from 1 (fleeting/short-term) to 10 (long-lasting/structural).
            7.  price_trend: "Upward", "Downward", or "Flat".
            8.  trend_strength: An integer from 1 (weak) to 10 (strong).
            9.  is_momentum_stock: boolean (true/false). Set to true ONLY if this event is likely to drive significant POSITIVE price momentum.
            10. formatted_output: A formatted string strictly following this layout:
                Event type: <event_type>
                Publish time: {event_data.get('event_date', 'Unknown')}
                Sentiment: <sentiment> (score: <sentiment_score>)
                Materiality score: <materiality_score>
                Impact duration: <impact_duration> (score: <persistence_score>)
                Price trend: <price_trend> (strength: <trend_strength>)
            11. reasoning: A structured object with these fields:
                - summary: 1 short sentence
                - momentum_drivers: list of specific drivers or empty list

            Return strictly valid JSON.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert financial analyst specializing in momentum trading."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )

            analysis_text = response.choices[0].message.content
            
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {
                    "event_type": "Unknown",
                    "sentiment": "Neutral",
                    "sentiment_score": 0.0,
                    "materiality_score": 1,
                    "impact_duration": "Unknown",
                    "persistence_score": 1,
                    "price_trend": "Flat",
                    "trend_strength": 1,
                    "is_momentum_stock": False,
                    "formatted_output": "Failed to parse API response.",
                    "reasoning": {
                        "summary": "Failed to parse API response.",
                        "momentum_drivers": []
                    }
                }
            
            return analysis

        except Exception as e:
            print(f"DeepSeek Analysis Failed: {e}")
            return {
                "event_type": "Error",
                "sentiment": "Neutral",
                "sentiment_score": 0.0,
                "materiality_score": 1,
                "impact_duration": "Unknown",
                "persistence_score": 1,
                "price_trend": "Flat",
                "trend_strength": 1,
                "is_momentum_stock": False,
                "formatted_output": f"DeepSeek analysis failed: {str(e)}",
                "reasoning": {
                    "summary": "DeepSeek analysis failed.",
                    "momentum_drivers": []
                }
            }

    def analyze_daily_news(self, daily_news_content, stock_code, event_date):
        try:
            prompt = f"""
            As a senior financial analyst, your task is to analyze all the news for a specific stock collected at the end of the trading day and provide a single, clear trading signal for the next trading day (BUY, SELL, or HOLD).

            **Stock:** {stock_code}
            **Date of News:** {event_date}

            **Collected News Content for the Day:**
            --- START OF NEWS ---
            {daily_news_content}
            --- END OF NEWS ---

            **Instructions:**
            1.  **Synthesize:** Read and synthesize all the provided news articles.
            2.  **Analyze Overall Sentiment:** Determine the dominant sentiment (Positive, Negative, or Neutral) across all news items.
            3.  **Evaluate Materiality:** Assess how material or significant the news is to the company's core business and financials (1-10).
            4.  **Evaluate Persistence:** Assess how long-lasting the impact of this news is likely to be (1-10).
            5.  **Generate a Signal:** Based on your analysis, provide a single, direct trading signal: `BUY`, `SELL`, or `HOLD`.
            6.  **Provide Reasoning:** Briefly explain your reasoning in 1-2 sentences.

            **Output Format:**
            Return your analysis in a pure JSON object with the following keys:
            - `sentiment_score`: A float from -1.0 (very negative) to 1.0 (very positive).
            - `daily_advice`: Your final trading signal ('BUY', 'SELL', 'HOLD').
            - `conviction_score`: An integer from 1 (low conviction) to 10 (high conviction).
            - `materiality_score`: An integer from 1 (immaterial/noise) to 10 (highly material/fundamental change).
            - `persistence_score`: An integer from 1 (fleeting/short-term) to 10 (long-lasting/structural).
            - `reasoning`: Your brief explanation.

            **Example JSON Output:**
            ```json
            {{
                "sentiment_score": 0.8,
                "daily_advice": "BUY",
                "conviction_score": 8,
                "materiality_score": 7,
                "persistence_score": 6,
                "reasoning": "Multiple reports of strong earnings and a new product launch indicate strong upward potential for the next trading day."
            }}
            ```

            Provide only the raw JSON object as your response.
            """

            response = self.client.chat.completions.create(
                model="deepseek-coder",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
                stream=False
            )

            response_text = response.choices[0].message.content
            json_match = re.search(r'```json\n({.*?})\n```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text

            return json.loads(json_str)

        except json.JSONDecodeError:
            print(f"DeepSeek Daily Analysis Failed: Could not decode JSON from response: {response_text}")
            return {"sentiment_score": 0.0, "daily_advice": "HOLD", "conviction_score": 0, "materiality_score": 0, "persistence_score": 0, "reasoning": "JSON decode error"}
        except Exception as e:
            print(f"An unexpected error occurred during DeepSeek daily analysis: {e}")
            return {"sentiment_score": 0.0, "daily_advice": "HOLD", "conviction_score": 0, "materiality_score": 0, "persistence_score": 0, "reasoning": "Unexpected error"}

    def generate_summary_report(self, events_analysis, stock_code):
        try:
            prompt = f"""
            You are a senior financial analyst. Based on the following analysis of recent events for {stock_code}, generate a concise summary report.

            Events Analysis Data:
            {json.dumps(events_analysis, indent=2, ensure_ascii=False)}

            Please output a string containing the formatted summary report. You MUST follow this exact structure, do NOT return JSON:
            
            Sentiment: <overall sentiment> (score: <score>)
            Momentum detected: <yes/no>
            Momentum drivers: <drivers or 'none'>
            Trading advice: <buy/hold/sell> (conviction score: <score>)
            Reason: <brief explanation>
            Risks: <list of risks or 'None'>
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant generating summary reports."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"Failed to generate summary report: {e}")
            return "Failed to generate summary report."

    def _coerce_positive_int(self, value, default):
        if value in (None, ""):
            return default
        try:
            normalized_value = int(value)
        except (TypeError, ValueError):
            return default
        if normalized_value <= 0:
            return default
        return normalized_value

    def _extract_stock_code_from_query(self, query):
        ticker_match = re.search(r'\b[A-Z]{1,5}(?:\.[A-Z]{1,3})?\b', query.upper())
        if ticker_match:
            return ticker_match.group(0)
        return ""

    def _normalize_query_result(self, query, parsed_result):
        parsed = parsed_result if isinstance(parsed_result, dict) else {}
        parameters = parsed.get("parameters", {}) if isinstance(parsed.get("parameters"), dict) else {}
        normalized_intent = parsed.get("intent", "unknown")

        extracted_count = re.search(r'\b(?:top|recommend|analyze|show|fetch|get)?\s*(\d+)\s+(?:stocks?|events?|news|articles?)\b', query, re.IGNORECASE)
        extracted_limit = re.search(r'\b(?:limit|show|fetch|get)\s*(?:to\s*)?(\d+)\b', query, re.IGNORECASE)
        extracted_days = re.search(r'\b(?:last|past|within)\s*(\d+)\s+days?\b', query, re.IGNORECASE)

        count_value = parameters.get("count")
        limit_value = parameters.get("limit")
        days_value = parameters.get("days")

        if extracted_count:
            count_value = extracted_count.group(1)
        if extracted_limit:
            limit_value = extracted_limit.group(1)
        if extracted_days:
            days_value = extracted_days.group(1)

        normalized_count = self._coerce_positive_int(count_value, 5)
        normalized_limit = self._coerce_positive_int(limit_value, normalized_count)
        normalized_days = self._coerce_positive_int(days_value, 3)

        stock_code = parameters.get("stock_code")
        if stock_code:
            stock_code = str(stock_code).strip().upper()
        if not stock_code:
            stock_code = self._extract_stock_code_from_query(query)

        return {
            "intent": normalized_intent,
            "parameters": {
                "count": normalized_count,
                "limit": normalized_limit,
                "days": normalized_days,
                "stock_code": stock_code,
                "direct_response": parameters.get("direct_response", "")
            }
        }

    def parse_user_query(self, query):
        try:
            prompt = f"""
            You are an intelligent financial AI agent. Your task is to understand the user's query and decide the best workflow to assist them.

            User Query: "{query}"

            Available workflows (intents):
            1. "recommend_momentum": The user is asking for momentum stock recommendations or top gainers.
            2. "analyze_stock": The user wants to analyze recent news, events, or momentum for a specific stock or company.
            3. "general_inquiry": The user is asking a general question, seeking advice on trading strategies, explaining concepts, or any query that does not require fetching live news.

            Extract the intent and any relevant parameters.
            Return a strictly valid JSON object with the following structure:
            {{
                "intent": "recommend_momentum" | "analyze_stock" | "general_inquiry" | "unknown",
                "parameters": {{
                    "count": int (default 5, extract if user specifies a number of stocks or events/news),
                    "limit": int (default to count for news/event fetch size),
                    "days": int (default 3, extract if user specifies a time window such as 'last 7 days'),
                    "stock_code": str (extract the stock ticker symbol, e.g., 'AAPL', 'NVDA', if intent is analyze_stock. If user gives company name, infer the ticker.),
                    "direct_response": str (if intent is general_inquiry or unknown, provide a helpful, professional, and detailed response to the user's query here. Otherwise, leave empty.)
                }}
            }}
            Return strictly valid JSON.
            """
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert financial AI agent. You route user queries to the correct tool or answer them directly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            analysis_text = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                return self._normalize_query_result(query, json.loads(json_match.group()))
            return self._normalize_query_result(query, {"intent": "unknown", "parameters": {}})
        except Exception as e:
            print(f"Failed to parse query: {e}")
            return self._normalize_query_result(query, {"intent": "unknown", "parameters": {}})
