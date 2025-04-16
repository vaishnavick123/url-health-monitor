from pydantic import BaseModel, HttpUrl
from typing import List, Optional

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