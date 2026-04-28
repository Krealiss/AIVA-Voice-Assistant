"""
Мінімальна версія AIVA для тестування dashboard
Без голосового розпізнавання та TTS
"""
import os
import sys
import logging

# Додаємо src до шляху
sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("aiva_lite")

# Імпорт dashboard модулів
from dashboard_api import router as dashboard_router
from websocket_manager import websocket_endpoint

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AIVA Lite Dashboard Ready")
    yield
    logger.info("AIVA Lite Dashboard Shutdown")

app = FastAPI(title="AIVA Lite Dashboard", lifespan=lifespan)

# Статичні файли (на рівень вище src)
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Dashboard API
app.include_router(dashboard_router)

# Головна сторінка
@app.get("/")
def root():
    return FileResponse(os.path.join(static_path, "dashboard.html"))

@app.get("/dashboard")
def dashboard():
    return FileResponse(os.path.join(static_path, "dashboard.html"))

# WebSocket
@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    await websocket_endpoint(websocket)

# Health check
@app.get("/api/health")
def health():
    return {"ok": True, "version": "0.9.0-lite"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AIVA Lite Dashboard on http://127.0.0.1:8787")
    uvicorn.run(app, host="127.0.0.1", port=8787)
