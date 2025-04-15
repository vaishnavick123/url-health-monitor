# URL Health Monitor

A Streamlit dashboard to monitor the health, uptime, and classification of URLs. This interface connects to a FastAPI backend to provide real-time health checks, response time tracking, anomaly detection, and classification.

---
## Features
- URL health checker that supports batch checking and live feedback
- Recent history view of checks with timestamps, response times and anomaly detection
- Overall dashboard displaying status distribution (UP/DOWN) and average uptime over the last 24 hours
- URL classification via LLM (e.g., domain-based categories)
- Uptime metrics for any specific URL across 24h, 7d, and 30d periods
- Mock URL controls to toggle and test response behavior

---

## Setup Instructions
- Install dependencies
`poetry install`
- Start the app using Docker
`docker-compose up --build`
- Streamlit frontend at: http://localhost:8501

