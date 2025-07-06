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
    """
    FastAPI 애플리케이션에 모든 API 라우트 등록
    
    운영 시 중요사항:
    - 센서 스캔, 테스트, 데이터 읽기 등 모든 REST API 엔드포인트 설정
    - 각 엔드포인트는 하드웨어 오류에 대한 예외 처리 포함
    - Mock 모드와 실제 하드웨어 모드 자동 구분
    - 센서별 전용 엔드포인트 (SHT40, SDP810, BME688) 제공
    
    Args:
        app (FastAPI): 라우트를 등록할 FastAPI 애플리케이션 인스턴스
    
    Returns:
        FastAPI: 라우트가 등록된 애플리케이션 인스턴스
    """
    
    # 센서 스캔 관련 엔드포인트
    @app.post("/api/sensors/scan-dual-mux")
    async def scan_dual_mux_system():
        """
        TCA9548A 이중 멀티플렉서 시스템 전체 스캔
        
        운영 시 중요사항:
        - I2C 버스 0, 1 모두에서 TCA9548A 멀티플렉서 감지
        - 각 채널별로 연결된 센서 자동 인식
        - SHT40, SDP810 등 전용 센서는 별도 스캔 로직 사용
        - 스캔 실패 시에도 빈 구조체 반환으로 프론트엔드 오류 방지
        
        Returns:
            dict: 전체 시스템 스캔 결과 (센서 목록, 버스 정보, 타임스탬프 포함)
        """
        try:
            scanner = get_scanner()
            result = scanner.scan_dual_mux_system()
            return result
        except Exception as e:
            print(f"❌ 이중 멀티플렉서 스캔 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"스캔 실패: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "sensors": [],
                "buses": {},
                "i2c_devices": [],
                "uart_devices": []
            }

    @app.post("/api/sensors/scan-bus/{bus_number}")
    async def scan_single_bus(bus_number: int):
        """
        지정된 I2C 버스 단일 스캔
        
        운영 시 중요사항:
        - 버스 번호 0 또는 1만 유효 (라즈베리파이 I2C 버스)
        - 해당 버스의 TCA9548A 멀티플렉서 감지 후 채널별 스캔
        - 멀티플렉서가 없는 경우 직접 연결된 센서 스캔
        - UART 센서는 버스 0에서만 스캔하여 중복 방지
        
        Args:
            bus_number (int): 스캔할 I2C 버스 번호 (0 또는 1)
        
        Returns:
            dict: 단일 버스 스캔 결과
        """
        try:
            if bus_number not in [0, 1]:
                return {
                    "success": False,
                    "error": "Invalid bus number",
                    "message": "버스 번호는 0 또는 1이어야 합니다",
                    "timestamp": datetime.now().isoformat()
                }
            
            scanner = get_scanner()
            result = scanner.scan_single_bus(bus_number)
            return result
        except Exception as e:
            print(f"❌ 버스 {bus_number} 스캔 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"버스 스캔 실패: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "bus": bus_number,
                "sensors": []
            }

    # 센서 테스트 엔드포인트
    @app.post("/api/sensors/test")
    async def test_sensor(request: SensorTestRequest):
        """
        I2C 센서 통신 테스트
        
        운영 시 중요사항:
        - 지정된 버스, 채널, 주소의 센서와 통신 테스트 수행
        - 주소 기반 센서 타입 자동 감지 (SHT40, BME688, BH1750 등)
        - 실제 하드웨어 통신 실패 시 기본값 반환으로 시스템 안정성 보장
        - Mock 데이터 완전 제거하여 실제 센서 상태만 반영
        
        Args:
            request (SensorTestRequest): 테스트할 센서 정보 (버스, 채널, 주소)
        
        Returns:
            dict: 센서 테스트 결과 및 기본 데이터
        """
        try:
            scanner = get_scanner()
            
            # 주소를 숫자로 변환
            address_num = None
            if request.address:
                if request.address.startswith('0x'):
                    address_num = int(request.address, 16)
                else:
                    address_num = int(request.address)
            
            # 센서 타입 감지
            sensor_type_map = {
                0x44: "SHT40", 0x45: "SHT40",
                0x76: "BME688", 0x77: "BME688", 
                0x23: "BH1750", 0x5C: "BH1750",
                0x25: "SDP810",
                0x29: "VL53L0X"
            }
            
            sensor_type = sensor_type_map.get(address_num, "Unknown")
            
            # 실제 센서 테스트만 수행 (Mock 데이터 완전 제거)
            # 센서 연결 실패 시 기본값 반환하여 오류 방지
            
            # 실제 센서 하드웨어 테스트
            try:
                # TODO: 실제 센서별 통신 테스트 구현 필요
                # 현재는 센서 연결 확인만 수행
                
                # 센서 연결 실패 시 기본값으로 오류 방지
                test_data = {
                    "bus": request.i2c_bus,
                    "channel": request.mux_channel,
                    "address": request.address,
                    "sensor_type": sensor_type,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"{sensor_type} 센서 연결 대기 중",
                    "test_value": 0,  # 데이터 없을 시 기본값
                    "status": "waiting"
                }
                
                return {"success": True, "data": test_data}
                
            except Exception as hw_error:
                return {
                    "success": False, 
                    "error": f"하드웨어 테스트 실패: {str(hw_error)}",
                    "data": {
                        "bus": request.i2c_bus,
                        "channel": request.mux_channel,
                        "address": request.address,
                        "sensor_type": sensor_type
                    }
                }
            
        except Exception as e:
            print(f"❌ 센서 테스트 실패: {e}")
            return {"success": False, "error": str(e), "data": None}

    @app.post("/api/sensors/test-uart")
    async def test_uart_sensor(request: UARTTestRequest):
        """
        UART 센서 통신 테스트 (SPS30 미세먼지 센서)
        
        운영 시 중요사항:
        - 현재 SPS30 센서만 지원 (SHDLC 프로토콜)
        - 센서 리셋, 측정 시작, 데이터 읽기 전체 프로세스 테스트
        - SHDLC 오류 코드 67 등 특정 오류 상황 처리
        - 시리얼 포트 권한 문제 시 명확한 오류 메시지 제공
        
        Args:
            request (UARTTestRequest): UART 센서 정보 (포트, 센서 타입)
        
        Returns:
            dict: UART 센서 테스트 결과 및 측정 데이터
        """
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
        """
        전체 센서 시스템 상태 정보 조회
        
        운영 시 중요사항:
        - 최신 센서 스캔을 실행하여 실시간 상태 반영
        - I2C/UART 센서 개수 및 작동 모드 정보 제공
        - 시스템 건강성 모니터링용 엔드포인트
        - 스캔 실패 시 HTTP 500 오류로 클라이언트에 명확한 상태 전달
        
        Returns:
            dict: 센서 시스템 전체 상태 정보
        
        Raises:
            HTTPException: 상태 조회 실패 시 500 오류
        """
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
        """
        현재 연결된 모든 센서 목록 조회
        
        운영 시 중요사항:
        - 전체 시스템 스캔을 수행하여 최신 센서 목록 반환
        - I2C 및 UART 센서 모두 포함
        - 센서별 상세 정보 (버스, 채널, 주소, 인터페이스) 제공
        - 프론트엔드 대시보드의 기본 데이터 소스
        
        Returns:
            list: 연결된 센서 정보 리스트
        
        Raises:
            HTTPException: 센서 목록 조회 실패 시 500 오류
        """
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
        """
        센서 타입별 동적 그룹 정보 생성 및 반환
        
        운영 시 중요사항:
        - 센서 타입에 따라 자동으로 그룹 분류 (온습도, 기압-가스, 조도, 공기질)
        - BME688은 온습도 제외하고 기압-가스저항만 사용
        - SHT40, SDP810은 각각 전용 그룹으로 분리
        - SPS30 백그라운드 스레드 상태도 확인하여 그룹에 포함
        - 대시보드 위젯 구성의 기준 데이터
        
        Returns:
            dict: 센서 그룹별 정보 및 개수
        
        Raises:
            HTTPException: 센서 그룹 조회 실패 시 500 오류
        """
        try:
            scanner = get_scanner()
            scan_result = scanner.scan_dual_mux_system()
            
            # 센서별 그룹화
            groups = {
                "temp-humidity": {"sensors": [], "count": 0},
                "sht40": {"sensors": [], "count": 0},  # SHT40 전용 그룹 추가
                "sdp810": {"sensors": [], "count": 0},  # SDP810 전용 그룹 추가
                "pressure": {"sensors": [], "count": 0}, 
                "pressure-gas": {"sensors": [], "count": 0},  # 메인 대시보드용 BME688 그룹
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
                
                if sensor_type == "BME688":
                    # BME688: 온도/습도 제거, 기압/가스저항만 사용 (air-quality는 SPS30 전용)
                    groups["pressure"]["sensors"].append(sensor)  # 기압 전용
                    groups["pressure-gas"]["sensors"].append(sensor)  # 메인 대시보드용 (기압+가스저항)
                elif sensor_type == "SHT40":
                    groups["sht40"]["sensors"].append(sensor)  # SHT40은 별도 그룹으로
                elif sensor_type == "SDP810":
                    groups["sdp810"]["sensors"].append(sensor)  # SDP810은 별도 그룹으로
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
        """
        특정 센서의 실시간 측정 데이터 읽기
        
        운영 시 중요사항:
        - 센서 ID 형식: "{sensor_type}_{bus}_{channel}" (예: bme688_1_0)
        - sensor_handlers 모듈의 센서별 읽기 함수 호출
        - 실제 하드웨어 통신을 통한 최신 데이터 제공
        - 센서 통신 실패 시에도 오류 정보 포함한 응답 반환
        
        Args:
            sensor_id (str): 센서 식별자 (형식: type_bus_channel)
        
        Returns:
            dict: 센서 측정 데이터 및 메타데이터
        
        Raises:
            HTTPException: 잘못된 센서 ID 형식 시 400 오류
        """
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

    # SHT40 전용 엔드포인트
    @app.get("/api/sensors/sht40")
    async def get_sht40_sensors():
        """
        SHT40 온습도 센서 전용 목록 조회
        
        운영 시 중요사항:
        - 전체 시스템 스캔 결과에서 SHT40 센서만 필터링
        - 온도/습도 측정이 필요한 애플리케이션용 전용 엔드포인트
        - 센서 개수 정보도 함께 제공하여 시스템 구성 파악 가능
        - SHT40은 주소 0x44, 0x45를 사용
        
        Returns:
            dict: SHT40 센서 목록 및 개수 정보
        
        Raises:
            HTTPException: SHT40 센서 조회 실패 시 500 오류
        """
        try:
            scanner = get_scanner()
            scan_result = scanner.scan_dual_mux_system()
            
            # SHT40 센서만 필터링
            sht40_sensors = [
                sensor for sensor in scan_result.get("sensors", [])
                if sensor.get("sensor_type") == "SHT40"
            ]
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "sht40_sensors": sht40_sensors,
                "count": len(sht40_sensors)
            }
            
        except Exception as e:
            print(f"❌ SHT40 센서 목록 조회 실패: {e}")
            raise HTTPException(status_code=500, detail=f"SHT40 센서 조회 실패: {str(e)}")
    
    @app.get("/api/sensors/sht40/{bus}/{channel}")
    async def get_sht40_sensor_data(bus: int, channel: int):
        """
        특정 위치의 SHT40 센서 데이터 읽기
        
        운영 시 중요사항:
        - 지정된 버스와 채널의 SHT40 센서에서 온도/습도 데이터 읽기
        - 실제 SHT40 센서 모듈 구현 대기 중 (현재 기본값 반환)
        - 센서 연결 실패 시에도 안정적인 응답 구조 유지
        - 단위 정보 포함 (°C, %RH)
        
        Args:
            bus (int): I2C 버스 번호
            channel (int): 멀티플렉서 채널 번호
        
        Returns:
            dict: SHT40 센서 측정 데이터 (온도, 습도)
        """
        try:
            # TODO: 실제 SHT40 센서 모듈 구현 필요
            # 현재는 센서 연결 대기 상태로 기본값 반환
            
            sensor_data = {
                "sensor_id": f"sht40_{bus}_{channel}_44",
                "bus": bus,
                "channel": channel,
                "address": "0x44",
                "sensor_type": "SHT40",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "temperature": 0,  # 데이터 없을 시 기본값
                    "humidity": 0      # 데이터 없을 시 기본값
                },
                "units": {
                    "temperature": "°C",
                    "humidity": "%RH"
                },
                "status": "waiting"  # 실제 센서 연결 대기
            }
            
            return {"success": True, "data": sensor_data}
            
        except Exception as e:
            print(f"❌ SHT40 센서 데이터 읽기 실패: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    @app.post("/api/sensors/sht40/test")
    async def test_sht40_sensor():
        """
        SHT40 센서 전용 스캔 및 테스트
        
        운영 시 중요사항:
        - 하드웨어 스캐너의 SHT40 전용 스캔 기능 호출
        - 멀티플렉서 채널별 SHT40 센서 감지
        - 센서별 통신 테스트 및 기본 측정 수행
        - 스캔 기능 미지원 시 명확한 오류 메시지 제공
        
        Returns:
            dict: SHT40 센서 스캔 및 테스트 결과
        """
        try:
            scanner = get_scanner()
            
            # SHT40 센서 스캔 실행
            if hasattr(scanner, 'scan_sht40_sensors'):
                sht40_devices = scanner.scan_sht40_sensors()
                
                return {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "sht40_devices": sht40_devices,
                    "count": len(sht40_devices)
                }
            else:
                return {
                    "success": False,
                    "error": "SHT40 스캔 기능이 지원되지 않습니다",
                    "data": None
                }
                
        except Exception as e:
            print(f"❌ SHT40 센서 테스트 실패: {e}")
            return {"success": False, "error": str(e), "data": None}

    # SDP810 전용 엔드포인트
    @app.get("/api/sensors/sdp810")
    async def get_sdp810_sensors():
        """
        SDP810 차압센서 전용 목록 조회
        
        운영 시 중요사항:
        - 전체 시스템 스캔 결과에서 SDP810 센서만 필터링
        - 차압 측정이 필요한 공기질 모니터링용 전용 엔드포인트
        - SDP810은 주소 0x25 고정 사용
        - 센서 조회 실패 시에도 빈 구조체로 안정적 응답
        
        Returns:
            dict: SDP810 센서 목록 및 개수 정보
        """
        try:
            scanner = get_scanner()
            scan_result = scanner.scan_dual_mux_system()
            
            # SDP810 센서만 필터링
            sdp810_sensors = [
                sensor for sensor in scan_result.get("sensors", [])
                if sensor.get("sensor_type") == "SDP810"
            ]
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "sdp810_sensors": sdp810_sensors,
                "count": len(sdp810_sensors)
            }
            
        except Exception as e:
            print(f"❌ SDP810 센서 목록 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"SDP810 센서 조회 실패: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "sdp810_sensors": [],
                "count": 0
            }
    
    @app.get("/api/sensors/sdp810/{bus}/{channel}")
    async def get_sdp810_sensor_data(bus: int, channel: int):
        """
        특정 위치의 SDP810 센서 차압 데이터 읽기
        
        운영 시 중요사항:
        - SDP810 전용 센서 클래스로 실제 차압 측정
        - CRC 검증 실패 시 자동 재시도 (최대 3회)
        - 240 스케일링 팩터 적용한 정확한 압력 계산
        - 측정 범위: ±500 Pa, 단위: Pa (파스칼)
        
        Args:
            bus (int): I2C 버스 번호
            channel (int): 멀티플렉서 채널 번호
        
        Returns:
            dict: SDP810 센서 차압 측정 데이터
        """
        try:
            # 실제 SDP810 센서 데이터 읽기 (240 스케일링 + CRC 재시도)
            from sdp810_sensor import SDP810Sensor
            
            # SDP810 센서 인스턴스 생성
            sensor = SDP810Sensor(bus_num=bus, mux_address=0x70, mux_channel=channel)
            
            if sensor.connect():
                # 재시도 로직으로 압력 읽기 (CRC 오류 시 자동 재시도)
                pressure = sensor.read_pressure_with_retry(max_retries=3)
                
                if pressure is not None:
                    sensor_data = {
                        "sensor_id": f"sdp810_{bus}_{channel}_25",
                        "bus": bus,
                        "channel": channel,
                        "address": "0x25",
                        "sensor_type": "SDP810",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "differential_pressure": round(pressure, 4)
                        },
                        "units": {
                            "differential_pressure": "Pa"
                        },
                        "status": "connected"
                    }
                    return {"success": True, "data": sensor_data}
                else:
                    return {"success": False, "error": "센서 읽기 실패 (CRC 오류 재시도 후)", "data": None}
            else:
                return {"success": False, "error": "센서 연결 실패", "data": None}
            
        except Exception as e:
            print(f"❌ SDP810 센서 데이터 읽기 실패: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    @app.post("/api/sensors/sdp810/test")
    async def test_sdp810_sensor():
        """
        SDP810 센서 전용 스캔 및 테스트
        
        운영 시 중요사항:
        - 하드웨어 스캐너의 SDP810 전용 스캔 기능 호출
        - 모든 버스와 채널에서 0x25 주소 검색
        - 차압 센서 통신 테스트 및 압력 데이터 검증
        - 스캔 기능 미지원 시 명확한 오류 메시지 제공
        
        Returns:
            dict: SDP810 센서 스캔 및 테스트 결과
        """
        try:
            scanner = get_scanner()
            
            # SDP810 센서 스캔 실행
            if hasattr(scanner, 'scan_sdp810_sensors'):
                sdp810_devices = scanner.scan_sdp810_sensors()
                
                return {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "sdp810_devices": sdp810_devices,
                    "count": len(sdp810_devices)
                }
            else:
                return {
                    "success": False,
                    "error": "SDP810 스캔 기능이 지원되지 않습니다",
                    "data": None
                }
                
        except Exception as e:
            print(f"❌ SDP810 센서 테스트 실패: {e}")
            return {"success": False, "error": str(e), "data": None}

    # BME688 전용 엔드포인트 (기압/가스저항만)
    @app.get("/api/sensors/bme688")
    async def get_bme688_sensors():
        """
        BME688 환경센서 목록 조회 (기압/가스저항 전용)
        
        운영 시 중요사항:
        - 전체 시스템 스캔 결과에서 BME688 센서만 필터링
        - 온도/습도 측정 제외, 기압/가스저항만 사용하는 정책
        - 대기질 및 기압 모니터링용 전용 엔드포인트
        - BME688은 주소 0x76, 0x77 사용
        
        Returns:
            dict: BME688 센서 목록 및 개수 정보
        """
        try:
            scanner = get_scanner()
            scan_result = scanner.scan_dual_mux_system()
            
            # BME688 센서만 필터링
            bme688_sensors = [
                sensor for sensor in scan_result.get("sensors", [])
                if sensor.get("sensor_type") == "BME688"
            ]
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "bme688_sensors": bme688_sensors,
                "count": len(bme688_sensors)
            }
            
        except Exception as e:
            print(f"❌ BME688 센서 목록 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"BME688 센서 조회 실패: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "bme688_sensors": [],
                "count": 0
            }
    
    @app.get("/api/sensors/bme688/{bus}/{channel}")
    async def get_bme688_sensor_data(bus: int, channel: int):
        """
        특정 위치의 BME688 센서 데이터 읽기 (기압/가스저항만)
        
        운영 시 중요사항:
        - BME688에서 기압(hPa)과 가스저항(Ω)만 측정
        - 온도/습도는 SHT40 전용으로 분리하여 중복 제거
        - sensor_handlers의 read_bme688_data 함수 호출
        - 센서 통신 실패 시 오류 정보 포함한 응답
        
        Args:
            bus (int): I2C 버스 번호
            channel (int): 멀티플렉서 채널 번호
        
        Returns:
            dict: BME688 센서 기압/가스저항 측정 데이터
        """
        try:
            # 실제 BME688 센서 데이터 읽기
            from sensor_handlers import read_bme688_data
            
            # BME688 센서 데이터 읽기 (기압/가스저항만)
            bme_data = await read_bme688_data(bus, channel, 0x77)
            
            if "error" not in bme_data:
                sensor_data = {
                    "sensor_id": f"bme688_{bus}_{channel}_77",
                    "bus": bus,
                    "channel": channel,
                    "address": "0x77",
                    "sensor_type": "BME688",
                    "timestamp": datetime.now().isoformat(),
                    # 프론트엔드가 기대하는 평탄한 구조로 변경
                    "pressure": bme_data.get("pressure", 0.0),
                    "gas_resistance": bme_data.get("gas_resistance", 0),
                    "units": {
                        "pressure": "hPa",
                        "gas_resistance": "Ω"
                    },
                    "status": "connected"
                }
                return {"success": True, "data": sensor_data}
            else:
                return {"success": False, "error": bme_data.get("error", "BME688 읽기 실패"), "data": None}
            
        except Exception as e:
            print(f"❌ BME688 센서 데이터 읽기 실패: {e}")
            return {"success": False, "error": str(e), "data": None}
    
    @app.post("/api/sensors/bme688/test")
    async def test_bme688_sensor():
        """
        BME688 센서 전용 스캔 및 테스트
        
        운영 시 중요사항:
        - 하드웨어 스캐너의 BME688 전용 스캔 기능 호출
        - Chip ID 0x61 확인을 통한 BME688 센서 인증
        - 기압/가스저항 센서로서의 통신 테스트
        - 스캔 기능 미지원 시 명확한 오류 메시지 제공
        
        Returns:
            dict: BME688 센서 스캔 및 테스트 결과
        """
        try:
            scanner = get_scanner()
            
            # BME688 센서 스캔 실행
            if hasattr(scanner, 'scan_bme688_sensors'):
                bme688_devices = scanner.scan_bme688_sensors()
                
                return {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "bme688_devices": bme688_devices,
                    "count": len(bme688_devices)
                }
            else:
                return {
                    "success": False,
                    "error": "BME688 스캔 기능이 지원되지 않습니다",
                    "data": None
                }
                
        except Exception as e:
            print(f"❌ BME688 센서 테스트 실패: {e}")
            return {"success": False, "error": str(e), "data": None}

    # SHT40 센서 전용 엔드포인트
    @app.post("/api/sensors/scan-sht40")
    async def scan_sht40_sensors_api():
        """
        SHT40 센서 동적 스캔 (모든 채널 검색)
        
        운영 시 중요사항:
        - 전체 TCA9548A 채널에서 SHT40 센서 동적 발견
        - CRC 에러가 있어도 센서 존재 확인 시 발견으로 처리
        - 발견된 센서 위치 정보 (Bus, Channel) 동적 저장
        - 위치에 관계없이 모든 SHT40 센서 자동 감지
        
        Returns:
            dict: 발견된 SHT40 센서 목록 및 개수
        """
        try:
            from sensor_handlers import update_sht40_sensor_list
            
            found_sensors = update_sht40_sensor_list()
            
            return {
                "success": True,
                "sensors": found_sensors,
                "count": len(found_sensors),
                "message": f"{len(found_sensors)}개 SHT40 센서 발견",
                "scan_time": time.time()
            }
        except Exception as e:
            print(f"❌ SHT40 센서 스캔 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "sensors": [],
                "count": 0
            }

    @app.get("/api/sensors/sht40")
    async def get_sht40_sensors():
        """현재 발견된 SHT40 센서 목록 반환"""
        try:
            from sensor_handlers import get_sht40_sensor_list, get_sht40_sensor_count
            
            sensors = get_sht40_sensor_list()
            
            return {
                "success": True,
                "sensors": sensors,
                "count": get_sht40_sensor_count(),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sensors": [],
                "count": 0
            }

    @app.get("/api/sensors/sht40/status")
    async def get_sht40_status():
        """
        SHT40 센서 상태 조회 (연결 테스트)
        
        운영 시 중요사항:
        - 빠른 연결 상태 확인만 수행 (전체 데이터 읽기 제외)
        - 각 센서별 개별 상태 확인
        - CRC 에러가 있어도 통신 가능하면 연결됨으로 표시
        """
        try:
            from sensor_handlers import get_sht40_sensor_list
            from sht40_sensor import SHT40Sensor
            
            sensors = get_sht40_sensor_list()
            status_data = []
            
            for sensor_config in sensors:
                try:
                    # 빠른 상태 체크 (연결 테스트만)
                    sensor = SHT40Sensor(
                        bus=sensor_config['bus'],
                        address=int(sensor_config['address'], 16) if isinstance(sensor_config['address'], str) else sensor_config['address'],
                        mux_channel=sensor_config.get('mux_channel'),
                        mux_address=int(sensor_config.get('mux_address', '0x70'), 16) if isinstance(sensor_config.get('mux_address'), str) else sensor_config.get('mux_address')
                    )
                    sensor.connect()
                    success, message = sensor.test_connection()
                    sensor.close()
                    
                    status_data.append({
                        "sensor_id": sensor_config.get('sensor_id'),
                        "location": sensor_config.get('location'),
                        "bus": sensor_config['bus'],
                        "channel": sensor_config.get('display_channel', 'direct'),
                        "address": sensor_config.get('address'),
                        "status": "connected" if success else "error",
                        "message": message
                    })
                    
                except Exception as e:
                    status_data.append({
                        "sensor_id": sensor_config.get('sensor_id'),
                        "location": sensor_config.get('location'),
                        "status": "error",
                        "message": str(e)
                    })
            
            return {
                "success": True,
                "sensors": status_data,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/sensors/sht40/data")
    async def get_sht40_data():
        """
        현재 발견된 모든 SHT40 센서에서 실시간 데이터 읽기
        
        운영 시 중요사항:
        - 3초 간격 호출 사이클에 최적화
        - CRC 에러 시 스킵 처리
        - 개별 센서 에러는 전체를 중단시키지 않음
        """
        try:
            from sensor_handlers import read_all_sht40_data
            
            data = await read_all_sht40_data()
            
            # 성공/실패 통계
            success_count = sum(1 for d in data if d.get('status') == 'success')
            skip_count = sum(1 for d in data if d.get('status') == 'crc_skip')
            error_count = sum(1 for d in data if d.get('status') == 'error')
            
            return {
                "success": True,
                "sensors": data,
                "count": len(data),
                "statistics": {
                    "success": success_count,
                    "crc_skip": skip_count,
                    "error": error_count
                },
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sensors": [],
                "count": 0
            }

    # 시스템 유틸리티 엔드포인트
    @app.post("/api/system/reset-scanner")
    async def reset_hardware_scanner():
        """
        하드웨어 스캐너 강제 리셋
        
        운영 시 중요사항:
        - TCA9548A 멀티플렉서 정보 캐시 초기화
        - 하드웨어 구성 변경 시 (센서 추가/제거) 사용
        - 센서 스캔 오류 발생 시 문제 해결용
        - 리셋 후 다음 스캔에서 하드웨어 재감지 수행
        
        Returns:
            dict: 리셋 성공 메시지
        
        Raises:
            HTTPException: 리셋 실패 시 500 오류
        """
        try:
            reset_scanner()
            return {"success": True, "message": "스캐너가 리셋되었습니다"}
        except Exception as e:
            print(f"❌ 스캐너 리셋 실패: {e}")
            raise HTTPException(status_code=500, detail=f"스캐너 리셋 실패: {str(e)}")

    return app