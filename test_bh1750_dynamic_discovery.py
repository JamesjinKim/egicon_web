#!/usr/bin/env python3
"""
BH1750 동적 센서 발견 테스트
hardware_scanner.py의 새로운 BH1750 동적 스캔 기능 테스트
"""

import asyncio
import json
from hardware_scanner import get_scanner

async def test_bh1750_dynamic_discovery():
    """BH1750 동적 센서 발견 테스트"""
    
    print("=" * 70)
    print("BH1750 동적 센서 발견 테스트")
    print("=" * 70)
    
    # 하드웨어 스캐너 인스턴스 가져오기
    scanner = get_scanner()
    print(f"라즈베리파이 환경: {scanner.is_raspberry_pi}")
    
    # 1. BH1750 전용 동적 스캔
    print("\n1. BH1750 전용 동적 스캔:")
    print("-" * 40)
    
    try:
        bh1750_devices = scanner.scan_bh1750_sensors()
        print(f"\n✅ BH1750 전용 스캔 결과: {len(bh1750_devices)}개 센서 발견")
        
        if bh1750_devices:
            print("\n📊 발견된 BH1750 센서 상세 정보:")
            for i, device in enumerate(bh1750_devices, 1):
                print(f"  {i}. 센서 ID: {device['sensor_id']}")
                print(f"     위치: {device['location']}")
                print(f"     주소: {device['address']}")
                print(f"     측정값: {device['test_result']}")
                if device.get('mux_channel') is not None:
                    print(f"     멀티플렉서: Bus {device['bus']}, CH{device['mux_channel']} (TCA9548A {device['mux_address']})")
                else:
                    print(f"     연결: Bus {device['bus']} 직접 연결")
                print()
        else:
            print("⚠️ 발견된 BH1750 센서가 없습니다.")
            
    except Exception as e:
        print(f"❌ BH1750 전용 스캔 실패: {e}")
    
    # 2. 전체 시스템 스캔 (BH1750 포함)
    print("\n2. 전체 시스템 스캔 (BH1750 통합):")
    print("-" * 40)
    
    try:
        scan_result = scanner.scan_dual_mux_system()
        
        print(f"스캔 성공: {scan_result.get('success', False)}")
        print(f"스캔 모드: {scan_result.get('mode', 'unknown')}")
        print(f"총 센서 개수: {len(scan_result.get('sensors', []))}")
        
        # BH1750 센서만 필터링
        all_sensors = scan_result.get('sensors', [])
        bh1750_sensors_from_scan = [s for s in all_sensors if s.get('sensor_type') == 'BH1750']
        
        print(f"\n🔍 전체 스캔에서 발견된 BH1750 센서: {len(bh1750_sensors_from_scan)}개")
        
        if bh1750_sensors_from_scan:
            for i, sensor in enumerate(bh1750_sensors_from_scan, 1):
                print(f"  {i}. {sensor.get('sensor_id')} - {sensor.get('test_result')}")
        
        # BH1750 전용 결과도 확인
        bh1750_devices_from_scan = scan_result.get('bh1750_devices', [])
        print(f"\n📊 bh1750_devices 배열: {len(bh1750_devices_from_scan)}개")
        
    except Exception as e:
        print(f"❌ 전체 시스템 스캔 실패: {e}")
    
    # 3. API 호환성 테스트 (/api/sensors/groups 형식)
    print("\n3. API 호환성 테스트:")
    print("-" * 40)
    
    try:
        # 스캔 결과를 기반으로 light 그룹 생성
        bh1750_devices = scanner.scan_bh1750_sensors()
        
        # API 응답 형식 생성
        light_group_api = {
            "success": True,
            "groups": {
                "light": {
                    "sensors": [],
                    "count": len(bh1750_devices),
                    "active_count": len(bh1750_devices),
                    "status": "online" if bh1750_devices else "offline",
                    "status_text": f"{len(bh1750_devices)}개 연결됨" if bh1750_devices else "센서 없음",
                    "types_summary": f"BH1750×{len(bh1750_devices)}" if bh1750_devices else "센서 없음"
                }
            }
        }
        
        # 각 센서를 API 형식으로 변환
        for device in bh1750_devices:
            api_sensor = {
                "sensor_type": device["sensor_type"],
                "bus": device["bus"],
                "mux_channel": device.get("mux_channel"),
                "address": int(device["address"], 16),  # 0x23 -> 35
                "sensor_id": device["sensor_id"],
                "status": device["status"],
                "interface": device["interface"],
                "measurements": device["measurements"],
                "units": device["units"]
            }
            light_group_api["groups"]["light"]["sensors"].append(api_sensor)
        
        print("✅ /api/sensors/groups 호환 API 응답:")
        print(json.dumps(light_group_api, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ API 호환성 테스트 실패: {e}")
    
    # 4. 개별 센서 API 엔드포인트 시뮬레이션
    print("\n4. 개별 센서 API 엔드포인트 시뮬레이션:")
    print("-" * 40)
    
    try:
        bh1750_devices = scanner.scan_bh1750_sensors()
        
        if bh1750_devices:
            for device in bh1750_devices:
                bus = device["bus"]
                channel = device.get("mux_channel", "direct")
                
                # 실제 조도 측정
                if scanner.is_raspberry_pi:
                    try:
                        if device.get("mux_channel") is not None:
                            # 멀티플렉서 채널 선택
                            scanner._select_channel(bus, device["mux_channel"])
                        
                        # 조도 측정
                        bus_obj = scanner.buses[bus]
                        address = int(device["address"], 16)
                        light_value = scanner._test_bh1750_measurement(bus_obj, address)
                        
                        if device.get("mux_channel") is not None:
                            scanner._disable_all_channels(bus)
                            
                    except Exception as e:
                        light_value = 0.0
                        print(f"⚠️ 측정 실패: {e}")
                else:
                    # Mock 데이터
                    light_value = 345.0
                
                # API 응답 형식
                api_response = {
                    "success": True,
                    "data": {
                        "light": light_value,
                        "timestamp": "2025-07-07T12:00:00Z"
                    },
                    "sensor_info": {
                        "bus": bus,
                        "mux_channel": device.get("mux_channel"),
                        "address": device["address"]
                    }
                }
                
                endpoint = f"/api/sensors/bh1750/{bus}/{channel}"
                print(f"\n✅ {endpoint}:")
                print(json.dumps(api_response, indent=2, ensure_ascii=False))
        else:
            print("⚠️ 테스트할 BH1750 센서가 없습니다.")
            
    except Exception as e:
        print(f"❌ 개별 센서 API 테스트 실패: {e}")
    
    # 5. 테스트 요약
    print("\n" + "=" * 70)
    print("BH1750 동적 센서 발견 테스트 완료")
    print("=" * 70)
    
    try:
        final_devices = scanner.scan_bh1750_sensors()
        print(f"✅ 최종 발견된 BH1750 센서: {len(final_devices)}개")
        
        if final_devices:
            print("\n📋 센서 목록:")
            for i, device in enumerate(final_devices, 1):
                location_info = ""
                if device.get('mux_channel') is not None:
                    location_info = f"Bus {device['bus']}, CH{device['mux_channel']}"
                else:
                    location_info = f"Bus {device['bus']}, 직접 연결"
                
                print(f"  {i}. {device['sensor_id']}")
                print(f"     위치: {location_info}")
                print(f"     주소: {device['address']}")
                print(f"     상태: {device['status']}")
                print(f"     측정: {device['test_result']}")
        else:
            print("\n⚠️ 동적 발견된 BH1750 센서가 없습니다.")
            print("\n🔧 확인사항:")
            print("   1. BH1750 센서가 올바르게 연결되었는지 확인")
            print("   2. I2C가 활성화되었는지 확인 (sudo raspi-config)")
            print("   3. TCA9548A 멀티플렉서 연결 상태 확인")
            print("   4. sudo i2cdetect -y 1 명령으로 수동 확인")
            
    except Exception as e:
        print(f"❌ 최종 테스트 실패: {e}")
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_bh1750_dynamic_discovery())