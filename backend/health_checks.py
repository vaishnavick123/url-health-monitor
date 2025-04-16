import httpx
from datetime import datetime, timedelta
from .db import execute_query, fetch_one, fetch_all


def detect_anomaly(url: str, threshold: int = 3, window: int = 10) -> bool:
    recent_checks = fetch_all("""
        SELECT status
        FROM checks
        WHERE url = ?
        ORDER BY checked_at DESC
        LIMIT ?
    """, (url, window))

    if len(recent_checks) < 2:
        return False

    flips = 0
    prev_status = recent_checks[0]['status']

    for check in recent_checks[1:]:
        if check['status'] != prev_status:
            flips += 1
        prev_status = check['status']

    print(f"Anomaly flips for {url}: {flips}")
    return flips >= threshold




def check_url(url):
    url = str(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    response_time = None
    try:
        start = datetime.utcnow()
        response = httpx.get(url, timeout=5, headers=headers)
        end = datetime.utcnow()
        response_time = (end - start).total_seconds() * 1000  # in ms
        print(f"Checked {url} → Status Code: {response.status_code}, Response Time: {response_time:.2f} ms")
        status = "UP" if response.status_code == 200 else f"DOWN ({response.status_code})"
    except httpx.ConnectError as e:
        print(f"Error connecting to {url}: {e}")
        status = "DOWN (Connection Error)"
    except httpx.TimeoutException as e:
        print(f"Timeout checking {url}: {e}")
        status = "DOWN (Timeout)"
    except Exception as e:
        print(f"Error checking {url}: {e}")
        status = "DOWN (Error)"

    checked_at = datetime.utcnow().isoformat()

    execute_query(
        "INSERT INTO checks (url, status, response_time, checked_at) VALUES (?, ?, ?, ?)",
        (str(url), status, response_time, checked_at)
    )

    is_anomaly = detect_anomaly(url)

    return {
        "url": url,
        "status": status,
        "response_time": response_time,
        "checked_at": checked_at,
        "response_time_anomaly": str(is_anomaly)
    }

def get_health_metrics():
    all_urls_result = fetch_all("SELECT DISTINCT url FROM checks")
    all_urls = [row['url'] for row in all_urls_result]
    total_monitored = len(all_urls)

    current_statuses = {}
    for url in all_urls:
        result = fetch_one("SELECT status FROM checks WHERE url = ? ORDER BY checked_at DESC LIMIT 1", (url,))
        if result:
            current_statuses[url] = result['status']

    current_up = sum(1 for status in current_statuses.values() if "UP" in status)
    current_down = total_monitored - current_up

    now = datetime.utcnow()
    twenty_four_hours_ago = now - timedelta(hours=24)
    total_uptime_seconds = 0
    total_checks_last_24h = 0

    for url in all_urls:
        url_checks = fetch_all(
            "SELECT status, checked_at FROM checks WHERE url = ? AND checked_at >= ?",
            (url, twenty_four_hours_ago.isoformat())
        )
        up_count = sum(1 for status, _ in url_checks if "UP" in status)
        total_checks_last_24h += len(url_checks)
        if total_checks_last_24h > 0 and len(url_checks) > 0:
            total_uptime_seconds += (up_count / len(url_checks))

    average_uptime_last_24h = (total_uptime_seconds / total_monitored * 100) if total_monitored > 0 else None

    return {
        "total_monitored": total_monitored,
        "current_up": current_up,
        "current_down": current_down,
        "average_uptime_last_24h": average_uptime_last_24h,
    }

def get_uptime(url: str, period: str = "24h"):
    now = datetime.utcnow()
    end_time = now
    if period == "24h":
        start_time = now - timedelta(hours=24)
    elif period == "7d":
        start_time = now - timedelta(days=7)
    elif period == "30d":
        start_time = now - timedelta(days=30)
    else:
        raise ValueError("Invalid period. Supported values: 24h, 7d, 30d")

    total_checks_result = fetch_one(
        "SELECT COUNT(*) as count FROM checks WHERE url = ? AND checked_at BETWEEN ? AND ?",
        (url, start_time.isoformat(), end_time.isoformat())
    )
    total_checks = total_checks_result['count'] if total_checks_result else 0

    up_checks_result = fetch_one(
        "SELECT COUNT(*) as count FROM checks WHERE url = ? AND status LIKE 'UP' AND checked_at BETWEEN ? AND ?",
        (url, start_time.isoformat(), end_time.isoformat())
    )
    up_checks = up_checks_result['count'] if up_checks_result else 0

    uptime_percentage = (up_checks / total_checks * 100) if total_checks > 0 else None

    return {
        "url": url,
        "uptime_percentage": uptime_percentage,
        "period_start": start_time.isoformat(),
        "period_end": end_time.isoformat(),
    }

def get_recent_downtime(limit: int = 5):
    rows = fetch_all("""
        SELECT url, MIN(checked_at) as down_since
        FROM checks
        WHERE status NOT LIKE 'UP'
        GROUP BY url
        HAVING MAX(CASE WHEN status LIKE 'UP' THEN 1 ELSE 0 END) = 0 OR
               MAX(checked_at) > (SELECT MAX(checked_at) FROM checks WHERE url = checks.url AND status LIKE 'UP')
        ORDER BY MIN(checked_at) DESC
        LIMIT ?
    """, (limit,))
    return [{"url": row['url'], "down_since": row['down_since']} for row in rows]

def get_history(limit: int = 100):
    rows = fetch_all("SELECT url, status, response_time, checked_at FROM checks ORDER BY checked_at DESC LIMIT ?", (limit,))
    return [
        {"url": row['url'], "status": row['status'], "response_time": row['response_time'], "checked_at": row['checked_at']}
        for row in rows
    ]