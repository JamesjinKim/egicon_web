"""
EG-ICON Dashboard - 프로토타입 백엔드
=====================================
egicon_dash 기반 FastAPI 서버
성능 최적화: 메모리 > 실시간성 > 응답속도
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
import time
import math
import random
from datetime import datetime
from typing import Dict, List, Any
import uvicorn

# FastAPI 앱 생성
app = FastAPI(
    title="EG-ICON Dashboard API",
    description="TCA9548A 멀티플렉서 기반 16개 센서 실시간 모니터링",
    version="1.0.0"
)

# 정적 파일 서빙 (프론트엔드)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# CSS, JS 파일 직접 서빙
from fastapi.responses import FileResponse

@app.get("/style.css")
async def serve_css():
    return FileResponse("frontend/style.css", media_type="text/css")

@app.get("/dashboard.js") 
async def serve_js():
    return FileResponse("frontend/dashboard.js", media_type="application/javascript")

@app.get("/settings.js")
async def serve_settings_js():
    return FileResponse("frontend/settings.js", media_type="application/javascript")

@app.get("/settings")
async def get_settings():
    """설정 페이지"""
    try:
        with open("frontend/settings.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>설정 페이지를 찾을 수 없습니다.</h1><p>frontend/settings.html 파일을 확인해주세요.</p>",
            status_code=404
        )

# 센서 설정 (JavaScript와 동일)
SENSOR_TYPES = {
    "temperature": {
        "label": "온도",
        "icon": "🌡️",
        "unit": "°C",
        "color": "#ff6384",
        "min": -10,
        "max": 50
    },
    "humidity": {
        "label": "습도", 
        "icon": "💧",
        "unit": "%",
        "color": "#36a2eb",
        "min": 0,
        "max": 100
    },
    "pressure": {
        "label": "압력",
        "icon": "📏", 
        "unit": "hPa",
        "color": "#4bc0c0",
        "min": 950,
        "max": 1050
    },
    "light": {
        "label": "조도",
        "icon": "☀️",
        "unit": "lux", 
        "color": "#ffce56",
        "min": 0,
        "max": 2000
    },
    "vibration": {
        "label": "진동",
        "icon": "〜",
        "unit": "Hz",
        "color": "#9966ff", 
        "min": 0,
        "max": 100
    },
    "airquality": {
        "label": "공기질",
        "icon": "🍃",
        "unit": "ppm",
        "color": "#00d084",
        "min": 0,
        "max": 500
    }
}

# Mock 센서 생성 (동적 개수)
MOCK_SENSORS = {}
def init_mock_sensors():
    """Mock 센서 초기화 - 각 타입별로 1-3개씩 생성"""
    sensor_counts = {
        "temperature": 3,
        "humidity": 2,
        "pressure": 2,
        "light": 2,
        "vibration": 2,
        "airquality": 1
    }
    
    for sensor_type, count in sensor_counts.items():
        for i in range(count):
            sensor_id = f"{sensor_type}_{i + 1}"
            MOCK_SENSORS[sensor_id] = {
                "id": sensor_id,
                "name": f"{SENSOR_TYPES[sensor_type]['label']} {i + 1}",
                "type": sensor_type,
                "status": "online",
                "last_update": datetime.now().isoformat(),
                "value": 0.0
            }

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket 연결됨. 현재 연결 수: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ WebSocket 연결 해제됨. 현재 연결 수: {len(self.active_connections)}")
        
    async def broadcast(self, message: dict):
        """모든 연결된 클라이언트에 메시지 브로드캐스트"""
        if self.active_connections:
            # 성능 최적화: 배치 전송
            message_json = json.dumps(message, ensure_ascii=False)
            disconnected = []
            
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_json)
                except:
                    disconnected.append(connection)
            
            # 연결 해제된 클라이언트 정리
            for connection in disconnected:
                self.active_connections.remove(connection)

manager = ConnectionManager()

def generate_mock_value(sensor_type: str, timestamp: float) -> float:
    """센서별 Mock 값 생성"""
    time_ms = timestamp * 1000
    
    if sensor_type == "temperature":
        return 20 + 10 * math.sin(time_ms / 60000) + (random.random() - 0.5) * 3
    elif sensor_type == "humidity":
        return 50 + 20 * math.sin(time_ms / 80000 + 1) + (random.random() - 0.5) * 5
    elif sensor_type == "pressure":
        return 1013 + 10 * math.sin(time_ms / 120000 + 2) + (random.random() - 0.5) * 2
    elif sensor_type == "light":
        hour = datetime.now().hour
        daylight = max(0, math.sin((hour - 6) * math.pi / 12))
        return daylight * 1500 + random.random() * 200
    elif sensor_type == "vibration":
        return random.random() * 20 + (random.random() > 0.9 and random.random() * 30 or 0)
    elif sensor_type == "airquality":
        return 100 + 50 * math.sin(time_ms / 180000 + 3) + (random.random() - 0.5) * 20
    else:
        return random.random() * 100

# 루트 경로 - 대시보드 HTML 반환
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """메인 대시보드 페이지"""
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>대시보드를 찾을 수 없습니다.</h1><p>frontend/index.html 파일을 확인해주세요.</p>",
            status_code=404
        )

# API 엔드포인트들
@app.get("/api/sensors/list")
async def get_sensor_list():
    """연결된 센서 목록 조회"""
    return {
        "sensors": list(MOCK_SENSORS.keys()),
        "count": len(MOCK_SENSORS),
        "types": SENSOR_TYPES,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/sensors")
async def get_all_sensors():
    """전체 센서 목록 조회 (설정 페이지용)"""
    # Mock 센서 목록 반환
    sensors = []
    for sensor_id, sensor_data in MOCK_SENSORS.items():
        sensors.append({
            "id": sensor_id,
            "name": sensor_data["name"],
            "type": sensor_data["type"],
            "status": "connected",
            "last_update": sensor_data.get("last_update", datetime.now().isoformat())
        })
    
    return sensors

@app.get("/api/sensors/status")
async def get_sensors_status():
    """모든 센서 상태 조회"""
    now = time.time()
    
    # Mock 데이터 업데이트
    for sensor_id, sensor in MOCK_SENSORS.items():
        sensor_type = sensor["type"]
        sensor["value"] = generate_mock_value(sensor_type, now)
        sensor["last_update"] = datetime.now().isoformat()
    
    return {
        "sensors": MOCK_SENSORS,
        "system_status": "online",
        "connected_count": len(MOCK_SENSORS),
        "total_sensors": 16,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/sensors/{sensor_id}")
async def get_sensor_data(sensor_id: str):
    """특정 센서 데이터 조회"""
    if sensor_id not in MOCK_SENSORS:
        return {"error": "센서를 찾을 수 없습니다", "sensor_id": sensor_id}
    
    sensor = MOCK_SENSORS[sensor_id]
    sensor_type = sensor["type"]
    now = time.time()
    
    sensor["value"] = generate_mock_value(sensor_type, now)
    sensor["last_update"] = datetime.now().isoformat()
    
    return sensor

@app.get("/api/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sensors_connected": len(MOCK_SENSORS),
        "websocket_connections": len(manager.active_connections)
    }

# 센서 스캔 관련 API 엔드포인트들
@app.post("/api/sensors/scan-all")
async def scan_all_sensors():
    """통합 센서 검색 (I2C Bus 0 + Bus 1)"""
    try:
        print("🔍 통합 센서 스캔 시작...")
        
        # Mock 데이터로 시뮬레이션 (실제 하드웨어 연결 시 I2C 코드로 교체)
        i2c_devices = []
        
        # Bus 0 Mock 센서들
        bus_0_sensors = [
            {"bus": 0, "mux_channel": 0, "address": "0x44", "sensor_name": "SHT40", "sensor_type": "온습도센서", "status": "연결됨"},
            {"bus": 0, "mux_channel": 1, "address": "0x76", "sensor_name": "BME688", "sensor_type": "환경센서", "status": "연결됨"},
            {"bus": 0, "mux_channel": 2, "address": "0x23", "sensor_name": "BH1750", "sensor_type": "조도센서", "status": "연결됨"},
        ]
        
        # Bus 1 Mock 센서들
        bus_1_sensors = [
            {"bus": 1, "mux_channel": 0, "address": "0x44", "sensor_name": "SHT40", "sensor_type": "온습도센서", "status": "연결됨"},
            {"bus": 1, "mux_channel": 1, "address": "0x76", "sensor_name": "BME688", "sensor_type": "환경센서", "status": "연결됨"},
            {"bus": 1, "mux_channel": 2, "address": "0x23", "sensor_name": "BH1750", "sensor_type": "조도센서", "status": "연결됨"},
        ]
        
        i2c_devices.extend(bus_0_sensors)
        i2c_devices.extend(bus_1_sensors)
        
        result = {
            "success": True,
            "i2c_devices": i2c_devices,
            "uart_devices": [],  # UART 디바이스는 별도 처리
            "total_devices": len(i2c_devices),
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ 통합 센서 스캔 완료: {len(i2c_devices)}개 발견")
        return result
        
    except Exception as e:
        print(f"❌ 통합 센서 스캔 실패: {e}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/sensors/scan-dual-mux")
async def scan_dual_mux_system():
    """이중 TCA9548A 시스템 전체 스캔"""
    try:
        print("🔍 이중 멀티플렉서 시스템 스캔 시작...")
        
        # Mock 데이터로 시뮬레이션
        all_sensors = []
        
        # I2C 버스 0, 1 순차 스캔 시뮬레이션
        for i2c_bus in [0, 1]:
            for mux_channel in range(8):
                # 일부 채널에만 센서가 연결된 것으로 시뮬레이션
                if (i2c_bus == 0 and mux_channel < 3) or (i2c_bus == 1 and mux_channel < 3):
                    sensor_addresses = [0x44, 0x76, 0x23]  # SHT40, BME688, BH1750
                    sensor_names = ["SHT40", "BME688", "BH1750"]
                    sensor_types = ["온습도센서", "환경센서", "조도센서"]
                    
                    addr = sensor_addresses[mux_channel]
                    sensor_info = {
                        "i2c_bus": i2c_bus,
                        "mux_channel": mux_channel,
                        "address": f"0x{addr:02X}",
                        "sensor_name": sensor_names[mux_channel],
                        "sensor_type": sensor_types[mux_channel],
                        "sensor_id": f"bus{i2c_bus}_ch{mux_channel}_{addr:02X}",
                        "status": "연결됨"
                    }
                    all_sensors.append(sensor_info)
        
        result = {
            "success": True,
            "total_buses": 2,
            "total_channels": 16,
            "sensors": all_sensors,
            "bus_0_count": len([s for s in all_sensors if s["i2c_bus"] == 0]),
            "bus_1_count": len([s for s in all_sensors if s["i2c_bus"] == 1]),
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ 이중 멀티플렉서 스캔 완료: {len(all_sensors)}개 센서 발견")
        return result
        
    except Exception as e:
        print(f"❌ 이중 멀티플렉서 스캔 실패: {e}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/sensors/scan-bus/{bus_number}")
async def scan_single_bus(bus_number: int):
    """단일 I2C 버스 스캔"""
    try:
        print(f"🔍 Bus {bus_number} 스캔 시작...")
        
        if bus_number not in [0, 1]:
            raise ValueError("지원되지 않는 버스 번호입니다. (0 또는 1만 지원)")
        
        # Mock 데이터로 시뮬레이션
        detected_sensors = []
        
        for mux_channel in range(8):
            # 일부 채널에만 센서 연결 시뮬레이션
            if mux_channel < 3:  # 0, 1, 2 채널에만 센서 있음
                sensor_addresses = [0x44, 0x76, 0x23]
                sensor_names = ["SHT40", "BME688", "BH1750"]
                sensor_types = ["온습도센서", "환경센서", "조도센서"]
                
                addr = sensor_addresses[mux_channel]
                sensor_info = {
                    "bus": bus_number,
                    "mux_channel": mux_channel,
                    "address": f"0x{addr:02X}",
                    "sensor_name": sensor_names[mux_channel],
                    "sensor_type": sensor_types[mux_channel],
                    "status": "연결됨"
                }
                detected_sensors.append(sensor_info)
        
        result = {
            "success": True,
            "bus_number": bus_number,
            "sensors": detected_sensors,
            "sensor_count": len(detected_sensors),
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ Bus {bus_number} 스캔 완료: {len(detected_sensors)}개 센서 발견")
        return result
        
    except Exception as e:
        print(f"❌ Bus {bus_number} 스캔 실패: {e}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/sensors/test")
async def test_sensor():
    """센서 테스트"""
    try:
        # Mock 테스트 결과
        test_result = {
            "success": True,
            "data": {
                "type": "SHT40",
                "values": {
                    "temperature": 25.6,
                    "humidity": 45.2,
                    "timestamp": datetime.now().isoformat()
                },
                "connection_status": "정상",
                "response_time": "12ms"
            }
        }
        
        print("🧪 센서 테스트 완료")
        return test_result
        
    except Exception as e:
        print(f"❌ 센서 테스트 실패: {e}")
        return {
            "success": False,
            "data": {
                "error": str(e)
            }
        }

@app.get("/api/sensors/status")
async def get_sensor_status():
    """센서 상태 조회"""
    try:
        # Mock 센서 상태 데이터
        sensor_status = {
            "total_sensors": 16,
            "connected_sensors": 6,
            "disconnected_sensors": 10,
            "bus_status": {
                "bus_0": {"status": "connected", "sensor_count": 3},
                "bus_1": {"status": "connected", "sensor_count": 3}
            },
            "last_scan": datetime.now().isoformat(),
            "system_health": "정상"
        }
        
        return sensor_status
        
    except Exception as e:
        print(f"❌ 센서 상태 조회 실패: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# WebSocket 엔드포인트 - 실시간 데이터 스트리밍
@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """실시간 센서 데이터 WebSocket 스트리밍"""
    await manager.connect(websocket)
    
    try:
        while True:
            # 실시간 데이터 생성 및 전송 (2초 간격)
            now = time.time()
            sensor_data = {}
            
            # 배치로 모든 센서 데이터 업데이트 (성능 최적화)
            for sensor_id, sensor in MOCK_SENSORS.items():
                sensor_type = sensor["type"]
                value = generate_mock_value(sensor_type, now)
                
                sensor_data[sensor_id] = {
                    "id": sensor_id,
                    "type": sensor_type,
                    "value": round(value, 2),
                    "status": "online",
                    "timestamp": datetime.now().isoformat()
                }
            
            # 실시간 데이터 브로드캐스트
            await manager.broadcast({
                "type": "sensor_data",
                "data": sensor_data,
                "system_status": "online",
                "timestamp": datetime.now().isoformat()
            })
            
            # 실시간성 보장: 2초 간격
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 오류: {e}")
        manager.disconnect(websocket)

# 백그라운드 작업 - 시스템 상태 모니터링
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기화"""
    init_mock_sensors()
    print("🚀 EG-ICON Dashboard 서버 시작됨")
    print(f"📊 Mock 센서 {len(MOCK_SENSORS)}개 초기화 완료")
    print("🌐 대시보드: http://localhost:8001")
    print("📖 API 문서: http://localhost:8001/docs")

@app.on_event("shutdown") 
async def shutdown_event():
    """애플리케이션 종료 시 정리"""
    print("🛑 EG-ICON Dashboard 서버 종료됨")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # 안정성을 위해 auto-reload 비활성화
        log_level="info"
    )