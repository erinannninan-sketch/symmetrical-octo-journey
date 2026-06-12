"""
modules/news.py
Fetches top headlines from NewsAPI across configured topics.
"""

import os
import requests
from datetime import datetime, timezone


def get_news(max_per_topic: int = 3) -> dict:
    """
    Returns a dict keyed by topic with lists of article dicts.
    Falls back to demo articles when no API key is set.
    """
    api_key = os.getenv("NEWS_API_KEY", "")
    topics_raw = os.getenv("NEWS_TOPICS", "technology,science,startups")
    topics = [t.strip() for t in topics_raw.split(",") if t.strip()]

    if not api_key or api_key == "your_newsapi_key":
        return _demo_news(topics)

    results: dict = {}
    for topic in topics:
        try:
            url = (
                "https://newsapi.org/v2/everything"
                f"?q={topic}&sortBy=publishedAt&pageSize={max_per_topic}"
                f"&language=en&apiKey={api_key}"
            )
            data = requests.get(url, timeout=8).json()
            articles = []
            for a in data.get("articles", [])[:max_per_topic]:
                pub = a.get("publishedAt", "")
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    formatted = dt.astimezone().strftime("%b %d, %H:%M")
                except Exception:
                    formatted = pub[:10]

                articles.append({
                    "title":   a.get("title", "No title"),
                    "source":  a.get("source", {}).get("name", "Unknown"),
                    "url":     a.get("url", "#"),
                    "summary": (a.get("description") or "")[:140],
                    "time":    formatted,
                    "image":   a.get("urlToImage"),
                })
            results[topic] = articles
        except Exception as exc:
            results[topic] = [{"title": f"Error: {exc}", "source": "",
                               "url": "#", "summary": "", "time": "", "image": None}]

    return results


def _demo_news(topics: list) -> dict:
    demo = {
        "title":   "Engineers Build Drone That Navigates Using Neutrino Detection",
        "source":  "TechCrunch",
        "url":     "https://techcrunch.com",
        "summary": "A research team has demonstrated autonomous navigation using "
                   "cosmic-ray muon tomography — no GPS required.",
        "time":    datetime.now().strftime("%b %d, %H:%M"),
        "image":   None,
    }
    return {t: [
        {**demo, "title": f"[Demo] Top story in '{t}' — add your NewsAPI key to load live articles."}
    ] for t in topics}