#!/usr/bin/env python3
"""
SHT40 센서 테스트 스크립트 - Bus 1 Channel 1
===========================================
Bus 1 CH1에서 SHT40 센서 검출 및 테스트
"""

import sys
import time
from datetime import datetime

# SHT40 센서 모듈 임포트
try:
    from sht40_sensor import SHT40Sensor
    print("✅ SHT40 센서 모듈 로드 성공")
except ImportError as e:
    print(f"❌ SHT40 센서 모듈 로드 실패: {e}")
    print("sht40_sensor.py 파일이 있는지 확인해주세요.")
    sys.exit(1)

# I2C 및 하드웨어 스캐너 임포트
try:
    import smbus2
    I2C_AVAILABLE = True
    print("✅ I2C 라이브러리 로드 성공")
except ImportError:
    I2C_AVAILABLE = False
    print("❌ I2C 라이브러리 없음 - Mock 모드로 실행")

def test_sht40_bus1_ch1():
    """Bus 1 Channel 1에서 SHT40 센서 테스트"""
    
    print("=" * 60)
    print("🔍 SHT40 센서 테스트 - Bus 1 Channel 1")
    print("=" * 60)
    
    # SHT40 센서 설정
    bus_num = 1
    channel = 1
    sht40_addresses = [0x44, 0x45]  # SHT40 가능한 주소들
    mux_address = 0x70  # TCA9548A 주소
    
    if not I2C_AVAILABLE:
        print("⚠️ I2C 라이브러리 없음 - 실제 테스트 불가능")
        return False
    
    print(f"📋 테스트 설정:")
    print(f"   - Bus: {bus_num}")
    print(f"   - Channel: {channel}")
    print(f"   - MUX Address: 0x{mux_address:02X}")
    print(f"   - SHT40 Addresses: {[f'0x{addr:02X}' for addr in sht40_addresses]}")
    print()
    
    found_sensors = []
    
    # 각 SHT40 주소에 대해 테스트
    for sht40_addr in sht40_addresses:
        print(f"🔍 SHT40 센서 테스트 중... (0x{sht40_addr:02X})")
        
        try:
            # SHT40 센서 객체 생성
            sensor = SHT40Sensor(
                bus=bus_num,
                address=sht40_addr,
                mux_channel=channel,
                mux_address=mux_address
            )
            
            # 센서 연결 시도
            print(f"   📡 연결 시도...")
            sensor.connect()
            
            # 연결 테스트
            print(f"   🧪 연결 테스트...")
            success, message = sensor.test_connection()
            
            if success:
                print(f"   ✅ SHT40 센서 발견! 0x{sht40_addr:02X}")
                print(f"   📊 테스트 결과: {message}")
                
                # 시리얼 번호 읽기 시도
                try:
                    serial_num = sensor.read_serial_number()
                    if serial_num:
                        print(f"   🔢 시리얼 번호: {serial_num}")
                except Exception as e:
                    print(f"   ⚠️ 시리얼 번호 읽기 실패: {e}")
                
                # 센서 정보 저장
                sensor_info = {
                    "address": f"0x{sht40_addr:02X}",
                    "bus": bus_num,
                    "channel": channel,
                    "test_result": message,
                    "sensor_id": f"sht40_{bus_num}_{channel}_{sht40_addr:02x}",
                    "timestamp": datetime.now().isoformat()
                }
                found_sensors.append(sensor_info)
                
                # 추가 측정 테스트
                print(f"   📈 연속 측정 테스트 (5회)...")
                for i in range(5):
                    try:
                        temp, humidity = sensor.read_with_retry(precision="high", max_retries=2)
                        if temp is not None and humidity is not None:
                            print(f"      {i+1}회: {temp:.2f}°C, {humidity:.2f}%RH")
                        else:
                            print(f"      {i+1}회: 측정 실패")
                        time.sleep(1)
                    except Exception as e:
                        print(f"      {i+1}회: 오류 - {e}")
                
            else:
                print(f"   ❌ SHT40 센서 없음 (0x{sht40_addr:02X}): {message}")
            
            # 센서 연결 해제
            sensor.close()
            
        except Exception as e:
            print(f"   ❌ SHT40 테스트 실패 (0x{sht40_addr:02X}): {e}")
        
        print()
    
    # 결과 요약
    print("=" * 60)
    print("📊 SHT40 테스트 결과 요약")
    print("=" * 60)
    
    if found_sensors:
        print(f"✅ 발견된 SHT40 센서: {len(found_sensors)}개")
        for i, sensor in enumerate(found_sensors, 1):
            print(f"   {i}. 주소: {sensor['address']}")
            print(f"      센서 ID: {sensor['sensor_id']}")
            print(f"      테스트 결과: {sensor['test_result']}")
            print(f"      타임스탬프: {sensor['timestamp']}")
    else:
        print("❌ Bus 1 Channel 1에서 SHT40 센서를 찾을 수 없습니다.")
        print()
        print("🔍 확인 사항:")
        print("   1. SHT40 센서가 올바르게 연결되어 있는지 확인")
        print("   2. TCA9548A 멀티플렉서 Channel 1에 연결되어 있는지 확인")
        print("   3. 전원 공급이 정상인지 확인 (3.3V)")
        print("   4. I2C 주소가 0x44 또는 0x45인지 확인")
        print("   5. 다른 센서와 주소 충돌이 없는지 확인")
    
    print("=" * 60)
    return len(found_sensors) > 0

def manual_i2c_scan():
    """수동 I2C 스캔 - Bus 1 Channel 1"""
    
    print("🔍 수동 I2C 스캔 - Bus 1 Channel 1")
    print("-" * 40)
    
    if not I2C_AVAILABLE:
        print("❌ I2C 라이브러리 없음")
        return
    
    try:
        bus = smbus2.SMBus(1)
        mux_address = 0x70
        channel = 1
        
        # 멀티플렉서 채널 선택
        print(f"📡 TCA9548A 채널 {channel} 선택...")
        channel_mask = 1 << channel
        bus.write_byte(mux_address, channel_mask)
        time.sleep(0.01)
        
        print(f"🔍 I2C 주소 스캔 중...")
        found_devices = []
        
        for addr in range(0x08, 0x78):  # I2C 주소 범위
            try:
                bus.read_byte(addr)
                found_devices.append(addr)
                print(f"   ✅ 0x{addr:02X} - 응답함")
            except:
                pass
        
        bus.close()
        
        if found_devices:
            print(f"\n📊 발견된 I2C 장치: {len(found_devices)}개")
            for addr in found_devices:
                device_type = "Unknown"
                if addr in [0x44, 0x45]:
                    device_type = "SHT40 (추정)"
                elif addr in [0x76, 0x77]:
                    device_type = "BME688 (추정)"
                elif addr in [0x23, 0x5C]:
                    device_type = "BH1750 (추정)"
                
                print(f"   0x{addr:02X} - {device_type}")
        else:
            print("❌ Bus 1 Channel 1에서 I2C 장치를 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ I2C 스캔 실패: {e}")

if __name__ == "__main__":
    print("🚀 SHT40 센서 테스트 시작")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 수동 I2C 스캔 먼저 실행
    manual_i2c_scan()
    print()
    
    # 2. SHT40 센서 테스트
    success = test_sht40_bus1_ch1()
    
    print()
    print("🏁 테스트 완료")
    print(f"⏰ 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("✅ SHT40 센서 테스트 성공!")
        sys.exit(0)
    else:
        print("❌ SHT40 센서 테스트 실패")
        sys.exit(1)