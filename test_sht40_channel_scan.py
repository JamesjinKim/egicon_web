#!/usr/bin/env python3
"""
SHT40 센서 동적 채널 스캔 프로그램
===============================
Bus 0, Bus 1 모두 동적으로 사용하는 환경에서
TCA9548A의 모든 채널을 스캔해서 SHT40 센서를 찾는 프로그램
"""

import sys
import time
import smbus2
import logging
import subprocess

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_crc(data):
    """CRC-8 체크섬 계산 (SHT40용)"""
    CRC = 0xFF
    for byte in data:
        CRC ^= byte
        for _ in range(8):
            if CRC & 0x80:
                CRC = (CRC << 1) ^ 0x31
            else:
                CRC = (CRC << 1) & 0xFF
    return CRC

def test_sht40_at_address(bus, address, bus_num, channel, tca_address):
    """특정 주소에서 SHT40 센서 테스트 (TCA9548A 채널 선택된 상태)"""
    CMD_SOFT_RESET = 0x94
    CMD_MEASURE_MEDIUM = 0xF6
    
    try:
        # 소프트 리셋 시도
        reset_msg = smbus2.i2c_msg.write(address, [CMD_SOFT_RESET])
        bus.i2c_rdwr(reset_msg)
        time.sleep(0.2)  # 리셋 후 충분한 대기
        
        # 측정 명령 전송
        measure_msg = smbus2.i2c_msg.write(address, [CMD_MEASURE_MEDIUM])
        bus.i2c_rdwr(measure_msg)
        time.sleep(0.5)  # 측정 완료까지 충분한 대기
        
        # 데이터 읽기
        read_msg = smbus2.i2c_msg.read(address, 6)
        bus.i2c_rdwr(read_msg)
        data = list(read_msg)
        
        # CRC 검증
        t_crc_ok = calculate_crc(data[0:2]) == data[2]
        rh_crc_ok = calculate_crc(data[3:5]) == data[5]
        
        if t_crc_ok and rh_crc_ok:
            # 온습도 계산
            t_raw = (data[0] << 8) | data[1]
            rh_raw = (data[3] << 8) | data[4]
            temperature = -45 + 175 * (t_raw / 65535.0)
            humidity = max(0, min(100, -6 + 125 * (rh_raw / 65535.0)))
            
            print(f"      ✅ 측정 성공: {temperature:.2f}°C, {humidity:.2f}%RH")
            return True
        else:
            print(f"      ⚠️ CRC 검증 실패 (T:{t_crc_ok}, RH:{rh_crc_ok})")
            return False
            
    except Exception as e:
        print(f"      ❌ 통신 실패: {e}")
        return False

def test_sht40_direct(bus, address, bus_num):
    """직접 연결된 SHT40 센서 테스트"""
    CMD_SOFT_RESET = 0x94
    CMD_MEASURE_MEDIUM = 0xF6
    
    try:
        # 소프트 리셋 시도
        reset_msg = smbus2.i2c_msg.write(address, [CMD_SOFT_RESET])
        bus.i2c_rdwr(reset_msg)
        time.sleep(0.2)
        
        # 측정 명령 전송
        measure_msg = smbus2.i2c_msg.write(address, [CMD_MEASURE_MEDIUM])
        bus.i2c_rdwr(measure_msg)
        time.sleep(0.5)
        
        # 데이터 읽기
        read_msg = smbus2.i2c_msg.read(address, 6)
        bus.i2c_rdwr(read_msg)
        data = list(read_msg)
        
        # CRC 검증
        t_crc_ok = calculate_crc(data[0:2]) == data[2]
        rh_crc_ok = calculate_crc(data[3:5]) == data[5]
        
        if t_crc_ok and rh_crc_ok:
            # 온습도 계산
            t_raw = (data[0] << 8) | data[1]
            rh_raw = (data[3] << 8) | data[4]
            temperature = -45 + 175 * (t_raw / 65535.0)
            humidity = max(0, min(100, -6 + 125 * (rh_raw / 65535.0)))
            
            print(f"    ✅ 측정 성공: {temperature:.2f}°C, {humidity:.2f}%RH")
            return True
        else:
            print(f"    ⚠️ CRC 검증 실패")
            return False
            
    except Exception as e:
        print(f"    ❌ 통신 실패: {e}")
        return False

def scan_all_buses_and_channels():
    """Bus 0, Bus 1 모든 TCA9548A 채널에서 SHT40 센서 동적 스캔"""
    print("🔍 동적 SHT40 센서 전체 스캔")
    print("=" * 60)
    
    buses_to_scan = [0, 1]  # 동적으로 사용되는 모든 버스
    tca_address = 0x70
    sht40_addresses = [0x44, 0x45]
    found_sensors = []
    
    for bus_num in buses_to_scan:
        print(f"\\n📡 === I2C Bus {bus_num} 스캔 ===")
        
        try:
            bus = smbus2.SMBus(bus_num)
            
            # 먼저 TCA9548A 존재 확인
            tca_available = False
            try:
                bus.write_byte(tca_address, 0x00)  # 모든 채널 비활성화
                current_channels = bus.read_byte(tca_address)
                tca_available = True
                print(f"✅ TCA9548A 발견 (Bus {bus_num}, 주소 0x{tca_address:02x})")
            except Exception as e:
                print(f"⚪ TCA9548A 없음 (Bus {bus_num}): {e}")
            
            if tca_available:
                # TCA9548A를 통한 각 채널 스캔
                print(f"🔍 TCA9548A 채널별 스캔 (Bus {bus_num})")
                
                for channel in range(8):
                    print(f"\\n  📍 채널 {channel} 스캔...")
                    
                    try:
                        # 채널 선택
                        channel_mask = 1 << channel
                        bus.write_byte(tca_address, channel_mask)
                        time.sleep(0.1)  # 채널 전환 대기시간 증가
                        
                        # 선택된 채널 확인
                        selected = bus.read_byte(tca_address)
                        if selected == channel_mask:
                            print(f"    ✅ 채널 {channel} 선택 성공")
                            
                            # SHT40 주소들 확인
                            for addr in sht40_addresses:
                                print(f"    🔍 주소 0x{addr:02x} 테스트...")
                                
                                success = test_sht40_at_address(bus, addr, bus_num, channel, tca_address)
                                if success:
                                    found_sensors.append({
                                        'bus': bus_num,
                                        'channel': channel,
                                        'address': addr,
                                        'tca_address': tca_address,
                                        'connection_type': 'multiplexed'
                                    })
                                    print(f"    🎯 SHT40 발견! Bus {bus_num}, 채널 {channel}, 주소 0x{addr:02x}")
                        else:
                            print(f"    ⚠️ 채널 {channel} 선택 실패 (예상: 0x{channel_mask:02x}, 실제: 0x{selected:02x})")
                            
                        # 채널 비활성화
                        bus.write_byte(tca_address, 0x00)
                        time.sleep(0.05)
                        
                    except Exception as e:
                        print(f"    ❌ 채널 {channel} 스캔 실패: {e}")
                        try:
                            bus.write_byte(tca_address, 0x00)
                        except:
                            pass
            
            # 직접 연결 센서도 확인
            print(f"\\n🔍 Bus {bus_num} 직접 연결 센서 스캔")
            for addr in sht40_addresses:
                print(f"  🔍 주소 0x{addr:02x} 직접 테스트...")
                success = test_sht40_direct(bus, addr, bus_num)
                if success:
                    found_sensors.append({
                        'bus': bus_num,
                        'channel': None,
                        'address': addr,
                        'tca_address': None,
                        'connection_type': 'direct'
                    })
                    print(f"  🎯 SHT40 직접 연결 발견! Bus {bus_num}, 주소 0x{addr:02x}")
            
            bus.close()
            
        except Exception as e:
            print(f"❌ Bus {bus_num} 스캔 실패: {e}")
            continue
    
    return found_sensors

def test_sensor_performance(sensor_info, test_count=5):
    """발견된 센서의 성능 테스트"""
    print(f"\\n🧪 성능 테스트: Bus {sensor_info['bus']}, 채널 {sensor_info.get('channel', 'Direct')}, 주소 0x{sensor_info['address']:02x}")
    print(f"연속 {test_count}회 측정 테스트")
    
    success_count = 0
    temperatures = []
    humidities = []
    
    try:
        bus = smbus2.SMBus(sensor_info['bus'])
        
        for i in range(test_count):
            print(f"  측정 {i+1}/{test_count}...", end=" ")
            
            try:
                # TCA9548A 채널 선택 (필요한 경우)
                if sensor_info['connection_type'] == 'multiplexed':
                    channel_mask = 1 << sensor_info['channel']
                    bus.write_byte(sensor_info['tca_address'], channel_mask)
                    time.sleep(0.1)
                
                # 측정 수행
                CMD_MEASURE_MEDIUM = 0xF6
                measure_msg = smbus2.i2c_msg.write(sensor_info['address'], [CMD_MEASURE_MEDIUM])
                bus.i2c_rdwr(measure_msg)
                time.sleep(0.5)
                
                # 데이터 읽기
                read_msg = smbus2.i2c_msg.read(sensor_info['address'], 6)
                bus.i2c_rdwr(read_msg)
                data = list(read_msg)
                
                # CRC 검증
                t_crc_ok = calculate_crc(data[0:2]) == data[2]
                rh_crc_ok = calculate_crc(data[3:5]) == data[5]
                
                if t_crc_ok and rh_crc_ok:
                    t_raw = (data[0] << 8) | data[1]
                    rh_raw = (data[3] << 8) | data[4]
                    temperature = -45 + 175 * (t_raw / 65535.0)
                    humidity = max(0, min(100, -6 + 125 * (rh_raw / 65535.0)))
                    
                    temperatures.append(temperature)
                    humidities.append(humidity)
                    success_count += 1
                    print(f"✅ {temperature:.1f}°C, {humidity:.1f}%RH")
                else:
                    print("❌ CRC 실패")
                
                # 채널 비활성화 (필요한 경우)
                if sensor_info['connection_type'] == 'multiplexed':
                    bus.write_byte(sensor_info['tca_address'], 0x00)
                
                time.sleep(1)  # 측정 간 간격
                
            except Exception as e:
                print(f"❌ 실패: {e}")
        
        bus.close()
        
        # 성능 분석
        success_rate = (success_count / test_count) * 100
        print(f"\\n📊 성능 분석:")
        print(f"  성공률: {success_rate:.1f}% ({success_count}/{test_count})")
        
        if temperatures and humidities:
            print(f"  온도 범위: {min(temperatures):.1f}°C ~ {max(temperatures):.1f}°C")
            print(f"  습도 범위: {min(humidities):.1f}%RH ~ {max(humidities):.1f}%RH")
            print(f"  온도 평균: {sum(temperatures)/len(temperatures):.1f}°C")
            print(f"  습도 평균: {sum(humidities)/len(humidities):.1f}%RH")
        
        return success_rate >= 80  # 80% 이상 성공률을 기준으로 판정
        
    except Exception as e:
        print(f"\\n❌ 성능 테스트 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("🚀 SHT40 센서 동적 채널 스캔 프로그램")
    print("=" * 60)
    print("목적: Bus 0, Bus 1 동적 환경에서 모든 TCA9548A 채널을 스캔하여")
    print("      SHT40 센서의 정확한 위치와 동작 상태 확인")
    print("=" * 60)
    
    # 현재 I2C 상태 표시
    print("\\n📊 현재 I2C 버스 상태:")
    try:
        for bus_num in [0, 1]:
            print(f"\\n--- Bus {bus_num} ---")
            result = subprocess.run(['i2cdetect', '-y', str(bus_num)], 
                                  capture_output=True, text=True)
            print(result.stdout)
    except Exception as e:
        print(f"❌ I2C 스캔 실패: {e}")
    
    # 전체 센서 스캔
    print("\\n" + "="*60)
    print("🔍 SHT40 센서 전체 스캔 시작")
    print("="*60)
    
    found_sensors = scan_all_buses_and_channels()
    
    # 결과 요약
    print("\\n" + "="*60)
    print("📊 스캔 결과 요약")
    print("="*60)
    
    if found_sensors:
        print(f"✅ SHT40 센서 {len(found_sensors)}개 발견:")
        
        for i, sensor in enumerate(found_sensors, 1):
            connection = "직접 연결" if sensor['connection_type'] == 'direct' else f"TCA9548A 채널 {sensor['channel']}"
            print(f"  {i}. Bus {sensor['bus']}, {connection}, 주소 0x{sensor['address']:02x}")
        
        # 각 센서 성능 테스트
        print("\\n" + "="*60)
        print("🧪 발견된 센서 성능 테스트")
        print("="*60)
        
        working_sensors = []
        for sensor in found_sensors:
            performance_ok = test_sensor_performance(sensor, test_count=5)
            if performance_ok:
                working_sensors.append(sensor)
        
        # 최종 결과 및 권장사항
        print("\\n" + "="*60)
        print("🎯 최종 결과 및 권장사항")
        print("="*60)
        
        if working_sensors:
            print(f"✅ 정상 동작 SHT40 센서: {len(working_sensors)}개")
            
            print("\\n💡 코드 수정 권장사항:")
            print("  다음 센서 정보를 hardware_scanner.py와 sensor_handlers.py에 반영:")
            
            for sensor in working_sensors:
                if sensor['connection_type'] == 'direct':
                    print(f"    - Bus {sensor['bus']}, 직접 연결, 주소 0x{sensor['address']:02x}")
                else:
                    print(f"    - Bus {sensor['bus']}, TCA9548A 채널 {sensor['channel']}, 주소 0x{sensor['address']:02x}")
            
            print("\\n📋 수정할 파일:")
            print("  1. hardware_scanner.py: scan_sht40_sensors() 함수")
            print("  2. sensor_handlers.py: read_sht40_data() 함수")
            print("  3. frontend/dashboard.js: SHT40 관련 설정")
            
        else:
            print("❌ 정상 동작하는 SHT40 센서 없음")
            print("\\n🔧 추가 진단 필요:")
            print("  1. 하드웨어 연결 상태 재확인")
            print("  2. 전원 공급 안정성 확인")
            print("  3. SHT40 센서 교체 검토")
    else:
        print("❌ SHT40 센서를 전혀 찾을 수 없음")
        print("\\n🔧 확인사항:")
        print("  1. SHT40 센서가 실제로 연결되어 있는지 확인")
        print("  2. I2C 케이블 연결 상태 확인")
        print("  3. TCA9548A 멀티플렉서 동작 상태 확인")
        print("  4. 전원 공급 상태 확인")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\\n⏹️ 사용자에 의해 스캔 중단됨")
    except Exception as e:
        print(f"\\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)