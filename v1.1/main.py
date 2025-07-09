#!/usr/bin/env python3
"""
EG-ICON Dashboard - 메인 서버
===========================
리팩터링된 FastAPI 서버 (모듈 분리)
성능 최적화: 메모리 > 실시간성 > 응답속도
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime

# 분리된 모듈들 import
from api_endpoints import setup_api_routes
from websocket_manager import setup_websocket_routes
from hardware_scanner import cleanup_scanner

# SPS30 백그라운드 스레드 import
from sps30_background import SPS30BackgroundThread

# 전역 SPS30 백그라운드 스레드 인스턴스
sps30_thread = None

def get_sps30_thread():
    """
    SPS30 백그라운드 스레드 인스턴스 반환
    
    운영 시 중요사항:
    - 전역 변수 sps30_thread의 참조를 반환
    - SPS30 미세먼지 센서의 백그라운드 데이터 수집 스레드 접근용
    - None일 경우 SPS30 센서가 비활성화 상태임을 의미
    
    Returns:
        SPS30BackgroundThread 인스턴스 또는 None
    """
    return sps30_thread

# 라이프사이클 이벤트 핸들러 (FastAPI 최신 방식)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 애플리케이션 라이프사이클 관리
    
    운영 시 중요사항:
    - 서버 시작 시 SPS30 백그라운드 스레드 초기화 및 시작
    - 서버 종료 시 모든 리소스 정리 (스레드, 하드웨어 스캐너)
    - 예외 발생 시에도 안전한 정리 보장
    
    Args:
        app: FastAPI 애플리케이션 인스턴스
    """
    global sps30_thread
    
    # 서버 시작 시 초기화
    print("🚀 EG-ICON Dashboard 서버 시작")
    print("📡 모듈 분리 완료:")
    print("   - sensor_handlers.py: 센서 데이터 읽기")
    print("   - api_endpoints.py: REST API 엔드포인트")  
    print("   - websocket_manager.py: 실시간 WebSocket 통신")
    print("   - hardware_scanner.py: 하드웨어 스캔")
    
    # SPS30 백그라운드 스레드 초기화 및 시작
    print("🌪️ SPS30 백그라운드 스레드 초기화 중...")
    try:
        sps30_thread = SPS30BackgroundThread(update_interval=10)  # 10초 간격
        if sps30_thread.start():
            print("✅ SPS30 백그라운드 스레드 시작됨")
        else:
            print("⚠️ SPS30 백그라운드 스레드 시작 실패 (센서 없음 또는 라이브러리 없음)")
    except Exception as e:
        print(f"❌ SPS30 백그라운드 스레드 초기화 실패: {e}")
        sps30_thread = None
    
    yield
    
    # 서버 종료 시 정리
    print("🛑 EG-ICON Dashboard 서버 종료")
    
    # SPS30 백그라운드 스레드 중지
    if sps30_thread:
        print("🛑 SPS30 백그라운드 스레드 중지 중...")
        sps30_thread.stop()
        print("✅ SPS30 백그라운드 스레드 중지 완료")
    
    cleanup_scanner()

# FastAPI 앱 생성 (lifespan 이벤트 포함)
app = FastAPI(
    title="EG-ICON Dashboard",
    description="TCA9548A 이중 멀티플렉서 센서 모니터링 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# 정적 파일 서빙 (프론트엔드)
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# JS/CSS 파일 직접 서빙을 위한 추가 라우트
@app.get("/dashboard.js")
async def get_dashboard_js():
    """
    dashboard.js 파일 서빙
    
    운영 시 중요사항:
    - 프론트엔드 메인 대시보드 JavaScript 파일 제공
    - 파일이 없으면 404 에러 반환
    - UTF-8 인코딩으로 읽어서 JavaScript MIME 타입으로 응답
    """
    try:
        with open("frontend/dashboard.js", "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="application/javascript")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="dashboard.js not found")

@app.get("/settings.js")
async def get_settings_js():
    """
    settings.js 파일 서빙
    
    운영 시 중요사항:
    - 프론트엔드 설정 페이지 JavaScript 파일 제공
    - 센서 설정 및 시스템 구성 관련 기능 포함
    """
    try:
        with open("frontend/settings.js", "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="application/javascript")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="settings.js not found")

@app.get("/dustsensor.js")
async def get_dustsensor_js():
    """
    dustsensor.js 파일 서빙
    
    운영 시 중요사항:
    - SPS30 미세먼지 센서 전용 페이지 JavaScript 파일 제공
    - PM1.0, PM2.5, PM10 데이터 시각화 및 실시간 모니터링 기능
    """
    try:
        with open("frontend/dustsensor.js", "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="application/javascript")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="dustsensor.js not found")

@app.get("/style.css")
async def get_style_css():
    """
    style.css 파일 서빙
    
    운영 시 중요사항:
    - 전체 웹 애플리케이션의 CSS 스타일 파일 제공
    - 대시보드, 설정, 미세먼지 페이지의 통합 스타일링
    """
    try:
        with open("frontend/style.css", "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="text/css")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="style.css not found")

# 라우트 설정
setup_api_routes(app)
setup_websocket_routes(app)

# 기본 HTML 페이지 라우트
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """
    메인 대시보드 페이지 라우트
    
    운영 시 중요사항:
    - 루트 경로(/)에서 메인 대시보드 HTML 제공
    - 모든 센서 데이터를 실시간으로 표시하는 메인 페이지
    - 파일이 없으면 404 에러 페이지 반환
    """
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)

@app.get("/settings", response_class=HTMLResponse)
async def settings():
    """
    설정 페이지 라우트
    
    운영 시 중요사항:
    - 센서 구성 및 시스템 설정 페이지 제공
    - 하드웨어 스캔, 센서 테스트 기능 포함
    - 시스템 관리자용 인터페이스
    """
    try:
        with open("frontend/settings.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Settings not found</h1>", status_code=404)

@app.get("/dustsensor", response_class=HTMLResponse)
async def dustsensor():
    """
    SPS30 미세먼지 센서 전용 페이지 라우트
    
    운영 시 중요사항:
    - SPS30 센서 데이터 전용 모니터링 페이지
    - PM1.0, PM2.5, PM4.0, PM10 실시간 차트 및 데이터 표시
    - 공기질 지수 표시 및 알림 기능
    """
    try:
        with open("frontend/dustsensor.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dust Sensor page not found</h1>", status_code=404)

# 시스템 정보 엔드포인트
@app.get("/api/system/info")
async def system_info():
    """
    시스템 정보 API 엔드포인트
    
    운영 시 중요사항:
    - 시스템 버전, 모드(하드웨어/개발), 기능 상태 정보 제공
    - SPS30 백그라운드 스레드 상태 포함
    - 클라이언트에서 시스템 상태 확인용으로 사용
    
    Returns:
        dict: 시스템 정보 딕셔너리
    """
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
            "dynamic_sensor_groups": True,
            "sps30_background": sps30_thread is not None
        }
    }

# SPS30 데이터 엔드포인트
@app.get("/api/sensors/sps30/data")
async def get_sps30_data():
    """
    SPS30 센서 현재 데이터 API 엔드포인트
    
    운영 시 중요사항:
    - 백그라운드 스레드에서 수집된 최신 SPS30 데이터 반환
    - 스레드가 없거나 데이터 수집 실패 시 에러 정보 포함
    - 실시간 API 호출에 최적화된 즉시 응답
    
    Returns:
        dict: SPS30 센서 데이터 및 상태 정보
    """
    if not sps30_thread:
        return {
            "success": False,
            "error": "SPS30 백그라운드 스레드가 초기화되지 않음",
            "data": None
        }
    
    try:
        data = sps30_thread.get_current_data()
        return {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

@app.get("/api/sensors/sps30/status")
async def get_sps30_status():
    """
    SPS30 백그라운드 스레드 상태 API 엔드포인트
    
    운영 시 중요사항:
    - SPS30 백그라운드 스레드의 상태 및 건강성 정보 제공
    - 스레드 실행 상태, 연결 상태, 성공률 등 모니터링 정보
    - 시스템 진단 및 문제 해결용으로 활용
    
    Returns:
        dict: SPS30 스레드 상태 정보
    """
    if not sps30_thread:
        return {
            "success": False,
            "error": "SPS30 백그라운드 스레드가 초기화되지 않음",
            "status": None
        }
    
    try:
        status = sps30_thread.get_status()
        return {
            "success": True,
            "status": status,
            "health": sps30_thread.is_healthy(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status": None
        }

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """
    헬스체크 API 엔드포인트
    
    운영 시 중요사항:
    - 서버 정상 작동 여부 확인용 기본 엔드포인트
    - 로드밸런서, 모니터링 시스템에서 사용
    - 항상 성공 응답 반환 (서버가 실행 중임을 의미)
    
    Returns:
        dict: 상태 및 타임스탬프 정보
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# 구 방식의 이벤트 핸들러 제거됨 (lifespan으로 대체)

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