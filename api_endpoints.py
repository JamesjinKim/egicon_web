#!/usr/bin/env python3
"""
EG-ICON API 엔드포인트 모듈
========================
main.py에서 분리된 API 라우트들
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from hardware_scanner import get_scanner, reset_scanner
from sensor_handlers import test_sps30_sensor, read_sensor_data

class SensorTestRequest(BaseModel):
    i2c_bus: int
    mux_channel: int
    address: Optional[str] = None

class UARTTestRequest(BaseModel):
    port: str
    sensor_type: str

def setup_api_routes(app: FastAPI):
    """API 라우트 설정"""
    
    # 센서 스캔 관련 엔드포인트
    @app.post("/api/sensors/scan-dual-mux")
    async def scan_dual_mux_system():
        """이중 멀티플렉서 시스템 전체 스캔"""
        try:
            scanner = get_scanner()
            result = scanner.scan_dual_mux_system()
            return result
        except Exception as e:
            print(f"❌ 이중 멀티플렉서 스캔 실패: {e}")
            raise HTTPException(status_code=500, detail=f"스캔 실패: {str(e)}")

    @app.post("/api/sensors/scan-bus/{bus_number}")
    async def scan_single_bus(bus_number: int):
        """단일 버스 스캔"""
        try:
            if bus_number not in [0, 1]:
                raise HTTPException(status_code=400, detail="버스 번호는 0 또는 1이어야 합니다")
            
            scanner = get_scanner()
            result = scanner.scan_single_bus(bus_number)
            return result
        except Exception as e:
            print(f"❌ 버스 {bus_number} 스캔 실패: {e}")
            raise HTTPException(status_code=500, detail=f"버스 스캔 실패: {str(e)}")

    # 센서 테스트 엔드포인트
    @app.post("/api/sensors/test")
    async def test_sensor(request: SensorTestRequest):
        """I2C 센서 테스트"""
        try:
            scanner = get_scanner()
            
            # Mock 모드에서 테스트 결과 시뮬레이션
            if not scanner.is_raspberry_pi:
                mock_data = {
                    "bus": request.i2c_bus,
                    "channel": request.mux_channel,
                    "address": request.address,
                    "sensor_type": "Mock",
                    "test_value": random.uniform(20, 30),
                    "timestamp": datetime.now().isoformat()
                }
                return {"success": True, "data": mock_data}
            
            # 실제 하드웨어 테스트 (구현 필요)
            return {"success": True, "data": {"message": "하드웨어 테스트 구현 필요"}}
            
        except Exception as e:
            print(f"❌ 센서 테스트 실패: {e}")
            return {"success": False, "error": str(e), "data": None}

    @app.post("/api/sensors/test-uart")
    async def test_uart_sensor(request: UARTTestRequest):
        """UART 센서 테스트 (SPS30 등)"""
        try:
            if request.sensor_type.upper() == "SPS30":
                result = await test_sps30_sensor(request.port)
                return result
            else:
                return {
                    "success": False,
                    "error": f"지원되지 않는 UART 센서 타입: {request.sensor_type}",
                    "data": None
                }
        except Exception as e:
            print(f"❌ UART 센서 테스트 실패: {e}")
            return {"success": False, "error": str(e), "data": None}

    # 센서 상태 및 정보 엔드포인트
    @app.get("/api/sensors/status")
    async def get_sensor_status():
        """센서 상태 정보 반환"""
        try:
            scanner = get_scanner()
            
            # 최신 스캔 수행
            scan_result = scanner.scan_dual_mux_system()
            
            status = {
                "timestamp": datetime.now().isoformat(),
                "mode": scan_result.get("mode", "unknown"),
                "total_sensors": len(scan_result.get("sensors", [])),
                "i2c_sensors": len(scan_result.get("i2c_devices", [])),
                "uart_sensors": len(scan_result.get("uart_devices", [])),
                "buses": scan_result.get("buses", {}),
                "success": scan_result.get("success", False)
            }
            
            return status
            
        except Exception as e:
            print(f"❌ 센서 상태 조회 실패: {e}")
            raise HTTPException(status_code=500, detail=f"상태 조회 실패: {str(e)}")

    @app.get("/api/sensors")
    async def get_sensors():
        """연결된 센서 목록 반환"""
        try:
            scanner = get_scanner()
            scan_result = scanner.scan_dual_mux_system()
            
            sensors = scan_result.get("sensors", [])
            return sensors
            
        except Exception as e:
            print(f"❌ 센서 목록 조회 실패: {e}")
            raise HTTPException(status_code=500, detail=f"센서 목록 조회 실패: {str(e)}")

    # 동적 센서 그룹 엔드포인트
    @app.get("/api/sensors/groups")
    async def get_dynamic_sensor_groups():
        """동적 센서 그룹 정보 반환"""
        try:
            scanner = get_scanner()
            scan_result = scanner.scan_dual_mux_system()
            
            # 센서별 그룹화
            groups = {
                "temp-humidity": {"sensors": [], "count": 0},
                "pressure": {"sensors": [], "count": 0}, 
                "light": {"sensors": [], "count": 0},
                "air-quality": {"sensors": [], "count": 0}
            }
            
            # SPS30 백그라운드 스레드에서 UART 센서 추가
            try:
                from main import get_sps30_thread
                sps30_thread = get_sps30_thread()
                
                if sps30_thread and sps30_thread.is_healthy():
                    sps30_sensor = {
                        "sensor_type": "SPS30",
                        "sensor_name": "SPS30",
                        "interface": "UART",
                        "port": sps30_thread.port_path,
                        "serial_number": sps30_thread.serial_number,
                        "status": "connected"
                    }
                    groups["air-quality"]["sensors"].append(sps30_sensor)
                    
            except Exception as e:
                print(f"⚠️ SPS30 그룹 추가 실패: {e}")
            
            # I2C 센서 그룹화
            for sensor in scan_result.get("sensors", []):
                sensor_type = sensor.get("sensor_type", "").upper()
                
                if sensor_type in ["BME688", "SHT40"]:
                    groups["temp-humidity"]["sensors"].append(sensor)
                    if sensor_type == "BME688":
                        groups["pressure"]["sensors"].append(sensor)
                elif sensor_type == "BH1750":
                    groups["light"]["sensors"].append(sensor)
                elif sensor_type == "SPS30":
                    groups["air-quality"]["sensors"].append(sensor)
            
            # 센서 개수 업데이트
            for group_name, group_data in groups.items():
                group_data["count"] = len(group_data["sensors"])
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "groups": groups
            }
            
        except Exception as e:
            print(f"❌ 동적 센서 그룹 조회 실패: {e}")
            raise HTTPException(status_code=500, detail=f"센서 그룹 조회 실패: {str(e)}")

    # 센서 데이터 읽기 엔드포인트
    @app.get("/api/sensors/data/{sensor_id}")
    async def get_sensor_data(sensor_id: str):
        """특정 센서의 실시간 데이터 읽기"""
        try:
            # 센서 ID 파싱 (예: "bme688_1_0")
            parts = sensor_id.split("_")
            if len(parts) >= 3:
                sensor_type = parts[0].upper()
                bus_number = int(parts[1])
                mux_channel = int(parts[2])
                
                sensor_info = {
                    "sensor_type": sensor_type,
                    "bus": bus_number,
                    "mux_channel": mux_channel,
                    "address": "0x77"  # 기본값
                }
                
                data = await read_sensor_data(sensor_info)
                return {"success": True, "data": data}
            else:
                raise HTTPException(status_code=400, detail="잘못된 센서 ID 형식")
                
        except Exception as e:
            print(f"❌ 센서 데이터 읽기 실패: {e}")
            return {"success": False, "error": str(e), "data": None}

    # 시스템 유틸리티 엔드포인트
    @app.post("/api/system/reset-scanner")
    async def reset_hardware_scanner():
        """하드웨어 스캐너 리셋"""
        try:
            reset_scanner()
            return {"success": True, "message": "스캐너가 리셋되었습니다"}
        except Exception as e:
            print(f"❌ 스캐너 리셋 실패: {e}")
            raise HTTPException(status_code=500, detail=f"스캐너 리셋 실패: {str(e)}")

    return app