#!/usr/bin/env python3
"""
전체 채널 스캔 스크립트
====================
Bus 0, Bus 1의 모든 채널에서 센서 검출
"""

import sys
import time
from datetime import datetime

# I2C 라이브러리 임포트
try:
    import smbus2
    I2C_AVAILABLE = True
    print("✅ I2C 라이브러리 로드 성공")
except ImportError:
    I2C_AVAILABLE = False
    print("❌ I2C 라이브러리 없음 - 실행 불가능")
    sys.exit(1)

def scan_channel(bus_num, channel, mux_address=0x70):
    """특정 채널 스캔"""
    try:
        bus = smbus2.SMBus(bus_num)
        
        # 멀티플렉서 채널 선택
        channel_mask = 1 << channel
        bus.write_byte(mux_address, channel_mask)
        time.sleep(0.01)
        
        found_devices = []
        
        # I2C 주소 스캔
        for addr in range(0x08, 0x78):
            try:
                bus.read_byte(addr)
                found_devices.append(addr)
            except:
                pass
        
        bus.close()
        return found_devices
        
    except Exception as e:
        print(f"❌ Bus {bus_num} Channel {channel} 스캔 실패: {e}")
        return []

def identify_sensor(addr):
    """주소로 센서 타입 추정"""
    sensor_map = {
        0x44: "SHT40",
        0x45: "SHT40", 
        0x76: "BME688",
        0x77: "BME688",
        0x23: "BH1750",
        0x5C: "BH1750",
        0x25: "SDP810",
        0x29: "VL53L0X"
    }
    return sensor_map.get(addr, "Unknown")

def scan_all_channels():
    """모든 버스와 채널 스캔"""
    
    print("=" * 80)
    print("🔍 전체 시스템 스캔 - 모든 버스/채널")
    print("=" * 80)
    
    total_devices = 0
    scan_results = {}
    
    for bus_num in [0, 1]:
        print(f"\n🚌 Bus {bus_num} 스캔 중...")
        scan_results[bus_num] = {}
        
        for channel in range(8):  # TCA9548A는 8채널
            print(f"   📡 Channel {channel} 스캔 중...", end=" ")
            
            devices = scan_channel(bus_num, channel)
            scan_results[bus_num][channel] = devices
            
            if devices:
                print(f"✅ {len(devices)}개 발견")
                for addr in devices:
                    sensor_type = identify_sensor(addr)
                    print(f"      0x{addr:02X} - {sensor_type}")
                    total_devices += 1
            else:
                print("❌ 없음")
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 스캔 결과 요약")
    print("=" * 80)
    
    if total_devices > 0:
        print(f"✅ 총 발견된 장치: {total_devices}개\n")
        
        # 버스별 상세 결과
        for bus_num in [0, 1]:
            bus_devices = sum(len(devices) for devices in scan_results[bus_num].values())
            if bus_devices > 0:
                print(f"🚌 Bus {bus_num}: {bus_devices}개 장치")
                
                for channel in range(8):
                    devices = scan_results[bus_num][channel]
                    if devices:
                        print(f"   📡 CH{channel}: ", end="")
                        device_strs = []
                        for addr in devices:
                            sensor_type = identify_sensor(addr)
                            device_strs.append(f"0x{addr:02X}({sensor_type})")
                        print(", ".join(device_strs))
                print()
        
        # SHT40 센서 특별 확인
        sht40_locations = []
        for bus_num in [0, 1]:
            for channel in range(8):
                devices = scan_results[bus_num][channel]
                for addr in devices:
                    if addr in [0x44, 0x45]:
                        sht40_locations.append(f"Bus{bus_num} CH{channel} 0x{addr:02X}")
        
        if sht40_locations:
            print("🌡️ SHT40 센서 발견 위치:")
            for location in sht40_locations:
                print(f"   ✅ {location}")
        else:
            print("❌ SHT40 센서(0x44, 0x45)를 찾을 수 없습니다.")
            
        print()
        
        # BME688 센서 확인
        bme688_locations = []
        for bus_num in [0, 1]:
            for channel in range(8):
                devices = scan_results[bus_num][channel]
                for addr in devices:
                    if addr in [0x76, 0x77]:
                        bme688_locations.append(f"Bus{bus_num} CH{channel} 0x{addr:02X}")
        
        if bme688_locations:
            print("🌡️ BME688 센서 발견 위치:")
            for location in bme688_locations:
                print(f"   ✅ {location}")
        print()
        
    else:
        print("❌ 어떤 I2C 장치도 찾을 수 없습니다.")
        print("🔍 확인 사항:")
        print("   1. TCA9548A 멀티플렉서가 올바르게 연결되어 있는지 확인")
        print("   2. 센서들이 전원을 받고 있는지 확인")
        print("   3. I2C 풀업 저항이 연결되어 있는지 확인")
        print("   4. 케이블 연결 상태 확인")
    
    return scan_results

def check_bus1_ch1_specifically():
    """Bus 1 Channel 1 특별 확인"""
    
    print("🔍 Bus 1 Channel 1 특별 확인")
    print("-" * 50)
    
    devices = scan_channel(1, 1)
    
    if devices:
        print(f"✅ Bus 1 CH1에서 {len(devices)}개 장치 발견:")
        for addr in devices:
            sensor_type = identify_sensor(addr)
            print(f"   0x{addr:02X} - {sensor_type}")
            
            if addr in [0x44, 0x45]:
                print(f"   🌡️ SHT40 센서 가능성 높음!")
                
    else:
        print("❌ Bus 1 CH1에서 장치를 찾을 수 없습니다.")
        
        # 추가 진단
        print("\n🔧 진단 정보:")
        
        # 멀티플렉서 자체 확인
        try:
            bus = smbus2.SMBus(1)
            bus.read_byte(0x70)  # TCA9548A 주소
            print("   ✅ TCA9548A 멀티플렉서 응답함")
            bus.close()
        except:
            print("   ❌ TCA9548A 멀티플렉서 응답 없음")
            
        # 다른 채널들도 빠르게 확인
        print("   📡 다른 채널 상태:")
        for ch in range(8):
            ch_devices = scan_channel(1, ch)
            if ch_devices:
                print(f"      CH{ch}: {len(ch_devices)}개 장치")
            else:
                print(f"      CH{ch}: 없음")

if __name__ == "__main__":
    print("🚀 전체 채널 스캔 시작")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 전체 스캔
    scan_results = scan_all_channels()
    
    print()
    
    # 2. Bus 1 CH1 특별 확인
    check_bus1_ch1_specifically()
    
    print()
    print("🏁 스캔 완료")
    print(f"⏰ 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")