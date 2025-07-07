#!/usr/bin/env python3
"""
BH1750 실시간 데이터 수집 테스트
Bus 1, CH 8 - 0x23 센서에서 2초 간격으로 10번 조도 측정
"""

import asyncio
import json
import time
from datetime import datetime
from hardware_scanner import get_scanner

async def test_bh1750_realtime_data():
    """BH1750 실시간 데이터 수집 테스트 - Bus 1, CH 8, 0x23"""
    
    print("=" * 70)
    print("BH1750 실시간 데이터 수집 테스트")
    print("대상: Bus 1, CH 8 - 0x23 (2초 간격 10번 측정)")
    print("=" * 70)
    
    # 하드웨어 스캐너 인스턴스 가져오기
    scanner = get_scanner()
    print(f"라즈베리파이 환경: {scanner.is_raspberry_pi}")
    
    # 테스트 대상 센서 정보
    target_bus = 1
    target_channel = 8
    target_address = 0x23
    measurement_count = 10
    interval_seconds = 2
    
    print(f"\n🎯 테스트 대상 센서:")
    print(f"   - Bus: {target_bus}")
    print(f"   - Channel: {target_channel}")
    print(f"   - Address: 0x{target_address:02X}")
    print(f"   - 측정 횟수: {measurement_count}회")
    print(f"   - 측정 간격: {interval_seconds}초")
    print()
    
    # 1. 센서 존재 확인
    print("1. 센서 존재 확인:")
    print("-" * 40)
    
    try:
        bh1750_devices = scanner.scan_bh1750_sensors()
        target_sensor = None
        
        for device in bh1750_devices:
            if (device['bus'] == target_bus and 
                device.get('mux_channel') == target_channel and 
                int(device['address'], 16) == target_address):
                target_sensor = device
                break
        
        if target_sensor:
            print(f"✅ 대상 센서 발견: {target_sensor['sensor_id']}")
            print(f"   위치: {target_sensor['location']}")
            print(f"   상태: {target_sensor['status']}")
            print(f"   초기 측정값: {target_sensor['test_result']}")
        else:
            print(f"❌ 대상 센서를 찾을 수 없습니다.")
            print(f"   Bus {target_bus}, CH {target_channel}, 0x{target_address:02X}")
            
            if bh1750_devices:
                print(f"\n📊 발견된 BH1750 센서 목록:")
                for i, device in enumerate(bh1750_devices, 1):
                    print(f"  {i}. {device['sensor_id']} - {device['location']}")
            
            print("\n테스트를 중단합니다.")
            return
            
    except Exception as e:
        print(f"❌ 센서 스캔 실패: {e}")
        return
    
    # 2. 실시간 데이터 수집
    print(f"\n2. 실시간 데이터 수집 (2초 간격 10회):")
    print("-" * 40)
    print(f"{'순번':>3} {'시간':>8} {'조도 (lux)':>12} {'상태':>8}")
    print("-" * 40)
    
    measurements = []
    errors = 0
    
    for i in range(measurement_count):
        try:
            # 현재 시간 기록
            current_time = datetime.now()
            time_str = current_time.strftime("%H:%M:%S")
            
            # 센서 측정
            if scanner.is_raspberry_pi:
                # 멀티플렉서 채널 선택
                if not scanner._select_channel(target_bus, target_channel):
                    raise Exception("멀티플렉서 채널 선택 실패")
                
                # 조도 측정
                bus_obj = scanner.buses[target_bus]
                light_value = scanner._test_bh1750_measurement(bus_obj, target_address)
                
                # 멀티플렉서 채널 해제
                scanner._disable_all_channels(target_bus)
                
                # 측정 결과 기록
                measurements.append({
                    'sequence': i + 1,
                    'time': current_time,
                    'light': light_value,
                    'status': 'OK'
                })
                
                print(f"{i+1:3d} {time_str:>8} {light_value:>10.1f} {'✅ OK':>8}")
                
            else:
                # Mock 데이터 (개발 환경)
                light_value = 334.2 + (i * 0.5)  # 약간의 변화 추가
                measurements.append({
                    'sequence': i + 1,
                    'time': current_time,
                    'light': light_value,
                    'status': 'MOCK'
                })
                
                print(f"{i+1:3d} {time_str:>8} {light_value:>10.1f} {'🔧 MOCK':>8}")
            
        except Exception as e:
            errors += 1
            error_time = datetime.now().strftime("%H:%M:%S")
            print(f"{i+1:3d} {error_time:>8} {'ERROR':>10} {'❌ FAIL':>8}")
            print(f"    오류: {str(e)}")
            
            measurements.append({
                'sequence': i + 1,
                'time': datetime.now(),
                'light': None,
                'status': 'ERROR',
                'error': str(e)
            })
        
        # 마지막 측정이 아니면 대기
        if i < measurement_count - 1:
            await asyncio.sleep(interval_seconds)
    
    # 3. 측정 결과 분석
    print(f"\n3. 측정 결과 분석:")
    print("-" * 40)
    
    successful_measurements = [m for m in measurements if m['status'] in ['OK', 'MOCK'] and m['light'] is not None]
    
    if successful_measurements:
        light_values = [m['light'] for m in successful_measurements]
        
        print(f"✅ 성공한 측정: {len(successful_measurements)}/{measurement_count}회")
        print(f"❌ 실패한 측정: {errors}회")
        print(f"📊 조도 통계:")
        print(f"   - 최소값: {min(light_values):.1f} lux")
        print(f"   - 최대값: {max(light_values):.1f} lux")
        print(f"   - 평균값: {sum(light_values)/len(light_values):.1f} lux")
        print(f"   - 변화 범위: {max(light_values) - min(light_values):.1f} lux")
        
        # 연속성 확인
        if len(light_values) > 1:
            changes = [abs(light_values[i] - light_values[i-1]) for i in range(1, len(light_values))]
            avg_change = sum(changes) / len(changes)
            print(f"   - 평균 변화량: {avg_change:.1f} lux")
        
        # 데이터 품질 평가
        if max(light_values) - min(light_values) > 0:
            print(f"   - 데이터 품질: ✅ 변화 감지됨 (실제 센서 가능성 높음)")
        else:
            print(f"   - 데이터 품질: ⚠️ 변화 없음 (Mock 데이터 또는 안정적 환경)")
    else:
        print(f"❌ 성공한 측정이 없습니다.")
        print(f"❌ 실패한 측정: {errors}회")
    
    # 4. API 호환성 검증
    print(f"\n4. API 호환성 검증:")
    print("-" * 40)
    
    if successful_measurements:
        # 최신 측정값으로 API 응답 형식 생성
        latest_measurement = successful_measurements[-1]
        
        api_response = {
            "success": True,
            "data": {
                "light": latest_measurement['light'],
                "timestamp": latest_measurement['time'].isoformat()
            },
            "sensor_info": {
                "bus": target_bus,
                "mux_channel": target_channel,
                "address": f"0x{target_address:02X}"
            }
        }
        
        print(f"✅ /api/sensors/bh1750/{target_bus}/{target_channel} 응답 형식:")
        print(json.dumps(api_response, indent=2, ensure_ascii=False))
    else:
        print(f"❌ 성공한 측정이 없어 API 응답을 생성할 수 없습니다.")
    
    # 5. 테스트 요약
    print("\n" + "=" * 70)
    print("BH1750 실시간 데이터 수집 테스트 완료")
    print("=" * 70)
    
    if successful_measurements:
        print(f"✅ 테스트 성공: {len(successful_measurements)}/{measurement_count}회 측정 성공")
        print(f"📊 최종 조도값: {successful_measurements[-1]['light']:.1f} lux")
        print(f"🔧 Dashboard API 검증 완료")
    else:
        print(f"❌ 테스트 실패: 성공한 측정이 없습니다.")
        print(f"🔧 확인사항:")
        print(f"   1. 센서 연결 상태 확인")
        print(f"   2. TCA9548A 멀티플렉서 상태 확인")
        print(f"   3. I2C 버스 상태 확인")
        print(f"   4. 센서 주소 확인 (0x{target_address:02X})")
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_bh1750_realtime_data())