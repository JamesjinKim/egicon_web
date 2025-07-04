#!/usr/bin/env python3
"""
EG-ICON Hardware Scanner
========================
TCA9548A 이중 멀티플렉서 + 센서 스캔 시스템
ref 폴더의 i2c_scanner.py와 simpleTCA9548A.py 기반
"""

import subprocess
import time
import platform
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# I2C 라이브러리 (라즈베리파이에서만 사용)
try:
    import smbus2
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False

class HardwareScanner:
    """하드웨어 스캔 및 센서 감지 클래스"""
    
    # 센서 주소 매핑 (ref/i2c_scanner.py 기반)
    SENSOR_ADDRESSES = {
        "SHT40": [0x44, 0x45],
        "BME688": [0x76, 0x77], 
        "BH1750": [0x23, 0x5C],
        "SDP810": [0x25],
        "VL53L0X": [0x29]
    }
    
    # TCA9548A 주소 범위
    TCA9548A_ADDRESSES = list(range(0x70, 0x78))
    
    def __init__(self):
        self.is_raspberry_pi = self._check_raspberry_pi()
        self.buses = {}  # {bus_number: smbus_object}
        self.tca_info = {}  # {bus_number: {'address': addr, 'channels': []}}
        
        if self.is_raspberry_pi and I2C_AVAILABLE:
            self._init_i2c_buses()
            self._detect_tca9548a()
        
    def _check_raspberry_pi(self) -> bool:
        """라즈베리파이 환경 확인"""
        try:
            # /proc/cpuinfo에서 라즈베리파이 확인
            with open('/proc/cpuinfo', 'r') as f:
                content = f.read()
                if 'Raspberry Pi' in content or 'BCM' in content:
                    return True
        except:
            pass
        
        # 플랫폼 정보로 ARM 확인
        return platform.machine().startswith('arm') or platform.machine().startswith('aarch')
    
    def _init_i2c_buses(self):
        """I2C 버스 0, 1 초기화"""
        for bus_num in [0, 1]:
            try:
                bus = smbus2.SMBus(bus_num)
                self.buses[bus_num] = bus
                print(f"I2C 버스 {bus_num} 초기화 성공")
            except Exception as e:
                print(f"I2C 버스 {bus_num} 초기화 실패: {e}")
    
    def _detect_tca9548a(self):
        """TCA9548A 멀티플렉서 감지 (simpleTCA9548A.py 기반)"""
        for bus_num, bus in self.buses.items():
            for addr in self.TCA9548A_ADDRESSES:
                try:
                    # TCA9548A 응답 테스트
                    bus.write_byte(addr, 0x00)  # 모든 채널 비활성화
                    self.tca_info[bus_num] = {
                        'address': addr,
                        'channels': list(range(8))
                    }
                    print(f"TCA9548A 발견: Bus {bus_num}, 주소 0x{addr:02X}")
                    break
                except:
                    try:
                        # 읽기 테스트
                        bus.read_byte(addr)
                        self.tca_info[bus_num] = {
                            'address': addr,
                            'channels': list(range(8))
                        }
                        print(f"TCA9548A 발견: Bus {bus_num}, 주소 0x{addr:02X}")
                        break
                    except:
                        continue
    
    def _select_channel(self, bus_num: int, channel: int) -> bool:
        """TCA9548A 채널 선택"""
        if not self.is_raspberry_pi or not I2C_AVAILABLE:
            return True  # Mock 모드에서는 항상 성공
            
        if bus_num not in self.tca_info:
            return False
            
        tca_addr = self.tca_info[bus_num]['address']
        bus = self.buses[bus_num]
        
        try:
            bus.write_byte(tca_addr, 1 << channel)
            time.sleep(0.05)  # 채널 전환 대기
            return True
        except Exception as e:
            print(f"채널 선택 실패 Bus {bus_num}, Ch {channel}: {e}")
            return False
    
    def _disable_all_channels(self, bus_num: int):
        """TCA9548A 모든 채널 비활성화"""
        if not self.is_raspberry_pi or not I2C_AVAILABLE:
            return
            
        if bus_num not in self.tca_info:
            return
            
        tca_addr = self.tca_info[bus_num]['address']
        bus = self.buses[bus_num]
        
        try:
            bus.write_byte(tca_addr, 0x00)
        except Exception as e:
            print(f"채널 비활성화 실패 Bus {bus_num}: {e}")
    
    def _detect_sensor_type(self, bus_num: int, address: int) -> Optional[str]:
        """주소 기반 센서 타입 감지"""
        for sensor_type, addresses in self.SENSOR_ADDRESSES.items():
            if address in addresses:
                return sensor_type
        return "Unknown"
    
    def _test_sensor_communication(self, bus_num: int, address: int, sensor_type: str) -> bool:
        """센서별 통신 테스트 (ref/i2c_scanner.py 기반)"""
        if not self.is_raspberry_pi or not I2C_AVAILABLE:
            return True  # Mock 모드
            
        bus = self.buses[bus_num]
        
        try:
            if sensor_type == "SHT40":
                # SHT40 소프트 리셋 테스트
                write_msg = smbus2.i2c_msg.write(address, [0x94])  # 소프트 리셋
                bus.i2c_rdwr(write_msg)
                time.sleep(0.01)
                return True
                
            elif sensor_type == "BME688":
                # BME688 칩 ID 확인
                chip_id = bus.read_byte_data(address, 0xD0)
                return chip_id == 0x61
                
            elif sensor_type == "BH1750":
                # BH1750 전원 켜기 테스트
                write_msg = smbus2.i2c_msg.write(address, [0x01])  # 전원 켜기
                bus.i2c_rdwr(write_msg)
                time.sleep(0.05)
                return True
                
            else:
                # 기본 읽기 테스트
                bus.read_byte(address)
                return True
                
        except Exception as e:
            print(f"센서 통신 테스트 실패 {sensor_type} 0x{address:02X}: {e}")
            return False
    
    def scan_bus_direct(self, bus_num: int) -> List[Dict]:
        """버스 직접 스캔 (TCA9548A 없이)"""
        devices = []
        
        if not self.is_raspberry_pi or not I2C_AVAILABLE:
            # Mock 데이터 반환
            mock_devices = [
                {"address": "0x44", "sensor_type": "SHT40", "status": "connected"},
                {"address": "0x76", "sensor_type": "BME688", "status": "connected"}
            ]
            return mock_devices
        
        if bus_num not in self.buses:
            return devices
            
        bus = self.buses[bus_num]
        
        # 주요 센서 주소 스캔
        all_addresses = []
        for addresses in self.SENSOR_ADDRESSES.values():
            all_addresses.extend(addresses)
        
        for addr in set(all_addresses):
            try:
                bus.read_byte(addr)
                sensor_type = self._detect_sensor_type(bus_num, addr)
                comm_ok = self._test_sensor_communication(bus_num, addr, sensor_type)
                
                devices.append({
                    "address": f"0x{addr:02X}",
                    "sensor_type": sensor_type,
                    "status": "connected" if comm_ok else "detected"
                })
                
            except Exception:
                continue
        
        return devices
    
    def scan_bus_with_mux(self, bus_num: int) -> Dict[int, List[Dict]]:
        """TCA9548A 멀티플렉서를 통한 버스 스캔"""
        results = {}
        
        if not self.is_raspberry_pi or not I2C_AVAILABLE:
            # Mock 데이터 반환
            mock_results = {}
            for ch in range(8):
                if ch < 3:  # 처음 3개 채널에만 센서 시뮬레이션
                    mock_results[ch] = [
                        {"address": "0x44", "sensor_type": "SHT40", "status": "connected"}
                    ]
                else:
                    mock_results[ch] = []
            return mock_results
        
        if bus_num not in self.tca_info:
            return results
        
        # 각 채널별 스캔
        for channel in range(8):
            results[channel] = []
            
            if not self._select_channel(bus_num, channel):
                continue
            
            # 채널에서 센서 검색
            channel_devices = self.scan_bus_direct(bus_num)
            results[channel] = channel_devices
            
            self._disable_all_channels(bus_num)
        
        return results
    
    def scan_dual_mux_system(self) -> Dict:
        """이중 멀티플렉서 시스템 전체 스캔"""
        scan_result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "mode": "hardware" if (self.is_raspberry_pi and I2C_AVAILABLE) else "mock",
            "buses": {},
            "sensors": [],
            "i2c_devices": []
        }
        
        try:
            for bus_num in [0, 1]:
                bus_info = {
                    "bus": bus_num,
                    "tca9548a_detected": bus_num in self.tca_info,
                    "channels": {}
                }
                
                if bus_num in self.tca_info:
                    # TCA9548A를 통한 스캔
                    channel_results = self.scan_bus_with_mux(bus_num)
                    bus_info["channels"] = channel_results
                    bus_info["tca9548a_address"] = f"0x{self.tca_info[bus_num]['address']:02X}"
                    
                    # 센서 목록 구성
                    for channel, devices in channel_results.items():
                        for device in devices:
                            sensor_data = {
                                "bus": bus_num,
                                "mux_channel": channel,
                                "address": device["address"],
                                "sensor_name": device["sensor_type"],
                                "sensor_type": device["sensor_type"],
                                "status": device["status"]
                            }
                            scan_result["sensors"].append(sensor_data)
                            scan_result["i2c_devices"].append(sensor_data)
                else:
                    # 직접 스캔
                    direct_devices = self.scan_bus_direct(bus_num)
                    bus_info["direct_devices"] = direct_devices
                    
                    for device in direct_devices:
                        sensor_data = {
                            "bus": bus_num,
                            "mux_channel": None,
                            "address": device["address"],
                            "sensor_name": device["sensor_type"],
                            "sensor_type": device["sensor_type"],
                            "status": device["status"]
                        }
                        scan_result["sensors"].append(sensor_data)
                        scan_result["i2c_devices"].append(sensor_data)
                
                scan_result["buses"][bus_num] = bus_info
            
        except Exception as e:
            scan_result["success"] = False
            scan_result["error"] = str(e)
        
        return scan_result
    
    def close(self):
        """리소스 정리"""
        if self.is_raspberry_pi and I2C_AVAILABLE:
            for bus_num, bus in self.buses.items():
                try:
                    if bus_num in self.tca_info:
                        self._disable_all_channels(bus_num)
                    bus.close()
                except Exception as e:
                    print(f"버스 {bus_num} 정리 실패: {e}")
        self.buses.clear()
        self.tca_info.clear()

# 전역 스캐너 인스턴스
_scanner_instance = None

def get_scanner() -> HardwareScanner:
    """싱글톤 스캐너 인스턴스 반환"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = HardwareScanner()
    return _scanner_instance

def cleanup_scanner():
    """스캐너 정리"""
    global _scanner_instance
    if _scanner_instance:
        _scanner_instance.close()
        _scanner_instance = None

# 테스트 코드
if __name__ == "__main__":
    try:
        scanner = HardwareScanner()
        print(f"라즈베리파이 환경: {scanner.is_raspberry_pi}")
        print(f"I2C 사용 가능: {I2C_AVAILABLE}")
        
        print("\n=== 이중 멀티플렉서 시스템 스캔 ===")
        result = scanner.scan_dual_mux_system()
        
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"오류: {e}")
    finally:
        scanner.close()