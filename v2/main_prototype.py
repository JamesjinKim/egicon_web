#!/usr/bin/env python3
"""
EG-ICON V2 Digital Twin Dashboard Prototype
OLED 제조공장 디지털 트윈 프로토타입 서버

Author: ShinHoTechnology
Version: V2.0 Prototype
Date: 2025-07-08
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import asyncio
import json
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EG-ICON V2 Digital Twin Dashboard",
    description="OLED 제조공장 디지털 트윈 프로토타입",
    version="2.0.0"
)

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory="frontend"), name="static")
templates = Jinja2Templates(directory="frontend")

# Mock 데이터 생성기 import
from mock_data_generator import MockDataGenerator
from websocket_simulator import WebSocketSimulator

# 전역 객체
mock_generator = MockDataGenerator()
ws_simulator = WebSocketSimulator()

@app.get("/", response_class=HTMLResponse)
async def main_dashboard(request: Request):
    """메인 대시보드 - 공장 전체 현황"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def modern_dashboard(request: Request):
    """새로운 모던 대시보드"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """상세 분석 페이지"""
    return templates.TemplateResponse("analytics.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """설정 관리 페이지"""
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """사용자 관리 페이지"""
    return templates.TemplateResponse("users.html", {"request": request})

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """로그 검색 페이지"""
    return templates.TemplateResponse("logs.html", {"request": request})

@app.get("/process/deposition", response_class=HTMLResponse)
async def process_deposition(request: Request):
    """증착 공정 페이지"""
    return templates.TemplateResponse("process_deposition.html", {"request": request})

@app.get("/process/photo", response_class=HTMLResponse)
async def process_photo(request: Request):
    """포토 공정 페이지"""
    return templates.TemplateResponse("process_photo.html", {"request": request})

@app.get("/process/etch", response_class=HTMLResponse)
async def process_etch(request: Request):
    """식각 공정 페이지"""
    return templates.TemplateResponse("process_etch.html", {"request": request})

@app.get("/process/encapsulation", response_class=HTMLResponse)
async def process_encapsulation(request: Request):
    """봉지 공정 페이지"""
    return templates.TemplateResponse("process_encapsulation.html", {"request": request})

@app.get("/process/inspection", response_class=HTMLResponse)
async def process_inspection(request: Request):
    """검사 공정 페이지"""
    return templates.TemplateResponse("process_inspection.html", {"request": request})

@app.get("/process/packaging", response_class=HTMLResponse)
async def process_packaging(request: Request):
    """패키징 공정 페이지"""
    return templates.TemplateResponse("process_packaging.html", {"request": request})

@app.get("/process/shipping", response_class=HTMLResponse)
async def process_shipping(request: Request):
    """출하 공정 페이지"""
    return templates.TemplateResponse("process_shipping.html", {"request": request})

# API 엔드포인트
@app.get("/api/factory/kpi")
async def get_factory_kpi():
    """공장 전체 KPI 데이터 반환"""
    return mock_generator.get_factory_kpi()

@app.get("/api/factory/layout")
async def get_factory_layout():
    """공장 평면도 데이터 반환"""
    return mock_generator.get_factory_layout()

@app.get("/api/process/{process_name}/sensors")
async def get_process_sensors(process_name: str):
    """공정별 센서 데이터 반환"""
    return mock_generator.get_process_sensors(process_name)

@app.get("/api/process/{process_name}/prediction")
async def get_process_prediction(process_name: str):
    """공정별 예지 보전 데이터 반환"""
    return mock_generator.get_process_prediction(process_name)

@app.get("/api/sensors/neural-network")
async def get_neural_network_status():
    """오감 신경망 상태 반환"""
    return mock_generator.get_neural_network_status()

# WebSocket 엔드포인트
@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket):
    """실시간 데이터 WebSocket"""
    await ws_simulator.connect(websocket)

# 서버 시작 시 실행
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    logger.info("🏭 EG-ICON V2 Digital Twin Dashboard 시작")
    logger.info("📊 Mock 데이터 생성기 초기화")
    await mock_generator.initialize()
    
    logger.info("🔌 WebSocket 시뮬레이터 시작")
    await ws_simulator.start()
    
    logger.info("✅ V2 프로토타입 서버 준비 완료")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 정리"""
    logger.info("🔄 V2 프로토타입 서버 종료")
    await ws_simulator.stop()

if __name__ == "__main__":
    print("🏭 EG-ICON V2 Digital Twin Dashboard Prototype")
    print("=" * 50)
    print("📍 URL: http://localhost:8002")
    print("📊 메인 대시보드: http://localhost:8002/")
    print("🏭 증착 공정: http://localhost:8002/process/deposition")
    print("📸 포토 공정: http://localhost:8002/process/photo")
    print("⚗️ 식각 공정: http://localhost:8002/process/etch")
    print("📦 봉지 공정: http://localhost:8002/process/encapsulation")
    print("🔍 검사 공정: http://localhost:8002/process/inspection")
    print("📦 패키징 공정: http://localhost:8002/process/packaging")
    print("🚚 출하 공정: http://localhost:8002/process/shipping")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)