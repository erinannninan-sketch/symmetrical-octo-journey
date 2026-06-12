"""
app.py — Pulse: Personal Morning Dashboard
==========================================
Run:  python app.py
      then open http://localhost:5000
"""

import os
import threading
from datetime import datetime
from pathlib import Path

import schedule
import time
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

from modules.weather       import get_weather
from modules.news          import get_news
from modules.github_stats  import get_github_stats
from modules.quote         import get_quote
from modules.study_tracker import (
    get_summary, start_session, stop_session,
    add_manual, get_active,
)
from modules.system_monitor import get_system_stats
from modules.mailer         import send_daily_digest, save_text_summary


# ── Flask setup ──────────────────────────────────────────────────────────────

app = Flask(__name__)

# Simple in-memory cache to avoid hammering APIs on every refresh
_cache: dict = {}
_cache_ts: dict = {}
CACHE_TTL = 300  # seconds


def _cached(key: str, fn, ttl: int = CACHE_TTL):
    now = time.time()
    if key not in _cache or (now - _cache_ts.get(key, 0)) > ttl:
        _cache[key]    = fn()
        _cache_ts[key] = now
    return _cache[key]


# ── Dashboard context ─────────────────────────────────────────────────────────

def build_context() -> dict:
    return {
        "weather": _cached("weather", get_weather, 600),
        "news":    _cached("news",    get_news,    1800),
        "github":  _cached("github",  get_github_stats, 900),
        "quote":   _cached("quote",   get_quote,   86400),
        "study":   get_summary(7),          # always fresh
        "system":  get_system_stats(),      # always fresh
        "now":     datetime.now().strftime("%A, %B %d %Y"),
        "time":    datetime.now().strftime("%H:%M"),
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    ctx = build_context()
    return render_template("dashboard.html", **ctx)


@app.route("/api/refresh")
def api_refresh():
    """Force-refresh all caches and return JSON payload."""
    _cache.clear()
    _cache_ts.clear()
    return jsonify(build_context())


@app.route("/api/system")
def api_system():
    """Live system stats (no cache)."""
    return jsonify(get_system_stats())


# ── Study tracker endpoints ───────────────────────────────────────────────────

@app.route("/api/study/start", methods=["POST"])
def api_study_start():
    body  = request.get_json(silent=True) or {}
    topic = body.get("topic", "General")
    goal  = body.get("goal", "")
    return jsonify(start_session(topic, goal))


@app.route("/api/study/stop", methods=["POST"])
def api_study_stop():
    body  = request.get_json(silent=True) or {}
    notes = body.get("notes", "")
    return jsonify(stop_session(notes))


@app.route("/api/study/add", methods=["POST"])
def api_study_add():
    body = request.get_json(silent=True) or {}
    return jsonify(add_manual(
        topic        = body.get("topic", "General"),
        duration_min = float(body.get("duration_min", 0)),
        notes        = body.get("notes", ""),
        when         = body.get("when"),
    ))


@app.route("/api/study/summary")
def api_study_summary():
    days = int(request.args.get("days", 7))
    return jsonify(get_summary(days))


@app.route("/api/study/active")
def api_study_active():
    return jsonify({"active": get_active()})


# ── Email digest endpoint ─────────────────────────────────────────────────────

@app.route("/api/send-digest", methods=["POST"])
def api_send_digest():
    ctx = build_context()
    save_text_summary(ctx)
    result = send_daily_digest(ctx)
    return jsonify(result)


# ── Scheduler ─────────────────────────────────────────────────────────────────

def _scheduled_digest():
    """Called by the background scheduler at the configured time."""
    print(f"[Pulse] Sending scheduled digest at {datetime.now().strftime('%H:%M')}")
    ctx = build_context()
    save_text_summary(ctx)
    result = send_daily_digest(ctx)
    print(f"[Pulse] Digest result: {result['msg']}")


def _run_scheduler():
    report_time = os.getenv("DAILY_REPORT_TIME", "07:30")
    schedule.every().day.at(report_time).do(_scheduled_digest)
    print(f"[Pulse] Scheduler active — daily digest at {report_time}")
    while True:
        schedule.run_pending()
        time.sleep(30)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Start the background scheduler in a daemon thread
    scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
    scheduler_thread.start()

    print(f"\n{'='*52}")
    print(f"  🌅 Pulse is running  →  http://localhost:{port}")
    print(f"{'='*52}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)