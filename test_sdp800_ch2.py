#!/usr/bin/env python3
"""
SDP800 차압센서 테스트 스크립트 - Bus 1 Channel 2
===============================================
Sensirion SDP800 시리즈 차압센서를 TCA9548A를 통해 테스트
"""

import sys
import time
import struct
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

class SDP800TCATest:
    """TCA9548A를 통한 SDP800 센서 테스트 클래스"""
    
    def __init__(self, bus_num=1, mux_address=0x70, mux_channel=2, sensor_address=0x25):
        self.bus_num = bus_num
        self.mux_address = mux_address
        self.mux_channel = mux_channel
        self.sensor_address = sensor_address
        self.bus = None
        
        # SDP800 센서 정보
        self.sensor_info = {
            "name": "SDP800",
            "manufacturer": "Sensirion",
            "pressure_range": "±500 Pa",
            "accuracy": "±1.5% of reading",
            "interface": "I2C",
            "address": f"0x{sensor_address:02X}"
        }
    
    def _calculate_crc8(self, data):
        """CRC-8 계산 (Sensirion 표준)"""
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
                crc &= 0xFF
        return crc
    
    def select_mux_channel(self):
        """TCA9548A 멀티플렉서 채널 선택"""
        try:
            channel_mask = 1 << self.mux_channel
            self.bus.write_byte(self.mux_address, channel_mask)
            time.sleep(0.01)  # 채널 전환 대기
            
            # 채널 선택 확인
            current_channel = self.bus.read_byte(self.mux_address)
            if current_channel == channel_mask:
                print(f"✅ TCA9548A 채널 {self.mux_channel} 선택 완료")
                return True
            else:
                print(f"❌ 채널 선택 실패: 요청={channel_mask:02X}, 실제={current_channel:02X}")
                return False
                
        except Exception as e:
            print(f"❌ 멀티플렉서 채널 선택 실패: {e}")
            return False
    
    def scan_channel_devices(self):
        """현재 채널에서 I2C 장치 스캔"""
        print(f"🔍 Channel {self.mux_channel}에서 I2C 장치 스캔...")
        found_devices = []
        
        try:
            for addr in range(0x08, 0x78):
                try:
                    self.bus.read_byte(addr)
                    found_devices.append(addr)
                    device_type = self._identify_device(addr)
                    print(f"   ✅ 0x{addr:02X} - {device_type}")
                except:
                    pass
            
            if not found_devices:
                print("   ❌ 장치를 찾을 수 없습니다")
            
            return found_devices
            
        except Exception as e:
            print(f"   ❌ 스캔 실패: {e}")
            return []
    
    def _identify_device(self, address):
        """주소로 장치 타입 추정"""
        device_map = {
            0x25: "SDP810/SDP800 (추정)",
            0x26: "SDP800 (추정)",
            0x44: "SHT40",
            0x45: "SHT40",
            0x76: "BME688",
            0x77: "BME688",
            0x23: "BH1750",
            0x5C: "BH1750",
            0x70: "TCA9548A"
        }
        return device_map.get(address, "Unknown")
    
    def test_sdp800_communication(self):
        """SDP800 센서 통신 테스트"""
        print(f"\n🧪 SDP800 센서 통신 테스트 (0x{self.sensor_address:02X})")
        print("-" * 50)
        
        try:
            # 1. 기본 응답 테스트
            print("1️⃣ 기본 응답 테스트...")
            self.bus.read_byte(self.sensor_address)
            print("   ✅ 센서가 I2C 주소에서 응답함")
            
            # 2. 압력 데이터 읽기 테스트
            print("\n2️⃣ 압력 데이터 읽기 테스트...")
            pressure, crc_ok, message = self._read_pressure_data()
            
            if pressure is not None:
                print(f"   ✅ 압력 읽기 성공: {pressure:.2f} Pa")
                print(f"   🔍 CRC 검증: {'✅ 성공' if crc_ok else '❌ 실패'}")
                print(f"   📝 메시지: {message}")
                return True, pressure
            else:
                print(f"   ❌ 압력 읽기 실패: {message}")
                return False, None
                
        except Exception as e:
            print(f"   ❌ 통신 테스트 실패: {e}")
            return False, None
    
    def _read_pressure_data(self):
        """SDP800 압력 데이터 읽기"""
        try:
            # 3바이트 읽기: [pressure_msb, pressure_lsb, crc]
            read_msg = smbus2.i2c_msg.read(self.sensor_address, 3)
            self.bus.i2c_rdwr(read_msg)
            raw_data = list(read_msg)
            
            if len(raw_data) != 3:
                return None, False, f"데이터 길이 오류: {len(raw_data)}"
            
            pressure_msb = raw_data[0]
            pressure_lsb = raw_data[1]
            received_crc = raw_data[2]
            
            # CRC 검증
            calculated_crc = self._calculate_crc8([pressure_msb, pressure_lsb])
            crc_ok = calculated_crc == received_crc
            
            # 압력 계산
            raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]
            pressure_pa = raw_pressure / 60.0  # SDP800 스케일링 팩터
            
            # 범위 제한 (±500 Pa)
            pressure_pa = max(-500.0, min(500.0, pressure_pa))
            
            return pressure_pa, crc_ok, "OK"
            
        except Exception as e:
            return None, False, f"읽기 오류: {e}"
    
    def continuous_measurement(self, duration=10):
        """연속 측정 테스트"""
        print(f"\n📈 연속 측정 테스트 ({duration}초)")
        print("-" * 50)
        
        measurements = []
        
        for i in range(duration):
            try:
                pressure, crc_ok, message = self._read_pressure_data()
                
                if pressure is not None:
                    measurements.append(pressure)
                    status = "✅" if crc_ok else "⚠️"
                    print(f"   {i+1:2d}초: {pressure:6.2f} Pa {status}")
                else:
                    print(f"   {i+1:2d}초: 측정 실패 - {message}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"   {i+1:2d}초: 오류 - {e}")
        
        # 측정 통계
        if measurements:
            avg_pressure = sum(measurements) / len(measurements)
            min_pressure = min(measurements)
            max_pressure = max(measurements)
            
            print(f"\n📊 측정 통계:")
            print(f"   평균: {avg_pressure:.2f} Pa")
            print(f"   최소: {min_pressure:.2f} Pa")
            print(f"   최대: {max_pressure:.2f} Pa")
            print(f"   범위: {max_pressure - min_pressure:.2f} Pa")
            print(f"   성공률: {len(measurements)}/{duration} ({len(measurements)/duration*100:.1f}%)")
        
        return measurements

def main():
    """메인 테스트 함수"""
    
    print("=" * 70)
    print("🚀 SDP800 차압센서 TCA9548A 테스트")
    print("=" * 70)
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 설정
    bus_num = 1
    mux_address = 0x70
    mux_channel = 0  # Channel 0 (스캔 결과에서 확인됨)
    sensor_address = 0x25  # SDP800 기본 주소
    
    print("📋 테스트 설정:")
    print(f"   I2C 버스: {bus_num}")
    print(f"   멀티플렉서: 0x{mux_address:02X}")
    print(f"   채널: {mux_channel}")
    print(f"   센서 주소: 0x{sensor_address:02X}")
    print()
    
    try:
        # SDP800 테스트 객체 생성
        tester = SDP800TCATest(bus_num, mux_address, mux_channel, sensor_address)
        
        # I2C 버스 연결
        tester.bus = smbus2.SMBus(bus_num)
        
        # 1. TCA9548A 멀티플렉서 확인
        print("1️⃣ TCA9548A 멀티플렉서 확인...")
        try:
            tester.bus.read_byte(mux_address)
            print("   ✅ TCA9548A 응답 확인")
        except Exception as e:
            print(f"   ❌ TCA9548A 응답 없음: {e}")
            return False
        
        # 2. 채널 선택
        print(f"\n2️⃣ Channel {mux_channel} 선택...")
        if not tester.select_mux_channel():
            print("   ❌ 채널 선택 실패")
            return False
        
        # 3. 채널 내 장치 스캔
        print(f"\n3️⃣ Channel {mux_channel} 장치 스캔...")
        devices = tester.scan_channel_devices()
        
        if sensor_address not in devices:
            print(f"   ❌ SDP800 센서(0x{sensor_address:02X})를 찾을 수 없습니다")
            print("   🔍 다른 주소들도 확인해보세요:")
            for addr in [0x25, 0x26]:  # SDP800 가능한 주소들
                if addr in devices:
                    print(f"      ✅ 0x{addr:02X}에서 장치 발견됨")
            return False
        
        # 4. SDP800 센서 테스트
        print(f"\n4️⃣ SDP800 센서 테스트...")
        success, pressure = tester.test_sdp800_communication()
        
        if not success:
            print("   ❌ SDP800 센서 테스트 실패")
            return False
        
        # 5. 연속 측정 테스트
        print(f"\n5️⃣ 연속 측정 테스트...")
        measurements = tester.continuous_measurement(5)  # 5초간 측정
        
        # 6. 센서 정보 출력
        print(f"\n6️⃣ 센서 정보:")
        for key, value in tester.sensor_info.items():
            print(f"   {key}: {value}")
        
        print("\n" + "=" * 70)
        print("✅ SDP800 센서 테스트 성공!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        return False
        
    finally:
        if 'tester' in locals() and tester.bus:
            tester.bus.close()
        print(f"\n⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)