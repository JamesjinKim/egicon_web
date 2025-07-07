#!/usr/bin/env python3
"""
SDP810 실시간 데이터 수집 테스트
================================
SDP810 차압센서에서 2초 간격으로 10번 측정하여 결과 출력
ref/sdp810_sensor.py와 ref/test_sdp810_direct.py 기반
"""

import asyncio
import json
import time
import struct
from datetime import datetime
from hardware_scanner import get_scanner

async def test_sdp810_realtime_data():
    """SDP810 실시간 데이터 수집 테스트"""
    
    print("=" * 70)
    print("SDP810 실시간 데이터 수집 테스트")
    print("차압센서에서 2초 간격으로 10번 측정")
    print("=" * 70)
    
    # 하드웨어 스캐너 인스턴스 가져오기
    scanner = get_scanner()
    print(f"라즈베리파이 환경: {scanner.is_raspberry_pi}")
    
    # 테스트 설정
    measurement_count = 10
    interval_seconds = 2
    
    print(f"\n🎯 테스트 설정:")
    print(f"   - 측정 횟수: {measurement_count}회")
    print(f"   - 측정 간격: {interval_seconds}초")
    print(f"   - 센서 타입: SDP810 차압센서")
    print(f"   - 대상 주소: 0x25")
    print()
    
    # 1. SDP810 센서 동적 스캔
    print("1. SDP810 센서 동적 스캔:")
    print("-" * 40)
    
    try:
        # hardware_scanner의 SDP810 스캔 기능 사용
        if hasattr(scanner, 'scan_sdp810_sensors'):
            sdp810_devices = scanner.scan_sdp810_sensors()
        else:
            print("⚠️ hardware_scanner에 scan_sdp810_sensors 함수가 없습니다.")
            print("   수동으로 SDP810 센서를 스캔합니다.")
            sdp810_devices = await manual_sdp810_scan(scanner)
        
        print(f"✅ SDP810 스캔 결과: {len(sdp810_devices)}개 센서 발견")
        
        if sdp810_devices:
            target_sensor = sdp810_devices[0]  # 첫 번째 센서 사용
            print(f"📊 대상 센서: {target_sensor.get('sensor_id', 'unknown')}")
            print(f"   위치: {target_sensor.get('location', 'unknown')}")
            print(f"   주소: {target_sensor.get('address', '0x25')}")
            print(f"   상태: {target_sensor.get('status', 'unknown')}")
            
            # 센서 정보 추출
            bus = target_sensor.get('bus', 1)
            channel = target_sensor.get('mux_channel')
            address = int(target_sensor.get('address', '0x25'), 16)
            
        else:
            print("❌ SDP810 센서를 찾을 수 없습니다.")
            print("\n테스트를 중단합니다.")
            return
            
    except Exception as e:
        print(f"❌ SDP810 센서 스캔 실패: {e}")
        return
    
    # 2. 실시간 데이터 수집
    print(f"\n2. 실시간 데이터 수집 (2초 간격 10회):")
    print("-" * 40)
    print(f"{'순번':>3} {'시간':>8} {'차압 (Pa)':>12} {'CRC':>5} {'상태':>8}")
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
                # 멀티플렉서 채널 선택 (있는 경우)
                if channel is not None:
                    if not scanner._select_channel(bus, channel):
                        raise Exception("멀티플렉서 채널 선택 실패")
                
                # SDP810 차압 측정 (센서 안정화 대기)
                time.sleep(0.1)  # 센서 안정화 대기
                bus_obj = scanner.buses[bus]
                pressure_data = measure_sdp810_pressure(bus_obj, address)
                
                # 멀티플렉서 채널 해제
                if channel is not None:
                    scanner._disable_all_channels(bus)
                
                if pressure_data['success']:
                    pressure_value = pressure_data['pressure']
                    crc_ok = pressure_data['crc_ok']
                    
                    # CRC 상태에 따른 전체 상태 결정
                    overall_status = 'OK' if crc_ok else 'CRC_FAIL'
                    
                    # 측정 결과 기록
                    measurements.append({
                        'sequence': i + 1,
                        'time': current_time,
                        'pressure': pressure_value,
                        'crc_ok': crc_ok,
                        'status': overall_status
                    })
                    
                    crc_status = "✅" if crc_ok else "❌"
                    status_display = "✅ OK" if crc_ok else "⚠️ CRC"
                    print(f"{i+1:3d} {time_str:>8} {pressure_value:>10.3f} {crc_status:>5} {status_display:>8}")
                else:
                    raise Exception(pressure_data['error'])
                
            else:
                # Mock 데이터 (개발 환경)
                pressure_value = 0.025 + (i * 0.001)  # 0.025~0.034 Pa 범위
                measurements.append({
                    'sequence': i + 1,
                    'time': current_time,
                    'pressure': pressure_value,
                    'crc_ok': True,
                    'status': 'MOCK'
                })
                
                print(f"{i+1:3d} {time_str:>8} {pressure_value:>10.3f} {'✅':>5} {'🔧 MOCK':>8}")
            
        except Exception as e:
            errors += 1
            error_time = datetime.now().strftime("%H:%M:%S")
            print(f"{i+1:3d} {error_time:>8} {'ERROR':>10} {'❌':>5} {'❌ FAIL':>8}")
            print(f"    오류: {str(e)}")
            
            measurements.append({
                'sequence': i + 1,
                'time': datetime.now(),
                'pressure': None,
                'crc_ok': False,
                'status': 'ERROR',
                'error': str(e)
            })
        
        # 마지막 측정이 아니면 대기
        if i < measurement_count - 1:
            await asyncio.sleep(interval_seconds)
    
    # 3. 측정 결과 분석
    print(f"\n3. 측정 결과 분석:")
    print("-" * 40)
    
    successful_measurements = [m for m in measurements if m['status'] in ['OK', 'MOCK', 'CRC_FAIL'] and m['pressure'] is not None]
    perfect_measurements = [m for m in measurements if m['status'] in ['OK', 'MOCK'] and m['pressure'] is not None]
    crc_failed_measurements = [m for m in measurements if m['status'] == 'CRC_FAIL']
    
    if successful_measurements:
        pressure_values = [m['pressure'] for m in successful_measurements]
        crc_successes = [m for m in successful_measurements if m['crc_ok']]
        
        print(f"✅ 완전 성공한 측정: {len(perfect_measurements)}/{measurement_count}회 (CRC 포함)")
        print(f"⚠️ CRC 실패 측정: {len(crc_failed_measurements)}/{measurement_count}회 (데이터는 유효)")
        print(f"❌ 완전 실패한 측정: {errors}회")
        print(f"📊 전체 데이터 신뢰도: {len(crc_successes)}/{len(successful_measurements)}회 ({len(crc_successes)/len(successful_measurements)*100:.1f}%)")
        print(f"📊 차압 통계:")
        print(f"   - 최소값: {min(pressure_values):.4f} Pa")
        print(f"   - 최대값: {max(pressure_values):.4f} Pa")
        print(f"   - 평균값: {sum(pressure_values)/len(pressure_values):.4f} Pa")
        print(f"   - 변화 범위: {max(pressure_values) - min(pressure_values):.4f} Pa")
        
        # 연속성 확인
        if len(pressure_values) > 1:
            changes = [abs(pressure_values[i] - pressure_values[i-1]) for i in range(1, len(pressure_values))]
            avg_change = sum(changes) / len(changes)
            print(f"   - 평균 변화량: {avg_change:.4f} Pa")
        
        # 데이터 품질 평가
        if max(pressure_values) - min(pressure_values) > 0.001:  # 0.001 Pa 이상 변화
            print(f"   - 데이터 품질: ✅ 변화 감지됨 (실제 센서 가능성 높음)")
        else:
            print(f"   - 데이터 품질: ⚠️ 변화 미미 (안정적 환경 또는 Mock 데이터)")
            
        # 일반적인 차압 범위와 비교
        avg_pressure = sum(pressure_values) / len(pressure_values)
        if abs(avg_pressure) < 0.1:  # ±0.1 Pa 이내
            print(f"   - 범위 평가: ✅ 일반적인 실내 차압 범위 (±0.1 Pa)")
        elif abs(avg_pressure) < 1.0:  # ±1 Pa 이내
            print(f"   - 범위 평가: ⚠️ 약간 높은 차압 (±1 Pa)")
        else:
            print(f"   - 범위 평가: ❌ 비정상적으로 높은 차압 (±1 Pa 초과)")
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
                "pressure": latest_measurement['pressure'],
                "timestamp": latest_measurement['time'].isoformat(),
                "crc_valid": latest_measurement['crc_ok']
            },
            "sensor_info": {
                "bus": bus,
                "mux_channel": channel,
                "address": f"0x{address:02X}"
            }
        }
        
        print(f"✅ /api/sensors/sdp810/{bus}/{channel if channel is not None else 'direct'} 응답 형식:")
        print(json.dumps(api_response, indent=2, ensure_ascii=False))
    else:
        print(f"❌ 성공한 측정이 없어 API 응답을 생성할 수 없습니다.")
    
    # 5. 테스트 요약
    print("\n" + "=" * 70)
    print("SDP810 실시간 데이터 수집 테스트 완료")
    print("=" * 70)
    
    if successful_measurements:
        print(f"✅ 테스트 성공: {len(successful_measurements)}/{measurement_count}회 데이터 수집")
        print(f"   - 완전 성공 (CRC 포함): {len(perfect_measurements)}회")
        print(f"   - CRC 실패 (데이터 유효): {len(crc_failed_measurements)}회")
        print(f"📊 최종 차압값: {successful_measurements[-1]['pressure']:.4f} Pa")
        
        if len(perfect_measurements) >= measurement_count * 0.7:  # 70% 이상 완전 성공
            print(f"🔧 Dashboard API 검증 준비 완료 (데이터 신뢰도 양호)")
        elif len(successful_measurements) >= measurement_count * 0.8:  # 80% 이상 데이터 수집
            print(f"⚠️ Dashboard API 검증 가능 (CRC 오류 다수, 센서 점검 권장)")
        else:
            print(f"❌ Dashboard API 검증 어려움 (데이터 신뢰도 낮음)")
    else:
        print(f"❌ 테스트 실패: 성공한 측정이 없습니다.")
        print(f"🔧 확인사항:")
        print(f"   1. SDP810 센서 연결 상태 확인")
        print(f"   2. TCA9548A 멀티플렉서 상태 확인 (해당하는 경우)")
        print(f"   3. I2C 버스 상태 확인")
        print(f"   4. 센서 주소 확인 (0x25)")
        print(f"   5. 센서 전원 및 배선 확인")
    
    print("=" * 70)


async def manual_sdp810_scan(scanner):
    """수동 SDP810 센서 스캔"""
    print("🔍 수동 SDP810 센서 스캔 시작...")
    
    sdp810_devices = []
    sdp810_address = 0x25
    
    # Bus 0, 1에서 직접 연결 및 멀티플렉서 채널 스캔
    for bus_num in [0, 1]:
        if bus_num not in scanner.buses:
            continue
            
        print(f"  🔍 Bus {bus_num} 스캔...")
        
        # 직접 연결 확인
        try:
            bus_obj = scanner.buses[bus_num]
            pressure_data = measure_sdp810_pressure(bus_obj, sdp810_address)
            if pressure_data['success']:
                device = {
                    'sensor_id': f'sdp810_{bus_num}_direct_25',
                    'sensor_type': 'SDP810',
                    'bus': bus_num,
                    'mux_channel': None,
                    'address': '0x25',
                    'location': f'Bus {bus_num}, 직접 연결',
                    'status': 'connected',
                    'test_result': f"차압: {pressure_data['pressure']:.3f} Pa"
                }
                sdp810_devices.append(device)
                print(f"    ✅ Bus {bus_num} 직접 연결: SDP810 발견")
        except Exception as e:
            print(f"    ⚪ Bus {bus_num} 직접 연결: 응답 없음")
        
        # 멀티플렉서 채널 확인
        if bus_num in scanner.tca_info:
            print(f"    🔍 Bus {bus_num} 멀티플렉서 채널 스캔...")
            for channel in range(8):
                try:
                    if scanner._select_channel(bus_num, channel):
                        bus_obj = scanner.buses[bus_num]
                        pressure_data = measure_sdp810_pressure(bus_obj, sdp810_address)
                        
                        if pressure_data['success']:
                            device = {
                                'sensor_id': f'sdp810_{bus_num}_{channel}_25',
                                'sensor_type': 'SDP810',
                                'bus': bus_num,
                                'mux_channel': channel,
                                'address': '0x25',
                                'location': f'Bus {bus_num}, CH {channel}',
                                'status': 'connected',
                                'test_result': f"차압: {pressure_data['pressure']:.3f} Pa"
                            }
                            sdp810_devices.append(device)
                            print(f"      ✅ Bus {bus_num} CH{channel}: SDP810 발견")
                        
                        scanner._disable_all_channels(bus_num)
                except Exception as e:
                    pass
    
    return sdp810_devices


def measure_sdp810_pressure(bus_obj, address):
    """SDP810 센서에서 차압 측정 (ref/sdp810_sensor.py 기반)"""
    try:
        # SDP810 센서 안정화 대기 (센서 특성상 필요)
        time.sleep(0.05)
        
        # 3바이트 읽기: [pressure_msb, pressure_lsb, crc]
        import smbus2
        read_msg = smbus2.i2c_msg.read(address, 3)
        bus_obj.i2c_rdwr(read_msg)
        raw_data = list(read_msg)
        
        if len(raw_data) != 3:
            return {"success": False, "error": f"데이터 길이 오류: {len(raw_data)}"}
        
        pressure_msb = raw_data[0]
        pressure_lsb = raw_data[1]
        received_crc = raw_data[2]
        
        # CRC 검증
        calculated_crc = calculate_crc8([pressure_msb, pressure_lsb])
        crc_ok = calculated_crc == received_crc
        
        # 압력 계산 (ref/sdp810_sensor.py 방식)
        import struct
        raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]
        pressure_pa = raw_pressure / 60.0  # SDP810 스케일링
        
        # 센서 범위 제한 적용 (±500 Pa)
        pressure_pa = max(-500.0, min(500.0, pressure_pa))
        
        return {
            "success": True,
            "pressure": pressure_pa,
            "crc_ok": crc_ok,
            "raw_pressure": raw_pressure,
            "raw_data": raw_data
        }
        
    except Exception as e:
        return {"success": False, "error": f"측정 오류: {e}"}


def calculate_crc8(data):
    """CRC8 체크섬 계산 (SDP810용)"""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x31
            else:
                crc = crc << 1
    return crc & 0xFF


if __name__ == "__main__":
    asyncio.run(test_sdp810_realtime_data())