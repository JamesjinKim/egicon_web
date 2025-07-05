#!/usr/bin/env python3
"""
SDP800 센서 위치 찾기 스크립트
============================
모든 채널과 주소에서 SDP800 센서 검색
"""

import sys
import time
from datetime import datetime

try:
    import smbus2
    print("✅ I2C 라이브러리 로드 성공")
except ImportError:
    print("❌ I2C 라이브러리 없음")
    sys.exit(1)

def scan_for_sdp800():
    """모든 채널에서 SDP800 센서 검색"""
    
    print("=" * 60)
    print("🔍 SDP800 센서 전체 검색")
    print("=" * 60)
    
    bus_num = 1
    mux_address = 0x70
    
    # SDP800 시리즈 가능한 주소들
    sdp_addresses = [
        0x25,  # SDP810, SDP800 기본
        0x26,  # SDP800 변형
        0x21,  # SDP3x 시리즈
        0x22,  # SDP3x 시리즈  
        0x23,  # SDP3x 시리즈
        0x24,  # SDP3x 시리즈
    ]
    
    found_sensors = []
    
    try:
        bus = smbus2.SMBus(bus_num)
        
        # 모든 채널 검색
        for channel in range(8):
            print(f"\n📡 Channel {channel} 검색 중...")
            
            try:
                # 채널 선택
                channel_mask = 1 << channel
                bus.write_byte(mux_address, channel_mask)
                time.sleep(0.01)
                
                # 채널 내 모든 장치 스캔
                channel_devices = []
                for addr in range(0x08, 0x78):
                    try:
                        bus.read_byte(addr)
                        channel_devices.append(addr)
                    except:
                        pass
                
                if channel_devices:
                    print(f"   발견된 장치들: {[f'0x{addr:02X}' for addr in channel_devices]}")
                    
                    # SDP800 주소 확인
                    for sdp_addr in sdp_addresses:
                        if sdp_addr in channel_devices:
                            print(f"   🎯 SDP800 후보 발견: 0x{sdp_addr:02X}")
                            
                            # SDP800 통신 테스트
                            success, pressure = test_sdp800_communication(bus, sdp_addr)
                            if success:
                                sensor_info = {
                                    'channel': channel,
                                    'address': sdp_addr,
                                    'pressure': pressure
                                }
                                found_sensors.append(sensor_info)
                                print(f"   ✅ SDP800 확인됨! 압력: {pressure:.2f} Pa")
                            else:
                                print(f"   ❌ SDP800 통신 실패")
                else:
                    print("   ❌ 장치 없음")
                    
            except Exception as e:
                print(f"   ❌ Channel {channel} 스캔 실패: {e}")
        
        bus.close()
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 SDP800 검색 결과")
        print("=" * 60)
        
        if found_sensors:
            print(f"✅ 발견된 SDP800 센서: {len(found_sensors)}개")
            for i, sensor in enumerate(found_sensors, 1):
                print(f"   {i}. Channel {sensor['channel']}, 주소 0x{sensor['address']:02X}")
                print(f"      현재 압력: {sensor['pressure']:.2f} Pa")
        else:
            print("❌ SDP800 센서를 찾을 수 없습니다.")
            print("\n🔍 확인 사항:")
            print("   1. SDP800 센서가 실제로 연결되어 있는지")
            print("   2. 전원 공급이 정상인지 (3.3V 또는 5V)")
            print("   3. I2C 케이블 연결 상태")
            print("   4. 센서 주소 설정 (ADDR 핀 상태)")
            print("   5. 다른 TCA9548A 채널에 연결되어 있는지")
        
        return found_sensors
        
    except Exception as e:
        print(f"❌ 검색 실패: {e}")
        return []

def test_sdp800_communication(bus, address):
    """SDP800 센서 통신 테스트"""
    try:
        # 3바이트 읽기 시도
        read_msg = smbus2.i2c_msg.read(address, 3)
        bus.i2c_rdwr(read_msg)
        raw_data = list(read_msg)
        
        if len(raw_data) == 3:
            # SDP800 데이터 파싱 시도
            import struct
            pressure_msb = raw_data[0]
            pressure_lsb = raw_data[1]
            
            # 압력 계산
            raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]
            pressure_pa = raw_pressure / 60.0
            
            # 합리적인 압력 범위 확인 (-1000 ~ +1000 Pa)
            if -1000 <= pressure_pa <= 1000:
                return True, pressure_pa
            else:
                return False, None
        
        return False, None
        
    except Exception as e:
        return False, None

def test_specific_address_across_channels(target_address=0x25):
    """특정 주소를 모든 채널에서 테스트"""
    
    print(f"\n🎯 주소 0x{target_address:02X} 전체 채널 검색")
    print("-" * 40)
    
    bus_num = 1
    mux_address = 0x70
    
    try:
        bus = smbus2.SMBus(bus_num)
        
        for channel in range(8):
            try:
                # 채널 선택
                channel_mask = 1 << channel
                bus.write_byte(mux_address, channel_mask)
                time.sleep(0.01)
                
                # 대상 주소 테스트
                bus.read_byte(target_address)
                print(f"Channel {channel}: ✅ 0x{target_address:02X} 응답함")
                
                # SDP800 통신 테스트
                success, pressure = test_sdp800_communication(bus, target_address)
                if success:
                    print(f"              🎯 SDP800 확인! 압력: {pressure:.2f} Pa")
                
            except Exception as e:
                print(f"Channel {channel}: ❌ 0x{target_address:02X} 응답없음")
        
        bus.close()
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    print("🚀 SDP800 센서 검색 시작")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 전체 검색
    found_sensors = scan_for_sdp800()
    
    # 2. 0x25 주소 특별 검색
    test_specific_address_across_channels(0x25)
    
    # 3. 0x26 주소도 검색
    test_specific_address_across_channels(0x26)
    
    print(f"\n⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if found_sensors:
        print("✅ SDP800 센서 검색 성공!")
    else:
        print("❌ SDP800 센서를 찾지 못했습니다.")