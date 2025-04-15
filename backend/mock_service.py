from fastapi import APIRouter
from fastapi.responses import JSONResponse

mock_router = APIRouter()
mock_service_up = {"status": True}  # in-memory toggle

@mock_router.get("/mock-url")
def test_mock_url():
    if mock_service_up["status"]:
        return {"message": "✅ Mock service is UP"}
    else:
        return JSONResponse(status_code=500, content={"error": "💥 Mock service is DOWN"})

@mock_router.post("/toggle-mock-url")
def toggle_mock_url():
    mock_service_up["status"] = not mock_service_up["status"]
    return {"new_status": "UP" if mock_service_up["status"] else "DOWN"}
