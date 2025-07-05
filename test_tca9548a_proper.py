#!/usr/bin/env python3
"""
TCA9548A 올바른 채널 선택 테스트
==============================
ref/tca9548a.py 방식에 따른 채널 선택 및 센서 테스트
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

class TCA9548AProper:
    """올바른 TCA9548A 채널 선택 클래스"""
    
    def __init__(self, bus_num=1):
        self.bus_num = bus_num
        self.bus = None
        # TCA9548A 주소 배열 (ref/tca9548a.py 방식)
        self.TCA9548A_ADDRESS = [0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77]
    
    def connect(self):
        """I2C 버스 연결"""
        try:
            self.bus = smbus2.SMBus(self.bus_num)
            return True
        except Exception as e:
            print(f"❌ I2C 버스 연결 실패: {e}")
            return False
    
    def tca9548a_select_channel(self, hub_id, channel):
        """
        TCA9548A 채널 선택 (ref/tca9548a.py 방식)
        
        Args:
            hub_id: TCA9548A ID (0=0x70, 1=0x71, ...)
            channel: 채널 번호 (0-7)
        """
        try:
            tca_address = self.TCA9548A_ADDRESS[hub_id]
            
            print(f"📡 TCA9548A 채널 선택: Hub{hub_id}(0x{tca_address:02X}) Channel{channel}")
            
            # 1단계: 모든 채널 비활성화 (중요!)
            self.bus.write_byte(tca_address, 0)
            time.sleep(0.01)
            
            # 2단계: 특정 채널만 활성화
            channel_mask = 1 << channel
            self.bus.write_byte(tca_address, channel_mask)
            time.sleep(0.01)
            
            # 3단계: 채널 선택 확인
            selected_channel = self.bus.read_byte(tca_address)
            
            if selected_channel == channel_mask:
                print(f"   ✅ 채널 선택 성공: 0x{selected_channel:02X}")
                return True
            else:
                print(f"   ❌ 채널 선택 실패: 요청=0x{channel_mask:02X}, 실제=0x{selected_channel:02X}")
                return False
                
        except Exception as e:
            print(f"   ❌ TCA9548A 채널 선택 실패: {e}")
            return False
    
    def scan_channel_devices(self, hub_id, channel):
        """특정 채널의 I2C 장치 스캔"""
        
        if not self.tca9548a_select_channel(hub_id, channel):
            return []
        
        print(f"🔍 Hub{hub_id} Channel{channel} 장치 스캔...")
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
                print("   ❌ 장치 없음")
            
            return found_devices
            
        except Exception as e:
            print(f"   ❌ 스캔 실패: {e}")
            return []
    
    def _identify_device(self, address):
        """주소로 장치 타입 식별"""
        device_map = {
            0x25: "SDP810",
            0x44: "SHT40",
            0x45: "SHT40",
            0x76: "BME688/BME680",
            0x77: "BME688/BME680",
            0x23: "BH1750",
            0x5C: "BH1750",
            0x70: "TCA9548A",
            0x71: "TCA9548A",
        }
        return device_map.get(address, "Unknown")
    
    def test_sensor_communication(self, hub_id, channel, sensor_address, sensor_type):
        """센서 통신 테스트"""
        
        print(f"\n🧪 센서 통신 테스트: {sensor_type} (0x{sensor_address:02X})")
        print("-" * 50)
        
        if not self.tca9548a_select_channel(hub_id, channel):
            return False
        
        try:
            if sensor_type.startswith("SDP"):
                return self._test_sdp800(sensor_address)
            elif sensor_type == "SHT40":
                return self._test_sht40(sensor_address)
            elif sensor_type.startswith("BME"):
                return self._test_bme688(sensor_address)
            else:
                # 기본 응답 테스트
                self.bus.read_byte(sensor_address)
                print(f"   ✅ {sensor_type} 기본 응답 확인")
                return True
                
        except Exception as e:
            print(f"   ❌ {sensor_type} 통신 실패: {e}")
            return False
    
    def _test_sdp800(self, address):
        """SDP800 센서 테스트"""
        try:
            # SDP800 3바이트 읽기
            read_msg = smbus2.i2c_msg.read(address, 3)
            self.bus.i2c_rdwr(read_msg)
            raw_data = list(read_msg)
            
            if len(raw_data) == 3:
                import struct
                pressure_msb = raw_data[0]
                pressure_lsb = raw_data[1]
                raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]
                pressure_pa = raw_pressure / 60.0
                
                print(f"   ✅ SDP800 압력: {pressure_pa:.2f} Pa")
                return True
            
            return False
            
        except Exception as e:
            print(f"   ❌ SDP800 테스트 실패: {e}")
            return False
    
    def _test_sht40(self, address):
        """SHT40 센서 테스트"""
        try:
            # SHT40 소프트 리셋
            self.bus.write_byte(address, 0x94)
            time.sleep(0.1)
            
            # 측정 명령
            self.bus.write_byte(address, 0xFD)
            time.sleep(0.02)
            
            # 6바이트 읽기
            read_msg = smbus2.i2c_msg.read(address, 6)
            self.bus.i2c_rdwr(read_msg)
            data = list(read_msg)
            
            if len(data) == 6:
                temp_raw = (data[0] << 8) | data[1]
                humidity_raw = (data[3] << 8) | data[4]
                temperature = -45 + 175 * (temp_raw / 65535.0)
                humidity = max(0, min(100, -6 + 125 * (humidity_raw / 65535.0)))
                
                print(f"   ✅ SHT40 온도: {temperature:.2f}°C, 습도: {humidity:.2f}%RH")
                return True
            
            return False
            
        except Exception as e:
            print(f"   ❌ SHT40 테스트 실패: {e}")
            return False
    
    def _test_bme688(self, address):
        """BME688 센서 테스트"""
        try:
            # BME688 칩 ID 읽기 (0xD0 레지스터)
            chip_id = self.bus.read_byte_data(address, 0xD0)
            if chip_id == 0x61:  # BME688 칩 ID
                print(f"   ✅ BME688 칩 ID 확인: 0x{chip_id:02X}")
                return True
            else:
                print(f"   ⚠️ 예상과 다른 칩 ID: 0x{chip_id:02X}")
                return False
                
        except Exception as e:
            print(f"   ❌ BME688 테스트 실패: {e}")
            return False
    
    def close(self):
        """I2C 버스 해제"""
        if self.bus:
            self.bus.close()
            self.bus = None

def main():
    """메인 테스트 함수"""
    
    print("=" * 70)
    print("🚀 TCA9548A 올바른 채널 선택 테스트")
    print("=" * 70)
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tca = TCA9548AProper()
    
    try:
        # I2C 연결
        if not tca.connect():
            return False
        
        # Hub 0 (0x70) 테스트
        hub_id = 0
        print(f"🔍 Hub {hub_id} (0x{tca.TCA9548A_ADDRESS[hub_id]:02X}) 테스트")
        print("=" * 50)
        
        # 모든 채널 스캔
        for channel in range(8):
            print(f"\n📡 Channel {channel} 테스트:")
            devices = tca.scan_channel_devices(hub_id, channel)
            
            # 센서별 통신 테스트
            for device_addr in devices:
                if device_addr != 0x70:  # TCA9548A 제외
                    device_type = tca._identify_device(device_addr)
                    if device_type != "Unknown":
                        tca.test_sensor_communication(hub_id, channel, device_addr, device_type)
        
        print("\n" + "=" * 70)
        print("✅ TCA9548A 테스트 완료!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False
        
    finally:
        tca.close()
        print(f"⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)