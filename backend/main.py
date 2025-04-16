from fastapi import FastAPI, HTTPException
from typing import List
from . import types
from .health_checks import check_url, get_health_metrics, get_uptime, get_recent_downtime, get_history
from .url_classifier import classify_url
from .mock_service import mock_router
from .db import init_db

app = FastAPI()
app.include_router(mock_router)

# Initialize the database on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Routes
@app.post("/check", response_model=List[types.URLStatus])
def check_urls(request: types.URLRequest):
    results = [check_url(url) for url in request.urls]
    return results

@app.get("/history", response_model=List[types.URLHistory])
def get_history_endpoint():
    return get_history()

@app.get("/health", response_model=types.HealthMetrics)
def get_health_metrics_endpoint():
    return get_health_metrics()

@app.get("/metrics/{url:path}", response_model=types.UptimeResponse)
def get_uptime_endpoint(url: str, period: str = "24h"):
    try:
        return get_uptime(url, period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/recent_downtime", response_model=List[types.RecentDowntime])
def get_recent_downtime_endpoint(limit: int = 5):
    return get_recent_downtime(limit)

@app.post("/classify", response_model=List[types.ClassificationResult])
def classify_urls_endpoint(request: types.ClassifyRequest):
    results = []
    for url in request.urls:
        category = classify_url(str(url))
        results.append({"url": url, "category": category})
    return results