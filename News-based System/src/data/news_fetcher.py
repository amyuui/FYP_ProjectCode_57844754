import yfinance as yf
import datetime
import os
from email.utils import parsedate_to_datetime

class NewsFetcher:
    def _coerce_positive_int(self, value, default=None):
        if value in (None, ""):
            return default
        try:
            coerced = int(value)
        except (TypeError, ValueError):
            return default
        if coerced <= 0:
            return default
        return coerced

    def _normalize_news_items(self, news_payload):
        if isinstance(news_payload, list):
            return news_payload
        if isinstance(news_payload, dict):
            nested_news = news_payload.get('news')
            if isinstance(nested_news, list):
                return nested_news
        return []

    def _normalize_datetime(self, value):
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return value

    def _parse_datetime_value(self, raw_value):
        if raw_value in (None, ""):
            return None

        try:
            if isinstance(raw_value, datetime.datetime):
                return self._normalize_datetime(raw_value)

            if isinstance(raw_value, datetime.date):
                return datetime.datetime.combine(raw_value, datetime.time.min)

            if isinstance(raw_value, (int, float)):
                timestamp = raw_value / 1000 if raw_value > 253402300799 else raw_value
                return datetime.datetime.utcfromtimestamp(timestamp)

            if isinstance(raw_value, str):
                stripped_value = raw_value.strip()
                if not stripped_value:
                    return None

                if stripped_value.isdigit():
                    timestamp = int(stripped_value)
                    if timestamp > 253402300799:
                        timestamp = timestamp / 1000
                    return datetime.datetime.utcfromtimestamp(timestamp)

                iso_value = stripped_value.replace("Z", "+00:00")
                try:
                    return self._normalize_datetime(datetime.datetime.fromisoformat(iso_value))
                except ValueError:
                    pass

                try:
                    return self._normalize_datetime(parsedate_to_datetime(stripped_value))
                except (TypeError, ValueError, IndexError, OverflowError):
                    pass

                for date_format in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                    try:
                        return datetime.datetime.strptime(stripped_value, date_format)
                    except ValueError:
                        pass
        except Exception:
            return None

        return None

    def _extract_event_datetime(self, item):
        if not isinstance(item, dict):
            return None

        content = item.get('content') if isinstance(item.get('content'), dict) else {}
        publish_candidates = [
            item.get('providerPublishTime'),
            item.get('publishTime'),
            item.get('pubDate'),
            item.get('publishedAt'),
            item.get('date'),
            content.get('providerPublishTime'),
            content.get('publishTime'),
            content.get('pubDate'),
            content.get('publishedAt'),
            content.get('date'),
            content.get('displayTime')
        ]

        for candidate in publish_candidates:
            parsed_datetime = self._parse_datetime_value(candidate)
            if parsed_datetime is not None:
                return parsed_datetime

        return None

    def _format_event_date(self, item):
        event_datetime = self._extract_event_datetime(item)
        if event_datetime is not None:
            return event_datetime.strftime('%Y-%m-%d %H:%M:%S')
        return "Unknown"

    def _build_event_content(self, item):
        title = item.get('title')
        publisher = item.get('publisher')
        summary = item.get('summary') or item.get('content')

        title_text = str(title).strip() if title is not None else ""
        if title_text.lower() in ("no content available", "no content"):
            title_text = ""

        publisher_text = str(publisher).strip() if publisher is not None else ""
        summary_text = str(summary).strip() if summary is not None else ""

        header_parts = [text for text in (title_text, publisher_text) if text]
        header = " - ".join(header_parts) if header_parts else ""

        if summary_text:
            if header:
                return f"{header}\n{summary_text}"
            return summary_text
        if header:
            return header

        link = item.get('link') or item.get('url')
        if link:
            link_text = str(link).strip()
            if link_text:
                return f"Source: {link_text}"

        return "No content available"

    def _extract_event_title(self, item):
        content = item.get('content')
        if isinstance(content, dict) and content.get('title'):
            title = content.get('title')
        else:
            title = item.get('title')

        if isinstance(title, dict):
            title = title.get('title')

        if title is not None:
            title_text = str(title).strip()
            if title_text and title_text.lower() not in ("no content available", "no content"):
                return title_text

        return "Unknown"

    def _extract_event_url(self, item):
        content = item.get('content')
        if isinstance(content, dict):
            click_through = content.get('clickThroughUrl')
            if isinstance(click_through, dict) and click_through.get('url'):
                return str(click_through.get('url')).strip()

            canonical = content.get('canonicalUrl')
            if isinstance(canonical, dict) and canonical.get('url'):
                return str(canonical.get('url')).strip()

            direct_link = content.get('link') or content.get('url')
            if direct_link:
                link_text = str(direct_link).strip()
                if link_text:
                    return link_text

        direct_link = item.get('link') or item.get('url')
        if direct_link:
            link_text = str(direct_link).strip()
            if link_text:
                return link_text

        click_through = item.get('clickThroughUrl')
        if isinstance(click_through, dict) and click_through.get('url'):
            return str(click_through.get('url')).strip()

        canonical = item.get('canonicalUrl')
        if isinstance(canonical, dict) and canonical.get('url'):
            return str(canonical.get('url')).strip()

        return "Unknown"

    def fetch_recent_events(self, stock_code, limit=None, days=3):
        """
        Fetch recent news events for a stock using yfinance.
        If days is provided, fetches news within the last `days` days.
        If limit is provided, limits the total number of events returned.
        """
        try:
            # Handle stock code format
            ticker_symbol = stock_code
            if stock_code.isdigit() and len(stock_code) == 6:
                if stock_code.startswith(('6', '9')):
                    ticker_symbol += '.SS'
                else:
                    ticker_symbol += '.SZ'
            
            ticker = yf.Ticker(ticker_symbol)
            news_items = self._normalize_news_items(ticker.news)
            normalized_days = self._coerce_positive_int(days, 3)
            normalized_limit = self._coerce_positive_int(limit, None)
            
            events = []
            if news_items:
                cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=normalized_days)
                for item in news_items:
                    event_datetime = self._extract_event_datetime(item)
                    if event_datetime is not None and event_datetime < cutoff_date:
                        continue

                    events.append({
                        'stock_code': stock_code,
                        'stock_name': ticker_symbol,
                        'event_title': self._extract_event_title(item),
                        'event_content': self._build_event_content(item),
                        'event_date': event_datetime.strftime('%Y-%m-%d %H:%M:%S') if event_datetime is not None else "Unknown",
                        'url': self._extract_event_url(item)
                    })
                    
                    if normalized_limit is not None and len(events) >= normalized_limit:
                        break
            return events
            
        except Exception as e:
            print(f"Failed to fetch news for {stock_code}: {e}")
            return []
