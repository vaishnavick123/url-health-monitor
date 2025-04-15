from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx
from datetime import datetime, timedelta
from typing import List, Optional
import sqlite3
from .url_classifier import classify_url
from .mock_service import mock_router


app = FastAPI()
app.include_router(mock_router)

# Database setup
conn = sqlite3.connect('url_checks.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        status TEXT NOT NULL,
        response_time REAL,
        checked_at TEXT NOT NULL
    )
''')
conn.commit()

# Pydantic model
class URLRequest(BaseModel):
    urls: List[HttpUrl]

class URLStatus(BaseModel):
    url: HttpUrl
    status: str
    response_time: float | None
    checked_at: str
    response_time_anomaly: bool

class URLHistory(BaseModel):
    url: HttpUrl
    status: str
    response_time: float | None
    checked_at: str
    
class HealthMetrics(BaseModel):
    total_monitored: int
    current_up: int
    current_down: int
    average_uptime_last_24h: float | None

class UptimeResponse(BaseModel):
    url: HttpUrl
    uptime_percentage: float | None
    period_start: str
    period_end: str

class RecentDowntime(BaseModel):
    url: HttpUrl
    down_since: str

class ClassifyRequest(BaseModel):
    urls: List[HttpUrl]

class ClassificationResult(BaseModel):
    url: HttpUrl
    category: str
    

# anomaly detection
def detect_anomaly(conn, url: str, threshold: int = 3, window: int = 10) -> bool:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status
        FROM checks
        WHERE url = ?
        ORDER BY checked_at DESC
        LIMIT ?
    """, (url, window))
    recent_checks = cursor.fetchall()

    if len(recent_checks) < 2:
        return False

    flips = 0
    prev_status = recent_checks[0][0]

    for check in recent_checks[1:]:
        if check[0] != prev_status:
            flips += 1
        prev_status = check[0]

    print(flips)
    return flips >= threshold


def check_url(url: str):
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
    except Exception as e:
        print(f"Error checking {url}: {e}")
        status = "DOWN"

    checked_at = datetime.utcnow().isoformat()

    cursor.execute(
        "INSERT INTO checks (url, status, response_time, checked_at) VALUES (?, ?, ?, ?)",
        (str(url), status, response_time, checked_at)
    )
    conn.commit()

    is_anomaly = detect_anomaly(conn, url)
   
    return {
        "url": url,
        "status": status,
        "response_time": response_time,
        "checked_at": checked_at,
        "response_time_anomaly": str(is_anomaly)
    }

# Routes
@app.post("/check", response_model=List[URLStatus])
def check_urls(request: URLRequest):
    results = [check_url(url) for url in request.urls]
    return results

@app.get("/history", response_model=List[URLHistory])
def get_history():
    cursor.execute("SELECT url, status, response_time, checked_at FROM checks ORDER BY checked_at DESC LIMIT 100")
    rows = cursor.fetchall()
    return [
        URLHistory(
            url=row[0],
            status=row[1],
            response_time=row[2],
            checked_at=row[3]
        ) for row in rows
    ]

@app.get("/health", response_model=HealthMetrics)
def get_health_metrics():
    cursor.execute("SELECT DISTINCT url FROM checks")
    all_urls = [row[0] for row in cursor.fetchall()]
    total_monitored = len(all_urls)

    current_statuses = {}
    for url in all_urls:
        cursor.execute("SELECT status FROM checks WHERE url = ? ORDER BY checked_at DESC LIMIT 1", (url,))
        result = cursor.fetchone()
        if result:
            current_statuses[url] = result[0]

    current_up = sum(1 for status in current_statuses.values() if "UP" in status)
    current_down = total_monitored - current_up

    now = datetime.utcnow()
    twenty_four_hours_ago = now - timedelta(hours=24)
    total_uptime_seconds = 0
    total_checks_last_24h = 0

    for url in all_urls:
        cursor.execute(
            "SELECT status, checked_at FROM checks WHERE url = ? AND checked_at >= ?",
            (url, twenty_four_hours_ago.isoformat())
        )
        url_checks = cursor.fetchall()
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

@app.get("/metrics/{url:path}", response_model=UptimeResponse)
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
        raise HTTPException(status_code=400, detail="Invalid period. Supported values: 24h, 7d, 30d")

    cursor.execute(
        "SELECT COUNT(*) FROM checks WHERE url = ? AND checked_at BETWEEN ? AND ?",
        (url, start_time.isoformat(), end_time.isoformat())
    )
    total_checks = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM checks WHERE url = ? AND status LIKE 'UP' AND checked_at BETWEEN ? AND ?",
        (url, start_time.isoformat(), end_time.isoformat())
    )
    up_checks = cursor.fetchone()[0]

    uptime_percentage = (up_checks / total_checks * 100) if total_checks > 0 else None

    return {
        "url": url,
        "uptime_percentage": uptime_percentage,
        "period_start": start_time.isoformat(),
        "period_end": end_time.isoformat(),
    }

@app.get("/recent_downtime", response_model=List[RecentDowntime])
def get_recent_downtime(limit: int = 5):
    cursor.execute("""
        SELECT url, MIN(checked_at)
        FROM checks
        WHERE status NOT LIKE 'UP'
        GROUP BY url
        HAVING MAX(CASE WHEN status LIKE 'UP' THEN 1 ELSE 0 END) = 0 OR
               MAX(checked_at) > (SELECT MAX(checked_at) FROM checks WHERE url = checks.url AND status LIKE 'UP')
        ORDER BY MIN(checked_at) DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    return [{"url": row[0], "down_since": row[1]} for row in rows]



@app.post("/classify", response_model=List[ClassificationResult])
def classify_urls_endpoint(request: ClassifyRequest):
    results = []
    for url in request.urls:
        category = classify_url(str(url))
        results.append({"url": url, "category": category})
    return results
