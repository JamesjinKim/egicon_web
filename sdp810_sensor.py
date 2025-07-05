#!/usr/bin/env python3
"""
SDP810 차압센서 모듈
==================
Sensirion SDP810 차압센서를 위한 전용 클래스
find_sdp800.py 및 test_sdp800_ch2.py 기반으로 SDP810용으로 표준화
"""

import sys
import time
import struct
from datetime import datetime
from typing import Optional, Tuple, List, Dict

# I2C 라이브러리
try:
    import smbus2
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False

class SDP810Sensor:
    """SDP810 차압센서 클래스"""
    
    # SDP810 표준 주소
    SDP810_ADDRESS = 0x25
    
    def __init__(self, bus_num: int = 1, mux_address: int = 0x70, mux_channel: Optional[int] = None):
        """
        SDP810 센서 초기화
        
        Args:
            bus_num: I2C 버스 번호 (기본값: 1)
            mux_address: TCA9548A 멀티플렉서 주소 (기본값: 0x70)
            mux_channel: 멀티플렉서 채널 (None이면 직접 연결)
        """
        self.bus_num = bus_num
        self.mux_address = mux_address
        self.mux_channel = mux_channel
        self.bus = None
        self.is_connected = False
        
        # 센서 정보
        self.sensor_info = {
            "name": "SDP810",
            "manufacturer": "Sensirion",
            "measurement_type": "Differential Pressure",
            "pressure_range": "±500 Pa",
            "accuracy": "±1.5% of reading",
            "interface": "I2C",
            "address": f"0x{self.SDP810_ADDRESS:02X}",
            "scaling_factor": 60.0
        }
    
    def _calculate_crc8(self, data: List[int]) -> int:
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
    
    def connect(self) -> bool:
        """I2C 연결 및 센서 초기화"""
        if not I2C_AVAILABLE:
            print("❌ I2C 라이브러리가 설치되지 않음")
            return False
        
        try:
            self.bus = smbus2.SMBus(self.bus_num)
            
            # 멀티플렉서 채널 선택 (필요시)
            if self.mux_channel is not None:
                if not self._select_mux_channel():
                    return False
            
            # 센서 응답 테스트
            self.bus.read_byte(self.SDP810_ADDRESS)
            
            # 압력 읽기 테스트
            pressure, crc_ok, message = self._read_pressure_data()
            if pressure is not None:
                self.is_connected = True
                print(f"✅ SDP810 센서 연결 성공 (압력: {pressure:.2f} Pa)")
                return True
            else:
                print(f"❌ SDP810 센서 통신 실패: {message}")
                return False
                
        except Exception as e:
            print(f"❌ SDP810 센서 연결 실패: {e}")
            return False
    
    def _select_mux_channel(self) -> bool:
        """TCA9548A 멀티플렉서 채널 선택"""
        try:
            # ref/tca9548a.py 방식: 초기화 후 채널 선택
            self.bus.write_byte(self.mux_address, 0)  # 모든 채널 비활성화
            time.sleep(0.01)
            
            channel_mask = 1 << self.mux_channel
            self.bus.write_byte(self.mux_address, channel_mask)
            time.sleep(0.01)
            
            # 채널 선택 확인
            current_channel = self.bus.read_byte(self.mux_address)
            if current_channel == channel_mask:
                return True
            else:
                print(f"❌ 채널 선택 실패: 요청={channel_mask:02X}, 실제={current_channel:02X}")
                return False
                
        except Exception as e:
            print(f"❌ 멀티플렉서 채널 선택 실패: {e}")
            return False
    
    def _read_pressure_data(self) -> Tuple[Optional[float], bool, str]:
        """SDP810 압력 데이터 읽기"""
        try:
            # 3바이트 읽기: [pressure_msb, pressure_lsb, crc]
            read_msg = smbus2.i2c_msg.read(self.SDP810_ADDRESS, 3)
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
            pressure_pa = raw_pressure / self.sensor_info["scaling_factor"]
            
            # 범위 제한 (±500 Pa)
            pressure_pa = max(-500.0, min(500.0, pressure_pa))
            
            return pressure_pa, crc_ok, "OK"
            
        except Exception as e:
            return None, False, f"읽기 오류: {e}"
    
    def read_pressure(self) -> Optional[float]:
        """압력 읽기 (단일 측정)"""
        if not self.is_connected:
            print("❌ 센서가 연결되지 않음")
            return None
        
        # 멀티플렉서 채널 재선택 (필요시)
        if self.mux_channel is not None:
            if not self._select_mux_channel():
                return None
        
        pressure, crc_ok, message = self._read_pressure_data()
        
        if pressure is not None and crc_ok:
            return pressure
        else:
            print(f"❌ 압력 읽기 실패: {message}")
            return None
    
    def read_pressure_with_crc(self) -> Tuple[Optional[float], bool, str]:
        """압력 읽기 (CRC 정보 포함)"""
        if not self.is_connected:
            return None, False, "센서가 연결되지 않음"
        
        # 멀티플렉서 채널 재선택 (필요시)
        if self.mux_channel is not None:
            if not self._select_mux_channel():
                return None, False, "채널 선택 실패"
        
        return self._read_pressure_data()
    
    def continuous_measurement(self, duration: int = 10, interval: float = 1.0) -> List[Dict]:
        """연속 측정"""
        measurements = []
        
        print(f"📈 SDP810 연속 측정 시작 ({duration}초, {interval}초 간격)")
        
        for i in range(duration):
            try:
                pressure, crc_ok, message = self.read_pressure_with_crc()
                
                measurement = {
                    "timestamp": datetime.now().isoformat(),
                    "measurement_number": i + 1,
                    "pressure_pa": pressure,
                    "crc_valid": crc_ok,
                    "message": message
                }
                
                measurements.append(measurement)
                
                if pressure is not None:
                    status = "✅" if crc_ok else "⚠️"
                    print(f"   {i+1:2d}초: {pressure:6.2f} Pa {status}")
                else:
                    print(f"   {i+1:2d}초: 측정 실패 - {message}")
                
                if i < duration - 1:  # 마지막 측정이 아닌 경우만 대기
                    time.sleep(interval)
                
            except Exception as e:
                measurement = {
                    "timestamp": datetime.now().isoformat(),
                    "measurement_number": i + 1,
                    "pressure_pa": None,
                    "crc_valid": False,
                    "message": f"오류: {e}"
                }
                measurements.append(measurement)
                print(f"   {i+1:2d}초: 오류 - {e}")
        
        # 측정 통계
        valid_measurements = [m["pressure_pa"] for m in measurements if m["pressure_pa"] is not None]
        
        if valid_measurements:
            avg_pressure = sum(valid_measurements) / len(valid_measurements)
            min_pressure = min(valid_measurements)
            max_pressure = max(valid_measurements)
            
            print(f"\n📊 측정 통계:")
            print(f"   평균: {avg_pressure:.2f} Pa")
            print(f"   최소: {min_pressure:.2f} Pa")
            print(f"   최대: {max_pressure:.2f} Pa")
            print(f"   범위: {max_pressure - min_pressure:.2f} Pa")
            print(f"   성공률: {len(valid_measurements)}/{duration} ({len(valid_measurements)/duration*100:.1f}%)")
        
        return measurements
    
    def get_sensor_info(self) -> Dict:
        """센서 정보 반환"""
        info = self.sensor_info.copy()
        info.update({
            "bus_number": self.bus_num,
            "mux_address": f"0x{self.mux_address:02X}" if self.mux_channel is not None else None,
            "mux_channel": self.mux_channel,
            "connection_status": "connected" if self.is_connected else "disconnected"
        })
        return info
    
    def test_communication(self) -> bool:
        """센서 통신 테스트"""
        print(f"🧪 SDP810 센서 통신 테스트...")
        
        try:
            # 기본 응답 테스트
            self.bus.read_byte(self.SDP810_ADDRESS)
            print("   ✅ 센서가 I2C 주소에서 응답함")
            
            # 압력 데이터 읽기 테스트
            pressure, crc_ok, message = self._read_pressure_data()
            
            if pressure is not None:
                print(f"   ✅ 압력 읽기 성공: {pressure:.2f} Pa")
                print(f"   🔍 CRC 검증: {'✅ 성공' if crc_ok else '❌ 실패'}")
                return True
            else:
                print(f"   ❌ 압력 읽기 실패: {message}")
                return False
                
        except Exception as e:
            print(f"   ❌ 통신 테스트 실패: {e}")
            return False
    
    def close(self):
        """연결 해제"""
        if self.bus:
            try:
                # 멀티플렉서 채널 비활성화 (필요시)
                if self.mux_channel is not None:
                    self.bus.write_byte(self.mux_address, 0)
                self.bus.close()
            except Exception as e:
                print(f"⚠️ 연결 해제 중 오류: {e}")
            finally:
                self.bus = None
                self.is_connected = False

def scan_sdp810_sensors(bus_numbers: List[int] = [0, 1], mux_address: int = 0x70) -> List[Dict]:
    """
    모든 버스와 채널에서 SDP810 센서 검색
    
    Args:
        bus_numbers: 검색할 I2C 버스 번호 리스트
        mux_address: TCA9548A 멀티플렉서 주소
    
    Returns:
        발견된 SDP810 센서 정보 리스트
    """
    print("🔍 SDP810 센서 전체 검색 시작...")
    found_sensors = []
    
    if not I2C_AVAILABLE:
        print("❌ I2C 라이브러리가 설치되지 않음")
        return found_sensors
    
    for bus_num in bus_numbers:
        try:
            bus = smbus2.SMBus(bus_num)
            print(f"🚌 Bus {bus_num} 검색 중...")
            
            # 직접 연결 확인
            try:
                bus.read_byte(SDP810Sensor.SDP810_ADDRESS)
                sensor = SDP810Sensor(bus_num=bus_num, mux_channel=None)
                if sensor.connect():
                    sensor_info = {
                        "bus": bus_num,
                        "mux_channel": None,
                        "address": f"0x{SDP810Sensor.SDP810_ADDRESS:02X}",
                        "sensor_type": "SDP810",
                        "connection_type": "direct"
                    }
                    found_sensors.append(sensor_info)
                    print(f"   ✅ Bus {bus_num} 직접: SDP810 발견")
                sensor.close()
            except:
                pass
            
            # 멀티플렉서를 통한 검색
            try:
                # TCA9548A 응답 확인
                bus.read_byte(mux_address)
                print(f"   🔍 TCA9548A 멀티플렉서 발견 (0x{mux_address:02X})")
                
                # 각 채널 검색
                for channel in range(8):
                    try:
                        # 채널 선택
                        bus.write_byte(mux_address, 0)  # 초기화
                        time.sleep(0.01)
                        channel_mask = 1 << channel
                        bus.write_byte(mux_address, channel_mask)
                        time.sleep(0.01)
                        
                        # SDP810 확인
                        bus.read_byte(SDP810Sensor.SDP810_ADDRESS)
                        
                        sensor = SDP810Sensor(bus_num=bus_num, mux_address=mux_address, mux_channel=channel)
                        if sensor.connect():
                            sensor_info = {
                                "bus": bus_num,
                                "mux_channel": channel,
                                "mux_address": f"0x{mux_address:02X}",
                                "address": f"0x{SDP810Sensor.SDP810_ADDRESS:02X}",
                                "sensor_type": "SDP810",
                                "connection_type": "multiplexed"
                            }
                            found_sensors.append(sensor_info)
                            print(f"   ✅ Bus {bus_num} CH{channel}: SDP810 발견")
                        sensor.close()
                        
                        # 채널 비활성화
                        bus.write_byte(mux_address, 0)
                        
                    except:
                        continue
                        
            except:
                print(f"   ⚪ Bus {bus_num}: TCA9548A 없음")
            
            bus.close()
            
        except Exception as e:
            print(f"❌ Bus {bus_num} 검색 실패: {e}")
    
    print(f"📊 SDP810 검색 완료: {len(found_sensors)}개 센서 발견")
    return found_sensors

# 테스트 코드
if __name__ == "__main__":
    print("🚀 SDP810 센서 테스트 시작")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 전체 센서 검색
    print("\n=== SDP810 센서 검색 ===")
    found_sensors = scan_sdp810_sensors()
    
    if found_sensors:
        print(f"\n✅ {len(found_sensors)}개 SDP810 센서 발견:")
        for i, sensor_info in enumerate(found_sensors, 1):
            print(f"   {i}. Bus {sensor_info['bus']}")
            if sensor_info['mux_channel'] is not None:
                print(f"      멀티플렉서: {sensor_info['mux_address']} Channel {sensor_info['mux_channel']}")
            else:
                print(f"      연결: 직접 연결")
            print(f"      주소: {sensor_info['address']}")
        
        # 2. 첫 번째 센서로 테스트
        print(f"\n=== 첫 번째 센서 테스트 ===")
        first_sensor = found_sensors[0]
        
        sensor = SDP810Sensor(
            bus_num=first_sensor['bus'],
            mux_channel=first_sensor.get('mux_channel')
        )
        
        if sensor.connect():
            # 센서 정보 출력
            info = sensor.get_sensor_info()
            print("📋 센서 정보:")
            for key, value in info.items():
                print(f"   {key}: {value}")
            
            # 통신 테스트
            sensor.test_communication()
            
            # 연속 측정 (5초)
            print(f"\n=== 연속 측정 테스트 ===")
            measurements = sensor.continuous_measurement(duration=5, interval=1.0)
            
            sensor.close()
        
    else:
        print("❌ SDP810 센서를 찾을 수 없습니다.")
    
    print(f"\n⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")