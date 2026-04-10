import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from stock_selection_agent.config import Config

# Add News-based System to path
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../News-based System"))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from src.data.news_fetcher import NewsFetcher
from src.core.llm_analyzer import LLMAnalyzer

def get_analyzer():
    Config.load()
    api_key = Config.DEEPSEEK_API_KEY
    if not api_key:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
    return LLMAnalyzer(api_key)

def _fetch_52_week_gainers():
    url = "https://finance.yahoo.com/markets/stocks/52-week-gainers/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
        return symbols if symbols else ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN"]
    except Exception as e:
        print(f"Error fetching 52-week gainers: {e}")
        return ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "AMD", "PLTR", "SMCI", "COIN"]

def recommend_momentum_stocks_by_news(count=5, news_limit=3, days=3):
    """
    Fetch 52-week gainers and analyze their news to find momentum stocks.
    """
    fetcher = NewsFetcher()
    analyzer = get_analyzer()
    candidate_stocks = _fetch_52_week_gainers()
    
    recommended = []
    for stock in candidate_stocks:
        if len(recommended) >= count:
            break
            
        events = fetcher.fetch_recent_events(stock, limit=news_limit, days=days)
        stock_has_momentum = False
        
        for event in events:
            analysis = analyzer.analyze_event(event)
            if analysis.get("is_momentum_stock"):
                sentiment = analysis.get("sentiment", "Neutral")
                if sentiment in ["Strongly Positive", "Positive"]:
                    recommended.append({
                        "stock": stock,
                        "event_title": event.get("event_title"),
                        "analysis": analysis
                    })
                    stock_has_momentum = True
                    break
    
    return json.dumps(recommended, ensure_ascii=False)

def analyze_stock_events(stock_code, limit=5, days=3):
    """
    Fetch and analyze recent events for a specific stock.
    """
    fetcher = NewsFetcher()
    analyzer = get_analyzer()
    
    events = fetcher.fetch_recent_events(stock_code, limit=limit, days=days)
    if not events:
        return json.dumps({"message": f"No recent events found for {stock_code}."})
        
    all_analysis = []
    for event in events:
        analysis = analyzer.analyze_event(event)
        analysis["event_title"] = event.get("event_title")
        analysis["url"] = event.get("url")
        all_analysis.append(analysis)
        
    summary_report = analyzer.generate_summary_report(all_analysis, stock_code)
    
    return json.dumps({
        "stock": stock_code,
        "summary": summary_report,
        "events": all_analysis
    }, ensure_ascii=False)
