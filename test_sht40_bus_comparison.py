#!/usr/bin/env python3
"""
SHT40 센서 Bus 0 vs Bus 1 + TCA9548A 비교 테스트
==============================================
Bus 0 직접 연결이 정상 동작하는데 Bus 1 + TCA9548A에서 
Remote I/O error가 발생하는 원인 분석
"""

import sys
import time
import smbus2
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SHT40BusComparison:
    """SHT40 센서 Bus 비교 테스트 클래스"""
    
    def __init__(self):
        self.CMD_MEASURE_HIGH_PRECISION = 0xFD
        self.CMD_MEASURE_MEDIUM_PRECISION = 0xF6
        self.CMD_MEASURE_LOW_PRECISION = 0xE0
        self.CMD_SOFT_RESET = 0x94
    
    def calculate_crc(self, data):
        """CRC-8 체크섬 계산"""
        CRC = 0xFF
        for byte in data:
            CRC ^= byte
            for _ in range(8):
                if CRC & 0x80:
                    CRC = (CRC << 1) ^ 0x31
                else:
                    CRC = (CRC << 1) & 0xFF
        return CRC
    
    def verify_crc(self, data, crc):
        """CRC 검증"""
        return self.calculate_crc(data) == crc
    
    def test_bus0_direct(self, address=0x44):
        """Bus 0 직접 연결 테스트 (정상 동작 확인된 방식)"""
        print(f"\\n🔍 === Bus 0 직접 연결 테스트 (주소: 0x{address:02x}) ===")
        
        try:
            bus = smbus2.SMBus(0)
            
            # 소프트 리셋
            reset_msg = smbus2.i2c_msg.write(address, [self.CMD_SOFT_RESET])
            bus.i2c_rdwr(reset_msg)
            time.sleep(0.1)
            print("✅ 소프트 리셋 성공")
            
            # 측정 명령 (Medium 정밀도)
            cmd = self.CMD_MEASURE_MEDIUM_PRECISION
            write_msg = smbus2.i2c_msg.write(address, [cmd])
            bus.i2c_rdwr(write_msg)
            print(f"✅ 측정 명령 전송 성공 (0x{cmd:02x})")
            
            # 대기
            time.sleep(0.02)
            
            # 데이터 읽기
            read_msg = smbus2.i2c_msg.read(address, 6)
            bus.i2c_rdwr(read_msg)
            data = list(read_msg)
            print(f"✅ 데이터 읽기 성공: {[hex(x) for x in data]}")
            
            # CRC 검증 및 값 계산
            t_data = [data[0], data[1]]
            t_crc = data[2]
            rh_data = [data[3], data[4]]
            rh_crc = data[5]
            
            t_crc_ok = self.verify_crc(t_data, t_crc)
            rh_crc_ok = self.verify_crc(rh_data, rh_crc)
            
            if t_crc_ok and rh_crc_ok:
                t_raw = (t_data[0] << 8) | t_data[1]
                rh_raw = (rh_data[0] << 8) | rh_data[1]
                temperature = -45 + 175 * (t_raw / 65535.0)
                humidity = max(0, min(100, -6 + 125 * (rh_raw / 65535.0)))
                print(f"✅ Bus 0 측정 성공: 온도={temperature:.2f}°C, 습도={humidity:.2f}%")
                bus.close()
                return True, temperature, humidity
            else:
                print(f"❌ Bus 0 CRC 실패: 온도={t_crc_ok}, 습도={rh_crc_ok}")
                bus.close()
                return False, None, None
                
        except Exception as e:
            print(f"❌ Bus 0 테스트 실패: {e}")
            if 'bus' in locals():
                bus.close()
            return False, None, None
    
    def test_bus1_tca9548a(self, address=0x44, channel=1, tca_address=0x70):
        """Bus 1 + TCA9548A 테스트 (문제가 있는 방식)"""
        print(f"\\n🔍 === Bus 1 + TCA9548A 테스트 (주소: 0x{address:02x}, 채널: {channel}) ===")
        
        try:
            bus = smbus2.SMBus(1)
            
            # TCA9548A 채널 선택
            channel_mask = 1 << channel
            bus.write_byte(tca_address, channel_mask)
            time.sleep(0.05)
            print(f"✅ TCA9548A 채널 {channel} 선택 성공 (마스크: 0x{channel_mask:02x})")
            
            # 소프트 리셋
            reset_msg = smbus2.i2c_msg.write(address, [self.CMD_SOFT_RESET])
            bus.i2c_rdwr(reset_msg)
            time.sleep(0.1)
            print("✅ 소프트 리셋 성공")
            
            # 측정 명령 (Medium 정밀도)
            cmd = self.CMD_MEASURE_MEDIUM_PRECISION
            write_msg = smbus2.i2c_msg.write(address, [cmd])
            bus.i2c_rdwr(write_msg)
            print(f"✅ 측정 명령 전송 성공 (0x{cmd:02x})")
            
            # 대기
            time.sleep(0.02)
            
            # 데이터 읽기
            read_msg = smbus2.i2c_msg.read(address, 6)
            bus.i2c_rdwr(read_msg)
            data = list(read_msg)
            print(f"✅ 데이터 읽기 성공: {[hex(x) for x in data]}")
            
            # CRC 검증 및 값 계산
            t_data = [data[0], data[1]]
            t_crc = data[2]
            rh_data = [data[3], data[4]]
            rh_crc = data[5]
            
            t_crc_ok = self.verify_crc(t_data, t_crc)
            rh_crc_ok = self.verify_crc(rh_data, rh_crc)
            
            if t_crc_ok and rh_crc_ok:
                t_raw = (t_data[0] << 8) | t_data[1]
                rh_raw = (rh_data[0] << 8) | rh_data[1]
                temperature = -45 + 175 * (t_raw / 65535.0)
                humidity = max(0, min(100, -6 + 125 * (rh_raw / 65535.0)))
                print(f"✅ Bus 1 + TCA9548A 측정 성공: 온도={temperature:.2f}°C, 습도={humidity:.2f}%")
                
                # 채널 비활성화
                bus.write_byte(tca_address, 0x00)
                bus.close()
                return True, temperature, humidity
            else:
                print(f"❌ Bus 1 + TCA9548A CRC 실패: 온도={t_crc_ok}, 습도={rh_crc_ok}")
                bus.write_byte(tca_address, 0x00)
                bus.close()
                return False, None, None
                
        except Exception as e:
            print(f"❌ Bus 1 + TCA9548A 테스트 실패: {e}")
            if 'bus' in locals():
                try:
                    bus.write_byte(tca_address, 0x00)
                    bus.close()
                except:
                    pass
            return False, None, None
    
    def test_bus1_direct(self, address=0x44):
        """Bus 1 직접 연결 테스트 (TCA9548A 없이)"""
        print(f"\\n🔍 === Bus 1 직접 연결 테스트 (주소: 0x{address:02x}) ===")
        
        try:
            bus = smbus2.SMBus(1)
            
            # 소프트 리셋
            reset_msg = smbus2.i2c_msg.write(address, [self.CMD_SOFT_RESET])
            bus.i2c_rdwr(reset_msg)
            time.sleep(0.1)
            print("✅ 소프트 리셋 성공")
            
            # 측정 명령 (Medium 정밀도)
            cmd = self.CMD_MEASURE_MEDIUM_PRECISION
            write_msg = smbus2.i2c_msg.write(address, [cmd])
            bus.i2c_rdwr(write_msg)
            print(f"✅ 측정 명령 전송 성공 (0x{cmd:02x})")
            
            # 대기
            time.sleep(0.02)
            
            # 데이터 읽기
            read_msg = smbus2.i2c_msg.read(address, 6)
            bus.i2c_rdwr(read_msg)
            data = list(read_msg)
            print(f"✅ 데이터 읽기 성공: {[hex(x) for x in data]}")
            
            # CRC 검증 및 값 계산
            t_data = [data[0], data[1]]
            t_crc = data[2]
            rh_data = [data[3], data[4]]
            rh_crc = data[5]
            
            t_crc_ok = self.verify_crc(t_data, t_crc)
            rh_crc_ok = self.verify_crc(rh_data, rh_crc)
            
            if t_crc_ok and rh_crc_ok:
                t_raw = (t_data[0] << 8) | t_data[1]
                rh_raw = (rh_data[0] << 8) | rh_data[1]
                temperature = -45 + 175 * (t_raw / 65535.0)
                humidity = max(0, min(100, -6 + 125 * (rh_raw / 65535.0)))
                print(f"✅ Bus 1 직접 측정 성공: 온도={temperature:.2f}°C, 습도={humidity:.2f}%")
                bus.close()
                return True, temperature, humidity
            else:
                print(f"❌ Bus 1 직접 CRC 실패: 온도={t_crc_ok}, 습도={rh_crc_ok}")
                bus.close()
                return False, None, None
                
        except Exception as e:
            print(f"❌ Bus 1 직접 테스트 실패: {e}")
            if 'bus' in locals():
                bus.close()
            return False, None, None
    
    def scan_i2c_buses(self):
        """I2C 버스 스캔"""
        print("\\n🔍 === I2C 버스 스캔 ===")
        
        for bus_num in [0, 1]:
            print(f"\\n--- Bus {bus_num} ---")
            try:
                import subprocess
                result = subprocess.run(['i2cdetect', '-y', str(bus_num)], 
                                      capture_output=True, text=True)
                print(result.stdout)
            except Exception as e:
                print(f"❌ Bus {bus_num} 스캔 실패: {e}")

def main():
    """비교 테스트 실행"""
    print("🧪 SHT40 센서 Bus 0 vs Bus 1 + TCA9548A 비교 테스트")
    print("=" * 60)
    print("목적: Bus 0에서 정상 동작하는 SHT40가 Bus 1 + TCA9548A에서")
    print("      Remote I/O error가 발생하는 원인 분석")
    print("=" * 60)
    
    tester = SHT40BusComparison()
    
    # I2C 버스 스캔
    tester.scan_i2c_buses()
    
    # 테스트 결과 저장
    results = {}
    
    # 1. Bus 0 직접 연결 테스트 (정상 동작 확인된 방식)
    print("\\n" + "="*60)
    print("1️⃣ Bus 0 직접 연결 테스트 (정상 동작 방식)")
    print("="*60)
    success, temp, hum = tester.test_bus0_direct()
    results['bus0_direct'] = {'success': success, 'temp': temp, 'hum': hum}
    
    # 2. Bus 1 직접 연결 테스트 (멀티플렉서 없이)
    print("\\n" + "="*60)
    print("2️⃣ Bus 1 직접 연결 테스트 (멀티플렉서 없이)")
    print("="*60)
    success, temp, hum = tester.test_bus1_direct()
    results['bus1_direct'] = {'success': success, 'temp': temp, 'hum': hum}
    
    # 3. Bus 1 + TCA9548A 테스트 (문제가 있는 방식)
    print("\\n" + "="*60)
    print("3️⃣ Bus 1 + TCA9548A 테스트 (문제 방식)")
    print("="*60)
    success, temp, hum = tester.test_bus1_tca9548a()
    results['bus1_tca9548a'] = {'success': success, 'temp': temp, 'hum': hum}
    
    # 결과 분석
    print("\\n" + "="*60)
    print("📊 테스트 결과 분석")
    print("="*60)
    
    for test_name, result in results.items():
        if result['success']:
            print(f"✅ {test_name}: 성공 - 온도={result['temp']:.2f}°C, 습도={result['hum']:.2f}%")
        else:
            print(f"❌ {test_name}: 실패")
    
    # 원인 분석
    print("\\n💡 원인 분석:")
    if results['bus0_direct']['success'] and not results['bus1_tca9548a']['success']:
        if results['bus1_direct']['success']:
            print("🎯 문제: TCA9548A 멀티플렉서 통신 문제")
            print("   - Bus 1 자체는 정상 동작")
            print("   - TCA9548A를 통한 SHT40 접근 시 문제 발생")
            print("   - 해결방안: TCA9548A 설정 또는 타이밍 조정 필요")
        else:
            print("🎯 문제: Bus 1 자체 문제")
            print("   - Bus 1에서 SHT40 직접 접근도 실패")
            print("   - 해결방안: Bus 1 하드웨어 연결 확인 필요")
    elif results['bus0_direct']['success'] and results['bus1_tca9548a']['success']:
        print("🎉 문제 해결: 모든 방식이 정상 동작")
    else:
        print("🚨 예상치 못한 결과: 추가 진단 필요")
    
    print("\\n" + "="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\\n⏹️ 사용자에 의해 테스트 중단됨")
    except Exception as e:
        print(f"\\n❌ 예상치 못한 오류: {e}")