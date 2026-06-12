"""
modules/system_monitor.py
Real-time system vitals using psutil.
"""

import platform
import shutil
import time
from datetime import datetime, timedelta

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False


def get_system_stats() -> dict:
    """Returns CPU, RAM, disk, network, uptime, and process info."""
    if not PSUTIL_OK:
        return _demo_stats()

    try:
        # CPU
        cpu_pct    = psutil.cpu_percent(interval=0.5)
        cpu_freq   = psutil.cpu_freq()
        cpu_count  = psutil.cpu_count(logical=True)
        cpu_phys   = psutil.cpu_count(logical=False)

        # RAM
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk (root)
        disk = psutil.disk_usage("/")

        # Network
        net1 = psutil.net_io_counters()
        time.sleep(0.5)
        net2 = psutil.net_io_counters()
        net_sent_kbps = (net2.bytes_sent - net1.bytes_sent) * 2 / 1024
        net_recv_kbps = (net2.bytes_recv - net1.bytes_recv) * 2 / 1024

        # Uptime
        boot_time = psutil.boot_time()
        uptime_sec = time.time() - boot_time
        uptime_str = _fmt_uptime(uptime_sec)

        # Top processes by CPU
        procs = []
        for proc in sorted(
            psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
            key=lambda p: p.info["cpu_percent"] or 0,
            reverse=True
        )[:5]:
            procs.append({
                "pid":    proc.info["pid"],
                "name":   proc.info["name"],
                "cpu":    round(proc.info["cpu_percent"] or 0, 1),
                "mem":    round(proc.info["memory_percent"] or 0, 1),
            })

        # Temperature (Linux only, graceful fail)
        temps = []
        try:
            raw_temps = psutil.sensors_temperatures()
            for name, entries in raw_temps.items():
                for entry in entries[:1]:
                    temps.append({
                        "label": entry.label or name,
                        "current": entry.current,
                        "high": entry.high,
                    })
        except (AttributeError, Exception):
            pass

        return {
            "cpu": {
                "percent":   cpu_pct,
                "freq_ghz":  round(cpu_freq.current / 1000, 2) if cpu_freq else "—",
                "cores":     cpu_count,
                "phys_cores": cpu_phys,
                "status":    _status(cpu_pct, 70, 90),
            },
            "ram": {
                "total_gb":  _gb(ram.total),
                "used_gb":   _gb(ram.used),
                "free_gb":   _gb(ram.available),
                "percent":   ram.percent,
                "status":    _status(ram.percent, 70, 85),
            },
            "swap": {
                "total_gb": _gb(swap.total),
                "used_gb":  _gb(swap.used),
                "percent":  swap.percent,
            },
            "disk": {
                "total_gb": _gb(disk.total),
                "used_gb":  _gb(disk.used),
                "free_gb":  _gb(disk.free),
                "percent":  disk.percent,
                "status":   _status(disk.percent, 75, 90),
            },
            "network": {
                "sent_kbps": round(net_sent_kbps, 1),
                "recv_kbps": round(net_recv_kbps, 1),
            },
            "uptime":  uptime_str,
            "os":      f"{platform.system()} {platform.release()}",
            "hostname": platform.node(),
            "processes": procs,
            "temps":     temps,
            "error":     None,
        }

    except Exception as exc:
        return {"error": str(exc)}


def _gb(b: int) -> float:
    return round(b / (1024 ** 3), 2)


def _fmt_uptime(secs: float) -> str:
    d = int(secs // 86400)
    h = int((secs % 86400) // 3600)
    m = int((secs % 3600) // 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    parts.append(f"{m}m")
    return " ".join(parts)


def _status(val: float, warn: float, crit: float) -> str:
    if val >= crit: return "critical"
    if val >= warn: return "warning"
    return "ok"


def _demo_stats() -> dict:
    return {
        "cpu":  {"percent": 34.2, "freq_ghz": 2.4, "cores": 8, "phys_cores": 4, "status": "ok"},
        "ram":  {"total_gb": 16.0, "used_gb": 7.3, "free_gb": 8.7, "percent": 45.6, "status": "ok"},
        "swap": {"total_gb": 4.0, "used_gb": 0.1, "percent": 2.5},
        "disk": {"total_gb": 500.0, "used_gb": 212.0, "free_gb": 288.0, "percent": 42.4, "status": "ok"},
        "network": {"sent_kbps": 24.5, "recv_kbps": 112.3},
        "uptime": "2d 4h 17m",
        "os": "Linux 6.5.0",
        "hostname": "pulse-host",
        "processes": [
            {"pid": 1234, "name": "python3", "cpu": 12.3, "mem": 2.1},
            {"pid": 5678, "name": "chrome",  "cpu":  8.4, "mem": 5.6},
        ],
        "temps": [],
        "error": None,
    }