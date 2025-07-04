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
from hardware_scanner import get_scanner, cleanup_scanner

# BH1750 센서 데이터 읽기 함수
async def read_bh1750_data(bus_number: int, mux_channel: int) -> float:
    """BH1750 센서에서 실제 조도 데이터 읽기"""
    try:
        scanner = get_scanner()
        
        # 라즈베리파이 환경이 아니면 Mock 데이터 반환
        if not scanner.is_raspberry_pi:
            return 850.0 + (mux_channel * 100) + (time.time() % 100)
        
        # 실제 하드웨어에서 BH1750 데이터 읽기
        import smbus2
        import time
        
        # TCA9548A 채널 선택
        if bus_number in scanner.tca_info:
            tca_address = scanner.tca_info[bus_number]['address']
            bus = smbus2.SMBus(bus_number)
            
            # 채널 선택
            bus.write_byte(tca_address, 1 << mux_channel)
            time.sleep(0.01)
            
            # BH1750에서 데이터 읽기
            try:
                # One Time H-Resolution Mode
                bus.write_byte(0x23, 0x20)
                time.sleep(0.15)  # 150ms 대기
                
                # 데이터 읽기
                data = bus.read_i2c_block_data(0x23, 0x20, 2)
                raw_value = (data[0] << 8) | data[1]
                lux = raw_value / 1.2
                
                # 채널 비활성화
                bus.write_byte(tca_address, 0x00)
                bus.close()
                
                return round(lux, 1) if 0 <= lux <= 65535 else None
                
            except Exception as e:
                # 채널 비활성화 및 정리
                try:
                    bus.write_byte(tca_address, 0x00)
                    bus.close()
                except:
                    pass
                raise e
        
        return None
        
    except Exception as e:
        print(f"BH1750 데이터 읽기 오류 (Bus {bus_number}, Ch {mux_channel}): {e}")
        return None

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

@app.get("/api/sensors/real-status")
async def get_real_sensors_status():
    """실제 연결된 센서들의 상태 및 데이터 조회"""
    try:
        # 하드웨어 스캐너를 통해 실제 센서 스캔
        scanner = get_scanner()
        scan_result = scanner.scan_dual_mux_system()
        
        real_sensors = {}
        
        if scan_result["success"] and scan_result.get("sensors"):
            for sensor in scan_result["sensors"]:
                # BH1750 센서인 경우 실제 데이터 읽기 시도
                if sensor["sensor_type"] == "BH1750":
                    try:
                        # 실제 센서 데이터 읽기 (ref/gui_bh1750.py 로직 활용)
                        real_value = await read_bh1750_data(sensor["bus"], sensor["mux_channel"])
                        
                        sensor_id = f"bh1750_{sensor['bus']}_{sensor['mux_channel']}"
                        real_sensors[sensor_id] = {
                            "id": sensor_id,
                            "name": f"BH1750 조도센서 (Ch{sensor['mux_channel']+1})",
                            "type": "light",
                            "value": real_value if real_value is not None else 0.0,
                            "status": "online" if real_value is not None else "error",
                            "bus": sensor["bus"],
                            "channel": sensor["mux_channel"],
                            "address": sensor["address"],
                            "last_update": datetime.now().isoformat()
                        }
                    except Exception as e:
                        print(f"BH1750 데이터 읽기 실패: {e}")
                        continue
                
                # 다른 센서 타입들도 나중에 추가 가능
                
        return {
            "sensors": real_sensors,
            "system_status": "online",
            "connected_count": len(real_sensors),
            "scan_mode": scan_result.get("mode", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"실제 센서 상태 조회 실패: {e}")
        return {
            "sensors": {},
            "system_status": "error",
            "connected_count": 0,
            "error": str(e),
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
    """통합 센서 검색 (I2C Bus 0 + Bus 1) - 실제 하드웨어 스캔"""
    try:
        print("🔍 통합 센서 스캔 시작...")
        
        # 하드웨어 스캐너 사용
        scanner = get_scanner()
        scan_result = scanner.scan_dual_mux_system()
        
        if scan_result["success"]:
            result = {
                "success": True,
                "mode": scan_result['mode'],
                "i2c_devices": scan_result["i2c_devices"],
                "uart_devices": [],  # UART 디바이스는 별도 처리
                "total_devices": len(scan_result["i2c_devices"]),
                "buses": scan_result["buses"],
                "timestamp": scan_result["timestamp"]
            }
            
            print(f"✅ 통합 센서 스캔 완료: {len(scan_result['i2c_devices'])}개 발견 ({scan_result['mode']} 모드)")
            return result
        else:
            raise Exception(scan_result.get("error", "스캔 실패"))
        
    except Exception as e:
        print(f"❌ 통합 센서 스캔 실패: {e}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/sensors/scan-dual-mux")
async def scan_dual_mux_system():
    """이중 TCA9548A 시스템 전체 스캔 - 실제 하드웨어 스캔"""
    try:
        print("🔍 이중 멀티플렉서 시스템 스캔 시작...")
        
        # 하드웨어 스캐너 사용
        scanner = get_scanner()
        scan_result = scanner.scan_dual_mux_system()
        
        if scan_result["success"]:
            print(f"✅ 이중 멀티플렉서 스캔 완료: {len(scan_result['sensors'])}개 센서 발견")
            print(f"🔧 모드: {scan_result['mode']}")
            
            # 기존 API 형식에 맞게 변환
            result = {
                "success": True,
                "message": f"이중 멀티플렉서 스캔 완료 ({scan_result['mode']} 모드)",
                "mode": scan_result['mode'],
                "total_buses": 2,
                "total_channels": 16,
                "sensors": scan_result["sensors"],
                "i2c_devices": scan_result["i2c_devices"],
                "buses": scan_result["buses"],
                "bus_0_count": len([s for s in scan_result["sensors"] if s["bus"] == 0]),
                "bus_1_count": len([s for s in scan_result["sensors"] if s["bus"] == 1]),
                "timestamp": scan_result["timestamp"]
            }
            return result
        else:
            raise Exception(scan_result.get("error", "스캔 실패"))
        
    except Exception as e:
        print(f"❌ 이중 멀티플렉서 스캔 실패: {e}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/sensors/scan-bus/{bus_number}")
async def scan_single_bus(bus_number: int):
    """단일 I2C 버스 스캔 - 실제 하드웨어 스캔"""
    try:
        print(f"🔍 Bus {bus_number} 스캔 시작...")
        
        if bus_number not in [0, 1]:
            raise ValueError("지원되지 않는 버스 번호입니다. (0 또는 1만 지원)")
        
        # 하드웨어 스캐너 사용
        scanner = get_scanner()
        scan_result = scanner.scan_single_bus(bus_number)
        
        if scan_result["success"]:
            # 디버깅을 위한 스캔 결과 출력
            print(f"🔍 Bus {bus_number} 스캔 결과:", scan_result)
            
            # 버스별 센서 데이터 추출
            bus_data = scan_result["buses"].get(str(bus_number), {})
            print(f"📊 Bus {bus_number} 데이터:", bus_data)
            detected_sensors = []
            
            # TCA9548A 채널별 센서 추출
            if "channels" in bus_data:
                for channel_num, channel_sensors in bus_data["channels"].items():
                    if channel_sensors:
                        for sensor in channel_sensors:
                            sensor_info = {
                                "bus": bus_number,
                                "mux_channel": int(channel_num),
                                "address": sensor["address"],
                                "sensor_name": sensor.get("sensor_name", sensor.get("sensor_type", "Unknown")),
                                "sensor_type": sensor.get("sensor_type", "Unknown"),
                                "status": "연결됨"
                            }
                            detected_sensors.append(sensor_info)
            
            # 직접 연결된 센서 처리
            elif "direct_devices" in bus_data:
                for i, sensor in enumerate(bus_data["direct_devices"]):
                    sensor_info = {
                        "bus": bus_number,
                        "mux_channel": i,  # 직접 연결된 센서의 경우 인덱스 사용
                        "address": sensor["address"],
                        "sensor_name": sensor.get("sensor_name", sensor.get("sensor_type", "Unknown")),
                        "sensor_type": sensor.get("sensor_type", "Unknown"),
                        "status": "연결됨"
                    }
                    detected_sensors.append(sensor_info)
            
            result = {
                "success": True,
                "bus_number": bus_number,
                "sensors": detected_sensors,
                "sensor_count": len(detected_sensors),
                "mode": scan_result["mode"],
                "timestamp": scan_result["timestamp"]
            }
            
            print(f"✅ Bus {bus_number} 스캔 완료: {len(detected_sensors)}개 센서 발견 ({scan_result['mode']} 모드)")
            return result
        else:
            raise Exception(scan_result.get("error", "버스 스캔 실패"))
        
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
            
            # Mock 센서 데이터 업데이트
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
            
            # 실제 센서 데이터 추가 (BH1750 등)
            try:
                real_sensors_response = await get_real_sensors_status()
                if real_sensors_response.get("sensors"):
                    for sensor_id, sensor_info in real_sensors_response["sensors"].items():
                        # 실제 센서 데이터로 Mock 데이터 덮어쓰기
                        sensor_data[sensor_id] = {
                            "id": sensor_id,
                            "type": sensor_info["type"],
                            "value": round(sensor_info["value"], 2),
                            "status": sensor_info["status"],
                            "timestamp": sensor_info["last_update"]
                        }
                        print(f"📡 실제 센서 데이터 추가: {sensor_id} = {sensor_info['value']}")
            except Exception as e:
                print(f"⚠️ 실제 센서 데이터 수집 실패: {e}")
            
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
    cleanup_scanner()  # 하드웨어 스캐너 정리
    print("🛑 EG-ICON Dashboard 서버 종료됨")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # 안정성을 위해 auto-reload 비활성화
        log_level="info"
    )