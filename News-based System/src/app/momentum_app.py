import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from src.data.news_fetcher import NewsFetcher
from src.core.llm_analyzer import LLMAnalyzer

class MomentumEventAnalyzerApp:
    def __init__(self, api_key):
        """
        Initialize the Momentum Event Analyzer App with necessary components.
        """
        self.fetcher = NewsFetcher()
        self.analyzer = LLMAnalyzer(api_key)

    def _fetch_52_week_gainers(self):
        """
        Fetch the list of 52-week gainers from Yahoo Finance.
        """
        url = "https://finance.yahoo.com/markets/stocks/52-week-gainers/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            symbols = []
            table = soup.find('table')
            if table:
                rows = table.find('tbody').find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if cols:
                        symbol = cols[0].text.strip()
                        if symbol:
                            symbols.append(symbol)
            return symbols if symbols else ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN"] # Fallback
        except Exception as e:
            print(f"Error fetching 52-week gainers: {e}")
            return ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "AMD", "PLTR", "SMCI", "COIN"]

    def recommend_momentum_stocks(self, count=5, news_limit=3, days=3):
        """
        Scan the '52 Week Gainers' list on Yahoo Finance, fetch their news, analyze them,
        and recommend up to `count` momentum stocks.
        """
        print("Fetching '52 Week Gainers' from Yahoo Finance...")
        candidate_stocks = self._fetch_52_week_gainers()
        
        print(f"Scanning market news for momentum opportunities (target: {count} stocks)...")
        recommended = []
        
        for stock in candidate_stocks:
            if len(recommended) >= count:
                break
                
            print(f"Checking news for {stock}...")
            events = self.fetcher.fetch_recent_events(stock, limit=news_limit, days=days)
            
            stock_has_momentum = False
            for event in events:
                analysis = self.analyzer.analyze_event(event)
                if analysis.get("is_momentum_stock"):
                    sentiment = analysis.get("sentiment", "Neutral")
                    if sentiment in ["Strongly Positive", "Positive"]:
                        recommended.append({
                            "stock": stock,
                            "event_title": event.get("event_title"),
                            "analysis": analysis
                        })
                        stock_has_momentum = True
                        print(f"  -> Found POSITIVE momentum signal for {stock}! (Sentiment: {sentiment})")
                        break
                        
            if not stock_has_momentum:
                print(f"  -> No strong POSITIVE momentum signal found for {stock}.")
                
        return recommended

    def handle_natural_language_query(self, query):
        """
        Main entry point for handling natural language queries.
        """
        parsed = self.analyzer.parse_user_query(query)
        intent = parsed.get("intent")
        params = parsed.get("parameters", {})
        
        if intent == "recommend_momentum":
            count = params.get("count", 5)
            limit = params.get("limit", 3)
            days = params.get("days", 3)
            print(f"\nAction: Recommending {count} momentum stocks based on the last {days} days of news.\n")
            recommendations = self.recommend_momentum_stocks(count=count, news_limit=limit, days=days)
            
            if not recommendations:
                print("Could not find any strong momentum stocks based on recent news from the scanned list.\n")
                return
                
            print("\n" + "="*50)
            print(f"🚀 TOP {len(recommendations)} MOMENTUM STOCK RECOMMENDATIONS 🚀")
            print("="*50)
            for i, rec in enumerate(recommendations, 1):
                analysis = rec['analysis']
                print(f"\n{i}. {rec['stock']} - Sentiment: {analysis.get('sentiment')}")
                print(f"   Event: {rec['event_title']}")
                print(f"   Impact: {analysis.get('impact_duration')}")
                reasoning = analysis.get('reasoning', {})
                print(f"   Summary: {reasoning.get('summary', 'N/A')}")
                drivers = reasoning.get('momentum_drivers', [])
                if drivers:
                    print(f"   Drivers: {', '.join(drivers)}")
            print("\n" + "="*50 + "\n")
            
        elif intent == "analyze_stock":
            stock_code = params.get("stock_code")
            count = params.get("count", 5)
            limit = params.get("limit", count)
            days = params.get("days", 3)
            if not stock_code:
                print("Could not identify the stock code from your query. Please specify one (e.g., 'Analyze AAPL' or 'How is Tesla doing?').\n")
                return
                
            print(f"\nAction: Analyzing up to {limit} events for {stock_code} from the last {days} days.\n")
            events = self.fetcher.fetch_recent_events(stock_code, limit=limit, days=days)
            if not events:
                print(f"No recent events found for {stock_code}.\n")
            else:
                all_analysis = []
                for i, event in enumerate(events, 1):
                    print(f"--- Event {i}: {event.get('event_title')} ---")
                    print(f"URL: {event.get('url', 'Unknown')}")
                    analysis = self.analyzer.analyze_event(event)
                    all_analysis.append(analysis)
                    
                    print(analysis.get('formatted_output', 'Formatting Error'))
                    print()

                print("\n--- Summary Report ---")
                summary_report = self.analyzer.generate_summary_report(all_analysis, stock_code)
                print(summary_report)
                print()
                
        elif intent in ["general_inquiry", "unknown"]:
            response = params.get("direct_response", "Sorry, I didn't understand your request. Try asking 'Recommend 5 momentum stocks', 'Analyze AAPL', or ask a general trading question.")
            print(f"\n🤖 Agent Response:\n{response}\n")
        else:
            print("Sorry, I didn't understand your request. Try asking 'Recommend 5 momentum stocks' or 'Analyze AAPL'.\n")
