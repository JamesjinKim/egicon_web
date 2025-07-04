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
import glob
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# I2C 라이브러리 (라즈베리파이에서만 사용)
try:
    import smbus2
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False

# SPS30 UART 센서 라이브러리
try:
    from shdlc_sps30 import Sps30ShdlcDevice
    from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
    from sensirion_shdlc_driver.errors import ShdlcError
    SPS30_AVAILABLE = True
except ImportError:
    SPS30_AVAILABLE = False

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
    
    # UART 센서 정보
    UART_SENSORS = {
        "SPS30": {
            "name": "SPS30 미세먼지 센서",
            "manufacturer": "Sensirion",
            "measurements": ["PM1.0", "PM2.5", "PM4.0", "PM10"],
            "units": "μg/m³"
        }
    }
    
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
                print(f"✅ I2C 버스 {bus_num} 초기화 성공")
            except Exception as e:
                print(f"❌ I2C 버스 {bus_num} 초기화 실패: {e}")
        
        print(f"📋 총 {len(self.buses)}개 I2C 버스 활성화: {list(self.buses.keys())}")
    
    def _detect_tca9548a(self):
        """TCA9548A 멀티플렉서 감지 (simpleTCA9548A.py 기반) - 이중 버스 지원"""
        print(f"🔍 TCA9548A 감지 시작: {len(self.buses)}개 버스 확인")
        
        # 각 버스별로 순환하며 독립적으로 TCA9548A 감지
        for bus_num in sorted(self.buses.keys()):  # 순서 보장
            bus = self.buses[bus_num]
            tca_found = False
            print(f"  📋 Bus {bus_num} TCA9548A 스캔 중...")
            
            # TCA9548A 주소 범위 순환 테스트
            for addr in self.TCA9548A_ADDRESSES:
                try:
                    print(f"    🔍 주소 0x{addr:02X} 테스트 중...")
                    # TCA9548A 응답 테스트 (write 방식)
                    bus.write_byte(addr, 0x00)  # 모든 채널 비활성화
                    self.tca_info[bus_num] = {
                        'address': addr,
                        'channels': list(range(8))
                    }
                    print(f"    ✅ TCA9548A 발견: Bus {bus_num}, 주소 0x{addr:02X} (write 방식)")
                    tca_found = True
                    break
                except Exception as e1:
                    try:
                        # 읽기 테스트 (read 방식)
                        response = bus.read_byte(addr)
                        self.tca_info[bus_num] = {
                            'address': addr,
                            'channels': list(range(8))
                        }
                        print(f"    ✅ TCA9548A 발견: Bus {bus_num}, 주소 0x{addr:02X} (read 방식, 응답: 0x{response:02X})")
                        tca_found = True
                        break
                    except Exception as e2:
                        print(f"    ⚪ 주소 0x{addr:02X}: 응답 없음")
                        continue
            
            if not tca_found:
                print(f"  ❌ Bus {bus_num}: TCA9548A 미발견")
            else:
                print(f"  ✅ Bus {bus_num}: TCA9548A 감지 완료")
        
        print(f"🏁 TCA9548A 감지 완료: {len(self.tca_info)}개 발견 {list(self.tca_info.keys())}")
    
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
    
    def _find_sps30_uart(self) -> Tuple[Optional[str], Optional[str]]:
        """
        SPS30 UART 센서 자동 검색 (ref/sps30_sensor.py 기반)
        
        Returns:
            Tuple[port_path, serial_number]: (시리얼 포트 경로, 시리얼 번호)
            실패 시 (None, None) 반환
        """
        if not SPS30_AVAILABLE:
            print("⚠️ SPS30 라이브러리가 설치되지 않음 - UART 스캔 건너뜀")
            return None, None
        
        print("🔍 SPS30 UART 센서 검색 중...")
        
        # USB 시리얼 포트 후보들 검색
        port_candidates = []
        port_candidates.extend(glob.glob('/dev/ttyUSB*'))  # USB-Serial 어댑터
        port_candidates.extend(glob.glob('/dev/ttyACM*'))  # Arduino/Micro 타입
        port_candidates.extend(glob.glob('/dev/ttyAMA*'))  # 라즈베리파이 UART
        
        if not port_candidates:
            print("❌ UART 시리얼 포트를 찾을 수 없음")
            return None, None
        
        print(f"📋 UART 포트 후보: {port_candidates}")
        
        # 각 포트에서 SPS30 센서 검색
        for port_path in port_candidates:
            try:
                print(f"🔌 UART 포트 테스트 중: {port_path}")
                
                with ShdlcSerialPort(port=port_path, baudrate=115200) as port:
                    device = Sps30ShdlcDevice(ShdlcConnection(port))
                    
                    # 센서 정보 읽기 시도
                    serial_number = device.device_information_serial_number()
                    
                    if serial_number:
                        print(f"✅ SPS30 센서 발견: {port_path} (S/N: {serial_number})")
                        return port_path, serial_number
                        
            except Exception as e:
                print(f"⚠️ UART 포트 {port_path} 테스트 실패: {e}")
                continue
        
        print("❌ SPS30 UART 센서를 찾을 수 없음")
        return None, None
    
    def scan_uart_sensors(self) -> List[Dict]:
        """UART 센서 스캔 (SPS30)"""
        uart_devices = []
        
        if not self.is_raspberry_pi:
            # Mock 데이터 반환 (개발 환경)
            mock_uart = {
                "port": "/dev/ttyUSB0",
                "sensor_type": "SPS30",
                "sensor_name": "SPS30",
                "serial_number": "MOCK_SPS30_12345",
                "status": "connected",
                "interface": "UART",
                "measurements": ["PM1.0", "PM2.5", "PM4.0", "PM10"],
                "units": "μg/m³"
            }
            uart_devices.append(mock_uart)
            print("🔧 Mock 모드: SPS30 UART 센서 시뮬레이션")
            return uart_devices
        
        # SPS30 UART 센서 검색
        port_path, serial_number = self._find_sps30_uart()
        
        if port_path and serial_number:
            uart_device = {
                "port": port_path,
                "sensor_type": "SPS30",
                "sensor_name": "SPS30",
                "serial_number": serial_number,
                "status": "connected",
                "interface": "UART",
                "measurements": self.UART_SENSORS["SPS30"]["measurements"],
                "units": self.UART_SENSORS["SPS30"]["units"]
            }
            uart_devices.append(uart_device)
            print(f"✅ SPS30 UART 센서 스캔 완료: {port_path}")
        
        return uart_devices
    
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
            print(f"❌ Bus {bus_num}가 초기화되지 않음")
            return devices
            
        bus = self.buses[bus_num]
        print(f"🔍 Bus {bus_num} 직접 스캔 시작")
        
        # 주요 센서 주소 스캔
        all_addresses = []
        for addresses in self.SENSOR_ADDRESSES.values():
            all_addresses.extend(addresses)
        
        scan_addresses = sorted(set(all_addresses))
        print(f"  📋 스캔 대상 주소: {[f'0x{addr:02X}' for addr in scan_addresses]}")
        
        for addr in scan_addresses:
            try:
                print(f"    🔍 주소 0x{addr:02X} 테스트 중...")
                bus.read_byte(addr)
                sensor_type = self._detect_sensor_type(bus_num, addr)
                comm_ok = self._test_sensor_communication(bus_num, addr, sensor_type)
                
                devices.append({
                    "address": f"0x{addr:02X}",
                    "sensor_type": sensor_type,
                    "status": "connected" if comm_ok else "detected"
                })
                
                print(f"    ✅ 0x{addr:02X}: {sensor_type} {'연결됨' if comm_ok else '감지됨'}")
                
            except Exception as e:
                print(f"    ⚪ 0x{addr:02X}: 응답 없음 ({str(e)[:50]})")
                continue
        
        print(f"🏁 Bus {bus_num} 직접 스캔 완료: {len(devices)}개 센서")
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
            print(f"⚠️ Bus {bus_num}에 TCA9548A가 감지되지 않음")
            return results
        
        tca_addr = self.tca_info[bus_num]['address']
        print(f"🔍 Bus {bus_num} TCA9548A(0x{tca_addr:02X}) 스캔 시작")
        
        # 각 채널별 스캔
        for channel in range(8):
            results[channel] = []
            print(f"  📡 채널 {channel} 스캔 중...")
            
            if not self._select_channel(bus_num, channel):
                print(f"    ❌ 채널 {channel} 선택 실패")
                continue
            
            # 채널에서 센서 검색
            channel_devices = self.scan_bus_direct(bus_num)
            results[channel] = channel_devices
            
            if channel_devices:
                print(f"    ✅ 채널 {channel}: {len(channel_devices)}개 센서 발견")
            else:
                print(f"    ⚪ 채널 {channel}: 센서 없음")
            
            self._disable_all_channels(bus_num)
        
        total_sensors = sum(len(devices) for devices in results.values())
        print(f"🏁 Bus {bus_num} 스캔 완료: 총 {total_sensors}개 센서")
        
        return results
    
    def scan_single_bus(self, bus_number: int) -> Dict:
        """단일 I2C 버스 스캔 (UART 센서 포함)"""
        scan_result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "mode": "hardware" if (self.is_raspberry_pi and I2C_AVAILABLE) else "mock",
            "buses": {},
            "sensors": [],
            "i2c_devices": [],
            "uart_devices": []
        }
        
        # 매번 스캔 시마다 TCA9548A 재감지 (하드웨어 변경 대응)
        if self.is_raspberry_pi and I2C_AVAILABLE:
            print(f"🔍 Bus {bus_number} 스캔 전 TCA9548A 재감지...")
            self.tca_info.clear()  # 기존 정보 초기화
            self._detect_tca9548a()  # 다시 감지
        
        try:
            bus_info = {
                "bus": bus_number,
                "tca9548a_detected": bus_number in self.tca_info,
                "channels": {}
            }
            
            if bus_number in self.tca_info:
                # TCA9548A를 통한 스캔
                channel_results = self.scan_bus_with_mux(bus_number)
                bus_info["channels"] = channel_results
                bus_info["tca9548a_address"] = f"0x{self.tca_info[bus_number]['address']:02X}"
                
                # 센서 목록 구성
                for channel, devices in channel_results.items():
                    for device in devices:
                        sensor_data = {
                            "bus": bus_number,
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
                direct_devices = self.scan_bus_direct(bus_number)
                bus_info["direct_devices"] = direct_devices
                
                for device in direct_devices:
                    sensor_data = {
                        "bus": bus_number,
                        "mux_channel": None,
                        "address": device["address"],
                        "sensor_name": device["sensor_type"],
                        "sensor_type": device["sensor_type"],
                        "status": device["status"]
                    }
                    scan_result["sensors"].append(sensor_data)
                    scan_result["i2c_devices"].append(sensor_data)
            
            scan_result["buses"][str(bus_number)] = bus_info
            
            # UART 센서 스캔 (버스 번호와 관계없이 전체 시스템에서 한 번만)
            if bus_number == 0:  # 첫 번째 버스에서만 UART 스캔 실행
                print("🔍 UART 센서 스캔 시작...")
                uart_devices = self.scan_uart_sensors()
                scan_result["uart_devices"] = uart_devices
                
                # UART 센서도 전체 센서 목록에 추가
                for uart_device in uart_devices:
                    uart_sensor_data = {
                        "bus": None,
                        "mux_channel": None,
                        "address": None,
                        "port": uart_device["port"],
                        "sensor_name": uart_device["sensor_name"],
                        "sensor_type": uart_device["sensor_type"],
                        "status": uart_device["status"],
                        "interface": "UART",
                        "serial_number": uart_device.get("serial_number"),
                        "measurements": uart_device.get("measurements", []),
                        "units": uart_device.get("units", "")
                    }
                    scan_result["sensors"].append(uart_sensor_data)
            
            i2c_count = len([s for s in scan_result['sensors'] if s.get('interface') != 'UART'])
            uart_count = len([s for s in scan_result['sensors'] if s.get('interface') == 'UART'])
            print(f"✅ Bus {bus_number} 단일 스캔 완료: I2C {i2c_count}개, UART {uart_count}개 센서 발견")
            
        except Exception as e:
            print(f"❌ Bus {bus_number} 단일 스캔 실패: {e}")
            scan_result["success"] = False
            scan_result["error"] = str(e)
        
        return scan_result
    
    def scan_dual_mux_system(self) -> Dict:
        """이중 멀티플렉서 시스템 전체 스캔 (UART 센서 포함)"""
        scan_result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "mode": "hardware" if (self.is_raspberry_pi and I2C_AVAILABLE) else "mock",
            "buses": {},
            "sensors": [],
            "i2c_devices": [],
            "uart_devices": []
        }
        
        # 매번 스캔 시마다 TCA9548A 재감지 (하드웨어 변경 대응)
        if self.is_raspberry_pi and I2C_AVAILABLE:
            print(f"🔍 전체 시스템 스캔 전 TCA9548A 재감지...")
            self.tca_info.clear()  # 기존 정보 초기화
            self._detect_tca9548a()  # 다시 감지
        
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
            
            # UART 센서 스캔 (전체 시스템에서 한 번만)
            print("🔍 UART 센서 스캔 시작...")
            uart_devices = self.scan_uart_sensors()
            scan_result["uart_devices"] = uart_devices
            
            # UART 센서도 전체 센서 목록에 추가
            for uart_device in uart_devices:
                uart_sensor_data = {
                    "bus": None,
                    "mux_channel": None,
                    "address": None,
                    "port": uart_device["port"],
                    "sensor_name": uart_device["sensor_name"],
                    "sensor_type": uart_device["sensor_type"],
                    "status": uart_device["status"],
                    "interface": "UART",
                    "serial_number": uart_device.get("serial_number"),
                    "measurements": uart_device.get("measurements", []),
                    "units": uart_device.get("units", "")
                }
                scan_result["sensors"].append(uart_sensor_data)
            
            i2c_count = len([s for s in scan_result['sensors'] if s.get('interface') != 'UART'])
            uart_count = len([s for s in scan_result['sensors'] if s.get('interface') == 'UART'])
            print(f"✅ 전체 시스템 스캔 완료: I2C {i2c_count}개, UART {uart_count}개 센서 발견")
            
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

def reset_scanner():
    """스캐너 리셋 (TCA9548A 재감지 강제)"""
    global _scanner_instance
    if _scanner_instance and _scanner_instance.is_raspberry_pi:
        print("🔄 스캐너 TCA9548A 정보 리셋")
        _scanner_instance.tca_info.clear()
        _scanner_instance._detect_tca9548a()

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