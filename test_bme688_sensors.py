#!/usr/bin/env python3
"""
BME688 센서 테스트 스크립트
라즈베리파이에서 실제 BME688 센서 상태 확인
"""

import asyncio
import json
from hardware_scanner import get_scanner
from sensor_handlers import read_bme688_data

async def test_bme688_sensors():
    """BME688 센서 발견 및 데이터 읽기 테스트"""
    
    print("=" * 50)
    print("BME688 센서 테스트 시작")
    print("=" * 50)
    
    # 1. 하드웨어 스캐너로 전체 시스템 스캔
    print("\n1. 전체 시스템 스캔:")
    scanner = get_scanner()
    scan_result = scanner.scan_dual_mux_system()
    
    print(f"스캔 성공: {scan_result.get('success', False)}")
    print(f"총 센서 개수: {len(scan_result.get('sensors', []))}")
    
    # 2. BME688 센서만 필터링
    print("\n2. BME688 센서 필터링:")
    bme688_sensors = []
    for sensor in scan_result.get('sensors', []):
        if sensor.get('sensor_type') == 'BME688':
            bme688_sensors.append(sensor)
            print(f"  - Bus {sensor.get('bus')}, Channel {sensor.get('mux_channel')}, Address {sensor.get('address')}")
    
    print(f"총 BME688 센서 개수: {len(bme688_sensors)}")
    
    # 3. API 그룹 구조 확인
    print("\n3. API 그룹 구조 확인:")
    try:
        # API 엔드포인트 시뮬레이션
        groups = {
            "pressure-gas": {"sensors": [], "count": 0}
        }
        
        for sensor in scan_result.get('sensors', []):
            if sensor.get('sensor_type') == 'BME688':
                groups["pressure-gas"]["sensors"].append(sensor)
        
        groups["pressure-gas"]["count"] = len(groups["pressure-gas"]["sensors"])
        
        print(f"pressure-gas 그룹 BME688 센서 개수: {groups['pressure-gas']['count']}")
        print("pressure-gas 그룹 센서 목록:")
        for i, sensor in enumerate(groups["pressure-gas"]["sensors"]):
            print(f"  {i+1}. Bus {sensor.get('bus')}, Channel {sensor.get('mux_channel')}")
            
    except Exception as e:
        print(f"API 그룹 구조 확인 실패: {e}")
    
    # 4. 개별 BME688 센서 데이터 읽기 테스트
    print("\n4. BME688 센서 데이터 읽기 테스트:")
    for i, sensor in enumerate(bme688_sensors[:3]):  # 처음 3개만 테스트
        bus = sensor.get('bus')
        channel = sensor.get('mux_channel')
        print(f"\n  센서 {i+1}: Bus {bus}, Channel {channel}")
        
        try:
            data = await read_bme688_data(bus, channel, 0x77)
            if 'error' not in data:
                print(f"    ✅ 압력: {data.get('pressure', 'N/A')} hPa")
                print(f"    ✅ 가스저항: {data.get('gas_resistance', 'N/A')} Ω")
            else:
                print(f"    ❌ 에러: {data.get('error')}")
        except Exception as e:
            print(f"    ❌ 예외: {e}")
    
    # 5. 프론트엔드가 기대하는 데이터 구조 생성
    print("\n5. 프론트엔드 예상 데이터 구조:")
    frontend_data = []
    for sensor in bme688_sensors:
        bus = sensor.get('bus')
        channel = sensor.get('mux_channel')
        sensor_id = f"bme688_{bus}_{channel}_77"
        
        try:
            data = await read_bme688_data(bus, channel, 0x77)
            if 'error' not in data:
                frontend_sensor = {
                    "sensorId": sensor_id,
                    "pressure": data.get('pressure'),
                    "gas_resistance": data.get('gas_resistance'),
                    "timestamp": "2025-07-06T12:00:00Z"
                }
                frontend_data.append(frontend_sensor)
        except:
            pass
    
    print(f"프론트엔드 데이터 개수: {len(frontend_data)}")
    for data in frontend_data[:3]:  # 처음 3개만 출력
        print(f"  - {data['sensorId']}: {data['pressure']} hPa, {data['gas_resistance']} Ω")
    
    print("\n" + "=" * 50)
    print("BME688 센서 테스트 완료")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_bme688_sensors())