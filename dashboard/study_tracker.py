"""
modules/study_tracker.py
Logs and retrieves study sessions stored in a JSON file.
Supports start/stop, manual entries, and weekly summaries.
"""

import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional


LOG_FILE = Path(os.getenv("STUDY_LOG_FILE", "reports/study_log.json"))


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load() -> dict:
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"sessions": [], "active": None}


def _save(data: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(data, indent=2))


# ── Public API ────────────────────────────────────────────────────────────────

def start_session(topic: str, goal: str = "") -> dict:
    """Begin a study session. Returns error if one is already active."""
    data = _load()
    if data.get("active"):
        return {"ok": False, "msg": "A session is already active. Stop it first."}
    data["active"] = {
        "topic":     topic,
        "goal":      goal,
        "start":     datetime.now().isoformat(),
    }
    _save(data)
    return {"ok": True, "msg": f"Session started: {topic}"}


def stop_session(notes: str = "") -> dict:
    """End the current session and persist it."""
    data = _load()
    if not data.get("active"):
        return {"ok": False, "msg": "No active session to stop."}

    active = data["active"]
    start_dt = datetime.fromisoformat(active["start"])
    end_dt   = datetime.now()
    duration_min = round((end_dt - start_dt).total_seconds() / 60, 1)

    session = {
        "topic":        active["topic"],
        "goal":         active.get("goal", ""),
        "notes":        notes,
        "start":        active["start"],
        "end":          end_dt.isoformat(),
        "duration_min": duration_min,
        "date":         end_dt.date().isoformat(),
    }
    data["sessions"].append(session)
    data["active"] = None
    _save(data)
    return {"ok": True, "session": session,
            "msg": f"Logged {duration_min} min of '{active['topic']}'"}


def add_manual(topic: str, duration_min: float,
               notes: str = "", when: Optional[str] = None) -> dict:
    """Manually log a completed session."""
    data = _load()
    when_dt = datetime.fromisoformat(when) if when else datetime.now()
    session = {
        "topic":        topic,
        "goal":         "",
        "notes":        notes,
        "start":        (when_dt - timedelta(minutes=duration_min)).isoformat(),
        "end":          when_dt.isoformat(),
        "duration_min": duration_min,
        "date":         when_dt.date().isoformat(),
        "manual":       True,
    }
    data["sessions"].append(session)
    _save(data)
    return {"ok": True, "session": session}


def get_summary(days: int = 7) -> dict:
    """
    Returns study stats for the last `days` days:
    total minutes, daily breakdown, topic distribution,
    longest session, and active session if any.
    """
    data  = _load()
    today = date.today()
    cutoff = today - timedelta(days=days - 1)

    recent = [
        s for s in data["sessions"]
        if date.fromisoformat(s["date"]) >= cutoff
    ]

    total_min = sum(s["duration_min"] for s in recent)

    # Daily totals
    daily: dict = {}
    for i in range(days):
        d = (cutoff + timedelta(days=i)).isoformat()
        daily[d] = 0.0
    for s in recent:
        daily[s["date"]] = daily.get(s["date"], 0.0) + s["duration_min"]

    # Topic totals
    topics: dict = {}
    for s in recent:
        topics[s["topic"]] = topics.get(s["topic"], 0.0) + s["duration_min"]

    longest = max(recent, key=lambda x: x["duration_min"]) if recent else None

    return {
        "total_min":   round(total_min, 1),
        "total_hours": round(total_min / 60, 2),
        "session_count": len(recent),
        "daily":       daily,
        "topics":      topics,
        "longest":     longest,
        "active":      data.get("active"),
        "today_min":   round(daily.get(today.isoformat(), 0.0), 1),
        "sessions":    recent[-10:],   # last 10 sessions
    }


def get_active() -> Optional[dict]:
    return _load().get("active")