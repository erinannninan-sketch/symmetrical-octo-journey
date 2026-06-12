"""
modules/github_stats.py
Fetches GitHub profile stats, recent commits, and repo info
using the GitHub REST API (no PyGithub dependency needed).
"""

import os
import requests
from datetime import datetime, timezone, timedelta


_BASE = "https://api.github.com"


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    h = {"Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28"}
    if token and token != "your_github_personal_access_token":
        h["Authorization"] = f"Bearer {token}"
    return h


def get_github_stats() -> dict:
    username = os.getenv("GITHUB_USERNAME", "")
    if not username or username == "your_github_username":
        return _demo_stats()

    try:
        # Profile
        profile_r = requests.get(f"{_BASE}/users/{username}",
                                 headers=_headers(), timeout=8)
        profile_r.raise_for_status()
        profile = profile_r.json()

        # Repos (sorted by push date)
        repos_r = requests.get(
            f"{_BASE}/users/{username}/repos?sort=pushed&per_page=5",
            headers=_headers(), timeout=8)
        repos_r.raise_for_status()
        repos_raw = repos_r.json()

        repos = []
        for r in repos_raw[:5]:
            repos.append({
                "name":        r["name"],
                "description": (r.get("description") or "—")[:80],
                "stars":       r["stargazers_count"],
                "forks":       r["forks_count"],
                "language":    r.get("language") or "—",
                "url":         r["html_url"],
                "updated":     _relative_time(r.get("pushed_at", "")),
            })

        # Recent events (commits/pushes)
        events_r = requests.get(
            f"{_BASE}/users/{username}/events/public?per_page=10",
            headers=_headers(), timeout=8)
        events_r.raise_for_status()
        events_raw = events_r.json()

        recent_commits = []
        seen = set()
        for event in events_raw:
            if event["type"] == "PushEvent":
                repo_name = event["repo"]["name"].split("/")[-1]
                for commit in event.get("payload", {}).get("commits", [])[:2]:
                    sha = commit["sha"][:7]
                    if sha in seen:
                        continue
                    seen.add(sha)
                    recent_commits.append({
                        "repo":    repo_name,
                        "sha":     sha,
                        "message": commit["message"].split("\n")[0][:72],
                        "time":    _relative_time(event.get("created_at", "")),
                    })
            if len(recent_commits) >= 5:
                break

        # Contribution streak (approximate via events in last 30 days)
        streak = _estimate_streak(events_raw)

        return {
            "username":       profile["login"],
            "name":           profile.get("name") or profile["login"],
            "avatar":         profile.get("avatar_url", ""),
            "public_repos":   profile.get("public_repos", 0),
            "followers":      profile.get("followers", 0),
            "following":      profile.get("following", 0),
            "bio":            (profile.get("bio") or ""),
            "repos":          repos,
            "recent_commits": recent_commits,
            "streak_days":    streak,
            "error":          None,
        }

    except Exception as exc:
        return {"error": str(exc), "repos": [], "recent_commits": []}


def _relative_time(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        if delta.days > 30:
            return dt.strftime("%b %d")
        if delta.days >= 1:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours >= 1:
            return f"{hours}h ago"
        return f"{delta.seconds // 60}m ago"
    except Exception:
        return iso[:10]


def _estimate_streak(events: list) -> int:
    push_days = set()
    for event in events:
        if event["type"] == "PushEvent":
            try:
                dt = datetime.fromisoformat(
                    event["created_at"].replace("Z", "+00:00"))
                push_days.add(dt.date())
            except Exception:
                pass
    if not push_days:
        return 0
    streak = 0
    day = datetime.now(timezone.utc).date()
    while day in push_days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _demo_stats() -> dict:
    return {
        "username": "annie-dev",
        "name": "Erin Ann Ninan",
        "avatar": "",
        "public_repos": 12,
        "followers": 34,
        "following": 28,
        "bio": "EEE @ TKM | Embedded Systems | IoT | Building things.",
        "repos": [
            {"name": "smart-microgrid", "description": "AI-assisted energy management",
             "stars": 5, "forks": 1, "language": "Python", "url": "#", "updated": "2h ago"},
            {"name": "self-balancing-bot", "description": "MPU6050 + PID + L298N",
             "stars": 3, "forks": 0, "language": "C++", "url": "#", "updated": "1d ago"},
            {"name": "portfolio", "description": "Personal portfolio site",
             "stars": 2, "forks": 0, "language": "HTML", "url": "#", "updated": "3d ago"},
        ],
        "recent_commits": [
            {"repo": "smart-microgrid", "sha": "a1b2c3d",
             "message": "Add PID tuning for load balancing", "time": "2h ago"},
            {"repo": "self-balancing-bot", "sha": "e4f5g6h",
             "message": "Fix MPU6050 calibration drift", "time": "1d ago"},
        ],
        "streak_days": 4,
        "error": None,
    }