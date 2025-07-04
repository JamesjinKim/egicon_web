#!/usr/bin/env python3
"""
EG-ICON Dashboard - 메인 서버
===========================
리팩터링된 FastAPI 서버 (모듈 분리)
성능 최적화: 메모리 > 실시간성 > 응답속도
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from datetime import datetime

# 분리된 모듈들 import
from api_endpoints import setup_api_routes
from websocket_manager import setup_websocket_routes
from hardware_scanner import cleanup_scanner

# FastAPI 앱 생성
app = FastAPI(
    title="EG-ICON Dashboard",
    description="TCA9548A 이중 멀티플렉서 센서 모니터링 시스템",
    version="1.0.0"
)

# 정적 파일 서빙 (프론트엔드)
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# 라우트 설정
setup_api_routes(app)
setup_websocket_routes(app)

# 기본 HTML 페이지 라우트
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """메인 대시보드 페이지"""
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)

@app.get("/settings", response_class=HTMLResponse)
async def settings():
    """설정 페이지"""
    try:
        with open("frontend/settings.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Settings not found</h1>", status_code=404)

# 시스템 정보 엔드포인트
@app.get("/api/system/info")
async def system_info():
    """시스템 정보 반환"""
    from hardware_scanner import get_scanner
    
    scanner = get_scanner()
    return {
        "system": "EG-ICON Dashboard",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "mode": "hardware" if scanner.is_raspberry_pi else "development",
        "features": {
            "i2c_scanning": True,
            "uart_scanning": True,
            "realtime_websocket": True,
            "dynamic_sensor_groups": True
        }
    }

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """헬스체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# 애플리케이션 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    print("🚀 EG-ICON Dashboard 서버 시작")
    print("📡 모듈 분리 완료:")
    print("   - sensor_handlers.py: 센서 데이터 읽기")
    print("   - api_endpoints.py: REST API 엔드포인트")  
    print("   - websocket_manager.py: 실시간 WebSocket 통신")
    print("   - hardware_scanner.py: 하드웨어 스캔")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 정리"""
    print("🛑 EG-ICON Dashboard 서버 종료")
    cleanup_scanner()

# 개발 서버 실행
if __name__ == "__main__":
    print("🔧 개발 모드로 서버 시작...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )