"""
modules/quote.py
Fetches a motivational quote from ZenQuotes (free, no API key).
Falls back to a curated local list on failure.
"""

import random
import requests


FALLBACK_QUOTES = [
    ("The best way to predict the future is to invent it.",
     "Alan Kay"),
    ("Simplicity is the soul of efficiency.",
     "Austin Freeman"),
    ("First, solve the problem. Then, write the code.",
     "John Johnson"),
    ("Code is like humor. When you have to explain it, it's bad.",
     "Cory House"),
    ("Programs must be written for people to read, and only incidentally for machines to execute.",
     "Harold Abelson"),
    ("An investment in knowledge pays the best interest.",
     "Benjamin Franklin"),
    ("The secret of getting ahead is getting started.",
     "Mark Twain"),
    ("Do what you can, with what you have, where you are.",
     "Theodore Roosevelt"),
    ("It always seems impossible until it's done.",
     "Nelson Mandela"),
    ("Build something 100 people love, not something 1 million people kind of like.",
     "Paul Graham"),
    ("Stay hungry. Stay foolish.",
     "Steve Jobs"),
    ("The only way to do great work is to love what you do.",
     "Steve Jobs"),
    ("Move fast and learn things.",
     "Engineering Folklore"),
    ("A ship in harbor is safe, but that is not what ships are for.",
     "John A. Shedd"),
    ("Done is better than perfect.",
     "Sheryl Sandberg"),
]


def get_quote() -> dict:
    """
    Returns a dict with 'text' and 'author'.
    Tries ZenQuotes first, falls back to local list.
    """
    try:
        resp = requests.get("https://zenquotes.io/api/random",
                            timeout=6)
        if resp.status_code == 200:
            data = resp.json()[0]
            return {
                "text":   data.get("q", ""),
                "author": data.get("a", "Unknown"),
                "source": "zenquotes",
            }
    except Exception:
        pass

    text, author = random.choice(FALLBACK_QUOTES)
    return {"text": text, "author": author, "source": "local"}