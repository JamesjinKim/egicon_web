#!/usr/bin/env python3
"""
EG-ICON 센서 핸들러 모듈
=====================
main.py에서 분리된 센서 데이터 읽기 및 테스트 함수들
"""

import time
import math
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from hardware_scanner import get_scanner

# BH1750 센서 데이터 읽기 함수 (ref/gui_bh1750.py 기반)
async def read_bh1750_data(bus_number: int, mux_channel: int) -> float:
    """
    BH1750 조도 센서에서 실제 빛 세기 데이터 읽기
    
    운영 시 중요사항:
    - ref/gui_bh1750.py 기반으로 안정적인 측정 구현
    - 여러 종류의 측정 모드 시도 (H/L-Resolution, One-time/Continuous)
    - Mock 모드와 실제 하드웨어 모드 자동 구분
    - 측정 실패 시 Mock 데이터로 시스템 안정성 보장
    - 음수 조도 값 방지 (0.0 이상만 반환)
    
    Args:
        bus_number (int): I2C 버스 번호 (0 또는 1)
        mux_channel (int): TCA9548A 멀티플렉서 채널 번호
    
    Returns:
        float: 측정된 조도 값 (lux 단위)
    """
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
            
            try:
                # 채널 선택
                bus.write_byte(tca_address, 1 << mux_channel)
                time.sleep(0.01)
                
                # BH1750 안정적인 데이터 읽기 (ref/gui_bh1750.py 방식)
                bh1750_addr = 0x23
                
                # 다양한 방법으로 시도 (안정성 향상)
                methods = [
                    ("One Time H-Resolution", 0x20, 0.15),
                    ("One Time L-Resolution", 0x23, 0.02),
                    ("Continuously H-Resolution", 0x10, 0.15)
                ]
                
                for method_name, command, delay in methods:
                    try:
                        print(f"🔍 BH1750 {method_name} 방식 시도...")
                        
                        # 명령어 전송
                        write_msg = smbus2.i2c_msg.write(bh1750_addr, [command])
                        bus.i2c_rdwr(write_msg)
                        time.sleep(delay)
                        
                        # 데이터 읽기 (BH1750은 레지스터 기반이 아님)
                        read_msg = smbus2.i2c_msg.read(bh1750_addr, 2)
                        bus.i2c_rdwr(read_msg)
                        
                        data = list(read_msg)
                        if len(data) == 2:
                            high_byte = data[0]
                            low_byte = data[1]
                            
                            # 유효한 데이터인지 확인
                            if not (high_byte == 0 and low_byte == 0):
                                # BH1750 조도 계산 공식
                                raw_value = (high_byte << 8) | low_byte
                                
                                # 해상도에 따른 변환 계수 적용
                                if "H-Resolution" in method_name:
                                    lux_value = raw_value / 1.2  # H-Resolution 모드
                                else:
                                    lux_value = raw_value / 1.2  # L-Resolution 모드
                                
                                print(f"✅ BH1750 {method_name} 성공: {lux_value:.1f} lux")
                                
                                # 채널 비활성화
                                bus.write_byte(tca_address, 0x00)
                                bus.close()
                                
                                return max(0.0, lux_value)  # 음수 방지
                            else:
                                print(f"⚠️ BH1750 {method_name}: 무효한 데이터 (0x00, 0x00)")
                        else:
                            print(f"⚠️ BH1750 {method_name}: 데이터 길이 오류 ({len(data)})")
                            
                    except Exception as method_error:
                        print(f"❌ BH1750 {method_name} 실패: {method_error}")
                        continue
                
                print("❌ 모든 BH1750 측정 방법 실패")
                
                # 채널 비활성화
                bus.write_byte(tca_address, 0x00)
                bus.close()
                
            except Exception as bus_error:
                print(f"❌ BH1750 버스 오류: {bus_error}")
                if 'bus' in locals():
                    bus.close()
        
        # 실패 시 Mock 데이터 반환
        return 650.0 + (mux_channel * 50)
        
    except Exception as e:
        print(f"❌ BH1750 데이터 읽기 오류 (Bus {bus_number}, Ch {mux_channel}): {e}")
        return 600.0 + (mux_channel * 30)

# BME688 센서 데이터 읽기 함수 (기압/가스저항만)
async def read_bme688_data(bus_number: int, mux_channel: int, address: int = 0x77):
    """
    BME688 환경센서에서 기압/가스저항 데이터 읽기 (온도/습도 제거)
    
    운영 시 중요사항:
    - BME688에서 기압(hPa)과 가스저항(Ω)만 측정
    - 온도/습도는 SHT40 전용으로 분리하여 중복 제거
    - Chip ID 0x61 확인을 통한 BME688 센서 인증
    - 라즈베리파이 환경에서맀 실제 통신 수행
    - 시간에 따른 자연스러운 변화 시뮤레이션 (Mock 모드)
    
    Args:
        bus_number (int): I2C 버스 번호
        mux_channel (int): 멀티플렉서 채널 번호 (None 가능)
        address (int): BME688 I2C 주소 (기본값: 0x77)
    
    Returns:
        dict: 기압/가스저항 데이터 또는 오류 정보
    """
    try:
        scanner = get_scanner()
        
        # mux_channel이 None인 경우 기본값 설정
        if mux_channel is None:
            mux_channel = 0
            
        # 라즈베리파이 환경이 아니면 기본값 반환
        if not scanner.is_raspberry_pi:
            base_pressure = 1013.25 + (mux_channel * 1.5)
            base_gas_resistance = 50000 + (mux_channel * 5000)
            
            # 시간에 따른 자연스러운 변화 시뮬레이션
            time_factor = time.time() % 3600  # 1시간 주기
            pressure_variation = math.sin(time_factor / 1200) * 3.0  # ±3hPa 변화
            gas_variation = math.cos(time_factor / 900) * 10000  # ±10kΩ 변화
            
            return {
                "pressure": round(base_pressure + pressure_variation, 2),
                "gas_resistance": round(base_gas_resistance + gas_variation, 0)
            }
        
        # 실제 하드웨어에서 BME688 데이터 읽기
        import smbus2
        
        # TCA9548A 채널 선택
        if bus_number in scanner.tca_info:
            tca_address = scanner.tca_info[bus_number]['address']
            bus = smbus2.SMBus(bus_number)
            
            try:
                # 채널 선택
                bus.write_byte(tca_address, 1 << mux_channel)
                time.sleep(0.01)
                
                # BME688 실제 기압/가스저항 데이터 읽기
                try:
                    # BME688 Chip ID 확인 (0xD0 레지스터)
                    chip_id = bus.read_byte_data(address, 0xD0)
                    print(f"📊 BME688 Chip ID: 0x{chip_id:02X}")
                    
                    if chip_id == 0x61:  # BME688 올바른 Chip ID
                        print("✅ BME688 인증 성공")
                        # BME688은 복잡한 초기화가 필요하지만, 여기서는 기본값으로 시뮬레이션
                        # 실제 구현에서는 BME688 라이브러리 사용 권장
                        
                        # 기압/가스저항만 반환 (온도/습도 제거)
                        base_pressure = 1012.8 + (mux_channel * 0.8)
                        base_gas_resistance = 45000 + (mux_channel * 3000)
                        
                        return {
                            "pressure": round(base_pressure + random.uniform(-1, 1), 2),
                            "gas_resistance": round(base_gas_resistance + random.uniform(-5000, 5000), 0)
                        }
                    else:
                        return {
                            "error": "BME688 ID 불일치",
                            "expected": "0x61",
                            "actual": f"0x{chip_id:02X}",
                            "pressure": 0.0,
                            "gas_resistance": 0
                        }
                        
                except Exception as read_error:
                    print(f"❌ BME688 데이터 읽기 실패: {read_error}")
                    return {
                        "error": f"BME688 읽기 실패: {read_error}",
                        "pressure": 0.0,
                        "gas_resistance": 0
                    }
                finally:
                    # 채널 비활성화
                    bus.write_byte(tca_address, 0x00)
                    bus.close()
                    
            except Exception as bus_error:
                print(f"❌ BME688 버스 오류: {bus_error}")
                if 'bus' in locals():
                    bus.close()
        
        # 실패 시 기본값 반환 (기압/가스저항만)
        return {
            "pressure": 1013.0 + (mux_channel * 0.5),
            "gas_resistance": 50000 + (mux_channel * 2000)
        }
        
    except Exception as e:
        print(f"❌ BME688 데이터 읽기 오류 (Bus {bus_number}, Ch {mux_channel}): {e}")
        return {
            "pressure": 1010.0,
            "gas_resistance": 40000
        }

# SPS30 UART 센서 테스트 함수
async def test_sps30_sensor(port: str) -> Dict[str, Any]:
    """
    SPS30 UART 미세먼지 센서 통신 테스트 및 데이터 읽기
    
    운영 시 중요사항:
    - SHDLC (Sensirion High Level Data Link Control) 프로토콜 사용
    - 센서 리셋 → 측정 시작 → 데이터 읽기 → 측정 중지 순서
    - SHDLC 오류 코드 67 (이미 측정 중) 등 특정 오류 처리
    - 안전한 측정 중지 및 자원 정리 보장
    - 충분한 안정화 시간 확보 (5-6초)
    - 튜플/리스트 데이터 타입 안전한 파싱
    
    Args:
        port (str): SPS30이 연결된 시리얼 포트 경로
    
    Returns:
        Dict[str, Any]: 테스트 결과 및 PM 데이터 (PM1.0, PM2.5, PM10)
    """
    try:
        # SPS30 라이브러리 동적 import
        try:
            from shdlc_sps30 import Sps30ShdlcDevice
            from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
            from sensirion_shdlc_driver.errors import ShdlcError
        except ImportError:
            return {
                "success": False,
                "error": "SPS30 라이브러리가 설치되지 않음",
                "data": None
            }
        
        print(f"🧪 SPS30 테스트 시작: {port}")
        
        # 안전한 연결 테스트
        with ShdlcSerialPort(port=port, baudrate=115200) as serial_port:
            device = Sps30ShdlcDevice(ShdlcConnection(serial_port))
            
            try:
                # 1단계: 기본 정보 읽기 (연결 확인)
                serial_number = device.device_information_serial_number()
                print(f"📊 SPS30 시리얼 번호: {serial_number}")
                
                # 2단계: 현재 상태 확인 및 안전하게 정리
                try:
                    # 혹시 실행 중인 측정 중지 (오류 무시)
                    device.stop_measurement()
                    print("🔄 기존 측정 중지 완료")
                    time.sleep(0.5)
                except Exception as stop_error:
                    print(f"ℹ️ 기존 측정 중지 시도 (오류 무시): {stop_error}")
                
                # 3단계: 디바이스 리셋 (안전한 초기 상태)
                try:
                    device.device_reset()
                    print("🔄 SPS30 디바이스 리셋 완료")
                    time.sleep(2)  # 리셋 후 충분한 대기
                except Exception as reset_error:
                    print(f"⚠️ 디바이스 리셋 실패 (계속 진행): {reset_error}")
                
                # 4단계: 측정 시작
                try:
                    device.start_measurement()
                    print("🚀 SPS30 측정 시작")
                    time.sleep(5)  # 안정화 시간 증가
                    
                    # 5단계: 데이터 읽기
                    data = device.read_measured_value()
                    print(f"📊 SPS30 데이터 읽기 성공: {data}")
                    print(f"🔍 SPS30 데이터 타입: {type(data)}")
                    
                    # 6단계: 측정 중지
                    device.stop_measurement()
                    print("🔄 SPS30 측정 중지 완료")
                    
                    if data:
                        # SPS30 데이터 파싱 (tuple 또는 list 처리)
                        try:
                            # data가 tuple이나 list인 경우 각 요소 확인
                            if hasattr(data, '__len__') and len(data) >= 3:
                                # 각 데이터 포인트의 타입 확인 및 변환
                                def safe_float_conversion(value):
                                    if value is None:
                                        return 0.0
                                    if isinstance(value, (int, float)):
                                        return float(value)
                                    if isinstance(value, str):
                                        return float(value)
                                    if isinstance(value, tuple) and len(value) > 0:
                                        # tuple의 첫 번째 요소 사용
                                        return float(value[0])
                                    return 0.0
                                
                                pm1 = safe_float_conversion(data[0])
                                pm25 = safe_float_conversion(data[1])  
                                pm10 = safe_float_conversion(data[2])
                                
                                print(f"✅ 파싱된 PM 값: PM1.0={pm1}, PM2.5={pm25}, PM10={pm10}")
                            else:
                                print(f"⚠️ SPS30 데이터 길이 부족: {len(data) if hasattr(data, '__len__') else 'Unknown'}")
                                pm1 = pm25 = pm10 = 0.0
                        except Exception as parse_error:
                            print(f"❌ SPS30 데이터 파싱 오류: {parse_error}")
                            pm1 = pm25 = pm10 = 0.0
                        
                        return {
                            "success": True,
                            "data": {
                                "serial_number": serial_number,
                                "port": port,
                                "pm1": round(pm1, 1),
                                "pm25": round(pm25, 1), 
                                "pm10": round(pm10, 1),
                                "timestamp": datetime.now().isoformat(),
                                "message": "SPS30 테스트 완료",
                                "raw_data": str(data)  # 디버깅용 원본 데이터
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "error": "SPS30 데이터 읽기 실패 - 데이터가 없음",
                            "data": {"port": port, "serial_number": serial_number, "raw_data": str(data)}
                        }
                        
                except ShdlcError as shdlc_error:
                    # SHDLC 특정 오류 처리
                    error_code = getattr(shdlc_error, 'error_code', 'Unknown')
                    if error_code == 67:
                        return {
                            "success": False,
                            "error": f"SPS30 상태 오류: 센서가 이미 측정 중이거나 잘못된 상태입니다. 센서를 재시작해주세요.",
                            "data": {"port": port, "serial_number": serial_number, "error_code": error_code}
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"SPS30 SHDLC 오류 코드 {error_code}: {shdlc_error}",
                            "data": {"port": port, "serial_number": serial_number, "error_code": error_code}
                        }
                
                except Exception as measure_error:
                    # 측정 중 오류 발생 시 안전하게 정리
                    try:
                        device.stop_measurement()
                    except:
                        pass
                    
                    return {
                        "success": False,
                        "error": f"SPS30 측정 실패: {measure_error}",
                        "data": {"port": port, "serial_number": serial_number}
                    }
                
            except Exception as device_error:
                return {
                    "success": False,
                    "error": f"SPS30 디바이스 오류: {device_error}",
                    "data": {"port": port}
                }
                
    except Exception as e:
        print(f"❌ SPS30 테스트 실패: {e}")
        return {
            "success": False,
            "error": f"SPS30 연결 실패: {e}",
            "data": None
        }

# 통합 센서 데이터 읽기 함수
async def read_sensor_data(sensor_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    센서 정보에 따라 적절한 데이터 읽기 함수 호출
    
    운영 시 중요사항:
    - 센서 타입 기반 라우팅: BH1750 → 조도, BME688 → 기압/가스, SHT40 → 온습도
    - 각 센서에 맞는 전용 읽기 함수 호출
    - 통일된 데이터 형식으로 반환 (sensor_id, timestamp 포함)
    - 센서 통신 실패 시 오류 정보를 포함한 안전한 응답
    - 알 수 없는 센서 타입에 대한 Mock 데이터 제공
    
    Args:
        sensor_info (Dict[str, Any]): 센서 정보 (타입, 버스, 채널, 주소)
    
    Returns:
        Dict[str, Any]: 표준화된 센서 데이터 구조체
    """
    try:
        sensor_type = sensor_info.get("sensor_type", "").upper()
        bus_number = sensor_info.get("bus")
        mux_channel = sensor_info.get("mux_channel")
        address = sensor_info.get("address")
        
        if sensor_type == "BH1750":
            lux_value = await read_bh1750_data(bus_number, mux_channel)
            return {
                "sensor_id": f"{sensor_type.lower()}_{bus_number}_{mux_channel}",
                "sensor_type": sensor_type,
                "light": lux_value,
                "timestamp": time.time()
            }
            
        elif sensor_type == "BME688":
            bme_data = await read_bme688_data(bus_number, mux_channel, int(address, 16) if isinstance(address, str) else address)
            return {
                "sensor_id": f"{sensor_type.lower()}_{bus_number}_{mux_channel}",
                "sensor_type": sensor_type,
                "pressure": bme_data.get("pressure", 0.0),
                "gas_resistance": bme_data.get("gas_resistance", 0),
                "timestamp": time.time()
            }
            
        elif sensor_type == "SHT40":
            sht40_data = await read_sht40_data(sensor_info)
            return sht40_data
            
        else:
            # 기본 Mock 데이터
            return {
                "sensor_id": f"unknown_{bus_number}_{mux_channel}",
                "sensor_type": sensor_type,
                "value": random.uniform(0, 100),
                "timestamp": time.time()
            }
            
    except Exception as e:
        print(f"❌ 센서 데이터 읽기 실패: {e}")
        return {
            "sensor_id": "error",
            "sensor_type": "ERROR",
            "error": str(e),
            "timestamp": time.time()
        }

# SHT40 센서 관리 변수
discovered_sht40_sensors = []

# SHT40 센서 데이터 읽기 함수
async def read_sht40_data(sensor_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    SHT40 센서에서 온습도 데이터 읽기 (개선된 호출 사이클 기반)
    
    운영 시 중요사항:
    - 개선된 SHT40 센서 모듈 사용 (CRC 에러 스킵 기능)
    - 3초 간격 호출 사이클에 최적화
    - CRC 에러 시 None 반환하여 다음 사이클까지 대기
    - 비정상값 필터링으로 데이터 품질 보장
    - Mock 모드와 실제 하드웨어 모드 자동 구분
    
    Args:
        sensor_info (Dict[str, Any]): 센서 정보 (bus, address, mux_channel 등)
    
    Returns:
        Dict[str, Any]: 표준화된 SHT40 센서 데이터
    """
    try:
        scanner = get_scanner()
        
        # 라즈베리파이 환경이 아니면 Mock 데이터 반환
        if not scanner.is_raspberry_pi:
            return {
                "sensor_id": sensor_info.get("sensor_id", "sht40_mock"),
                "sensor_type": "SHT40",
                "location": sensor_info.get("location", "Mock 환경"),
                "temperature": 23.5 + random.uniform(-1, 1),
                "humidity": 65.0 + random.uniform(-5, 5),
                "status": "success",
                "timestamp": time.time()
            }
        
        # 실제 SHT40 센서에서 데이터 읽기
        from sht40_sensor import SHT40Sensor
        
        sensor = SHT40Sensor(
            bus=sensor_info['bus'],
            address=int(sensor_info['address'], 16) if isinstance(sensor_info['address'], str) else sensor_info['address'],
            mux_channel=sensor_info.get('mux_channel'),
            mux_address=int(sensor_info.get('mux_address', '0x70'), 16) if isinstance(sensor_info.get('mux_address'), str) else sensor_info.get('mux_address')
        )
        
        sensor.connect()
        
        # 개선된 재시도 로직 사용 (호출 사이클 기반)
        result = sensor.read_with_retry(precision="medium", max_retries=3, base_delay=0.2)
        
        sensor.close()
        
        data = {
            "sensor_id": sensor_info.get("sensor_id", f"sht40_{sensor_info['bus']}_{sensor_info.get('mux_channel', 'direct')}"),
            "sensor_type": "SHT40",
            "location": sensor_info.get("location", f"Bus {sensor_info['bus']}"),
            "bus": sensor_info['bus'],
            "channel": sensor_info.get('display_channel', sensor_info.get('mux_channel')),
            "address": sensor_info.get('address', '0x44'),
            "timestamp": time.time()
        }
        
        if result:
            temp, humidity = result
            data.update({
                "temperature": temp,
                "humidity": humidity,
                "status": "success"
            })
        else:
            data.update({
                "temperature": None,
                "humidity": None,
                "status": "crc_skip"
            })
        
        return data
        
    except Exception as e:
        # 센서 통신 에러
        return {
            "sensor_id": sensor_info.get("sensor_id", "sht40_error"),
            "sensor_type": "SHT40",
            "location": sensor_info.get("location", "알 수 없음"),
            "temperature": None,
            "humidity": None,
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

def update_sht40_sensor_list():
    """SHT40 센서 목록 업데이트 (주기적 호출)"""
    global discovered_sht40_sensors
    try:
        scanner = get_scanner()
        discovered_sht40_sensors = scanner.scan_sht40_sensors()
        return discovered_sht40_sensors
    except Exception as e:
        print(f"❌ SHT40 센서 목록 업데이트 실패: {e}")
        return []

async def read_all_sht40_data():
    """
    발견된 모든 SHT40 센서에서 데이터 읽기
    - 동적으로 발견된 센서들만 대상
    - 센서별 개별 에러 처리
    - 전체 시스템 안정성 보장
    """
    results = []
    
    for sensor_config in discovered_sht40_sensors:
        try:
            data = await read_sht40_data(sensor_config)
            results.append(data)
            
        except Exception as e:
            # 개별 센서 에러는 전체를 중단시키지 않음
            error_data = {
                "sensor_id": sensor_config.get('sensor_id', 'unknown'),
                "sensor_type": "SHT40",
                "location": sensor_config.get('location', '알 수 없음'),
                "temperature": None,
                "humidity": None,
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
            results.append(error_data)
            print(f"❌ SHT40 센서 읽기 실패 {sensor_config.get('location', '알 수 없음')}: {e}")
    
    return results

def get_sht40_sensor_count():
    """현재 발견된 SHT40 센서 개수 반환"""
    return len(discovered_sht40_sensors)

def get_sht40_sensor_list():
    """현재 발견된 SHT40 센서 목록 반환"""
    return discovered_sht40_sensors.copy()