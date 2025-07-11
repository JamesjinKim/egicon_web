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

# SPS30 UART 센서 라이브러리 (시스템 직접 실행용 - ref/gui_sps30.py와 동일)
try:
    from shdlc_sps30 import Sps30ShdlcDevice
    from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
    from sensirion_shdlc_driver.errors import ShdlcError
    SPS30_AVAILABLE = True
    print("✅ SPS30 라이브러리 로드 성공 (시스템 환경)")
except ImportError as e:
    SPS30_AVAILABLE = False
    print(f"⚠️ SPS30 라이브러리 로드 실패: {e}")
    print("   설치 방법: sudo pip3 install sensirion-shdlc-sps30")
    print("   또는 가상환경 비활성화 후 시스템에서 직접 실행")

# SHT40 센서 모듈
try:
    from sht40_sensor import SHT40Sensor, scan_sht40_sensors
    SHT40_AVAILABLE = True
    print("✅ SHT40 센서 모듈 로드 성공")
except ImportError as e:
    SHT40_AVAILABLE = False
    print(f"⚠️ SHT40 센서 모듈 로드 실패: {e}")

class HardwareScanner:
    """
    TCA9548A 이중 멀티플렉서 시스템 하드웨어 스캔 및 센서 감지 클래스
    
    운영 시 중요사항:
    - 라즈베리파이 환경 자동 감지 후 Mock/실제 모드 분기
    - I2C 버스 0, 1에서 TCA9548A 멀티플렉서 자동 감지
    - 센서별 전용 스캔 기능 (SHT40, SDP810, BME688, BH1750)
    - UART 센서 (SPS30) 포트 자동 검색
    - 하드웨어 변경 대응을 위한 매 스캔마다 TCA9548A 재감지
    - 센서 주소 기반 타입 자동 분류
    """
    
    # 센서 주소 매핑 (ref/i2c_scanner.py 기반)
    SENSOR_ADDRESSES = {
        "SHT40": [0x44, 0x45],
        "BME688": [0x76, 0x77], 
        "BH1750": [0x23, 0x5C],
        "SDP810": [0x25],
        "VL53L0X": [0x29]
    }
    
    # TCA9548A 주소 범위 (실제 사용하는 주소만)
    TCA9548A_ADDRESSES = [0x70, 0x71]
    
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
        """
        현재 시스템이 라즈베리파이인지 확인
        
        운영 시 중요사항:
        - /proc/cpuinfo에서 Raspberry Pi 또는 BCM 키워드 확인
        - ARM/aarch64 아키텍처 확인
        - 개발 환경(x86)과 운영 환경(ARM) 자동 구분
        - False 반환 시 Mock 모드로 동작
        
        Returns:
            bool: 라즈베리파이 환경 여부
        """
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
        """
        라즈베리파이 I2C 버스 0, 1 초기화
        
        운영 시 중요사항:
        - 라즈베리파이 표준 I2C 버스 0, 1 사용
        - smbus2 라이브러리를 통한 I2C 통신 초기화
        - 버스 초기화 실패 시에도 다른 버스는 계속 진행
        - 초기화된 버스만 self.buses 딕셔너리에 저장
        - I2C 권한 문제 시 sudo 권한 또는 i2c 그룹 추가 필요
        """
        for bus_num in [0, 1]:
            try:
                bus = smbus2.SMBus(bus_num)
                self.buses[bus_num] = bus
                print(f"✅ I2C 버스 {bus_num} 초기화 성공")
            except Exception as e:
                print(f"❌ I2C 버스 {bus_num} 초기화 실패: {e}")
        
        print(f"📋 총 {len(self.buses)}개 I2C 버스 활성화: {list(self.buses.keys())}")
    
    def _detect_tca9548a(self):
        """
        TCA9548A 8채널 I2C 멀티플렉서 감지 및 설정
        
        운영 시 중요사항:
        - 각 I2C 버스(0, 1)에서 독립적으로 TCA9548A 검색
        - 주소 0x70, 0x71 범위에서 멀티플렉서 감지
        - write 방식과 read 방식 양쪽으로 통신 테스트
        - 감지 실패 시에도 직접 연결된 센서 스캔 가능
        - simpleTCA9548A.py 기반의 안정적인 감지 로직
        - 매 스캔마다 재감지하여 하드웨어 변경 대응
        """
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
        """
        TCA9548A 멀티플렉서의 특정 채널 활성화
        
        운영 시 중요사항:
        - 채널 마스크(1 << channel) 방식으로 단일 채널 선택
        - 50ms 대기로 채널 전환 안정화 시간 확보
        - Mock 모드에서는 항상 성공으로 처리
        - 채널 선택 실패 시 해당 채널 스캔 건너뛰기
        - 센서 스캔 전에 반드시 해당 채널 선택 필요
        
        Args:
            bus_num (int): I2C 버스 번호
            channel (int): 활성화할 채널 번호 (0-7)
        
        Returns:
            bool: 채널 선택 성공 여부
        """
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
        print("🔍 SPS30 UART 센서 검색 시작...")
        
        if not SPS30_AVAILABLE:
            print("❌ SPS30 라이브러리가 설치되지 않음")
            print("   해결방법: sudo pip3 install sensirion-shdlc-sps30")
            return None, None
        
        print("✅ SPS30 라이브러리 확인됨")
        
        # USB 시리얼 포트 후보들 검색
        port_candidates = []
        usb_ports = glob.glob('/dev/ttyUSB*')
        acm_ports = glob.glob('/dev/ttyACM*') 
        ama_ports = glob.glob('/dev/ttyAMA*')
        
        port_candidates.extend(usb_ports)
        port_candidates.extend(acm_ports)
        port_candidates.extend(ama_ports)
        
        print(f"📋 발견된 시리얼 포트:")
        print(f"  - USB 포트: {usb_ports}")
        print(f"  - ACM 포트: {acm_ports}")
        print(f"  - AMA 포트: {ama_ports}")
        print(f"  - 총 후보: {port_candidates}")
        
        if not port_candidates:
            print("❌ 사용 가능한 UART 시리얼 포트가 없습니다")
            print("  확인사항:")
            print("  1. SPS30이 USB로 연결되었는지 확인")
            print("  2. 'ls -la /dev/tty*' 명령으로 포트 확인")
            print("  3. 사용자가 dialout 그룹에 속해있는지 확인")
            return None, None
        
        # 각 포트에서 SPS30 센서 검색
        for port_path in port_candidates:
            try:
                print(f"🔌 UART 포트 테스트: {port_path}")
                
                # 포트 권한 확인
                import os
                if not os.access(port_path, os.R_OK | os.W_OK):
                    print(f"⚠️ 포트 {port_path} 권한 없음 - dialout 그룹 확인 필요")
                    continue
                
                with ShdlcSerialPort(port=port_path, baudrate=115200) as port:
                    device = Sps30ShdlcDevice(ShdlcConnection(port))
                    
                    print(f"  📡 SPS30 통신 시도 중...")
                    # 센서 정보 읽기 시도 (타임아웃 적용)
                    serial_number = device.device_information_serial_number()
                    
                    if serial_number:
                        print(f"✅ SPS30 센서 발견!")
                        print(f"  📍 포트: {port_path}")
                        print(f"  🏷️ 시리얼 번호: {serial_number}")
                        return port_path, serial_number
                    else:
                        print(f"  ❌ 시리얼 번호 읽기 실패")
                        
            except Exception as e:
                print(f"  ❌ 포트 {port_path} 테스트 실패:")
                print(f"     오류: {type(e).__name__}: {e}")
                continue
        
        print("❌ 모든 포트에서 SPS30 센서를 찾지 못했습니다")
        print("  문제 해결 방법:")
        print("  1. SPS30 센서가 올바르게 연결되었는지 확인")
        print("  2. USB 케이블과 어댑터 상태 확인")
        print("  3. 라즈베리파이 재부팅 후 재시도")
        print("  4. 'sudo usermod -a -G dialout $USER' 실행 후 재로그인")
        return None, None
    
    def scan_uart_sensors(self) -> List[Dict]:
        """UART 센서 스캔 (SPS30)"""
        print("🔍 UART 센서 스캔 시작...")
        uart_devices = []
        
        if not self.is_raspberry_pi:
            # 라즈베리파이 환경이 아니면 빈 목록 반환
            print("⚠️ SPS30 UART 센서 사용 불가: 라즈베리파이 환경에서만 사용 가능")
            return uart_devices
        
        print("🔗 라즈베리파이 환경: 실제 UART 센서 검색")
        
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
        else:
            print("❌ SPS30 UART 센서를 찾지 못했습니다")
        
        print(f"📊 UART 스캔 결과: {len(uart_devices)}개 센서 발견")
        return uart_devices
    
    def scan_sdp810_sensors(self) -> List[Dict]:
        """SDP810 차압센서 전용 스캔 (모든 채널에서 0x25 주소 검색)"""
        print("🔍 SDP810 차압센서 전용 스캔 시작...")
        sdp810_devices = []
        
        if not self.is_raspberry_pi or not I2C_AVAILABLE:
            # 라즈베리파이 환경이 아니면 빈 목록 반환
            print("⚠️ SDP810 센서 사용 불가: 라즈베리파이 환경에서만 사용 가능")
            return sdp810_devices
        
        print("🔗 라즈베리파이 환경: 실제 SDP810 센서 검색")
        
        # 모든 버스와 채널에서 0x25 주소 검색
        for bus_num in [0, 1]:
            if bus_num not in self.buses:
                continue
                
            bus = self.buses[bus_num]
            
            if bus_num in self.tca_info:
                # 멀티플렉서를 통한 스캔
                mux_address = self.tca_info[bus_num]["address"]
                print(f"  🔍 Bus {bus_num} 멀티플렉서 채널 스캔 중...")
                
                for channel in range(8):
                    try:
                        # 채널 선택
                        if not self._select_channel(bus_num, channel):
                            continue
                        
                        # 0x25 주소에서 SDP810 확인
                        bus.read_byte(0x25)
                        
                        # SDP810 통신 테스트
                        if self._test_sdp810_communication(bus, 0x25):
                            sensor_data = {
                                "sensor_type": "SDP810",
                                "sensor_id": f"sdp810_{bus_num}_{channel}_25",
                                "bus": bus_num,
                                "address": "0x25",
                                "mux_channel": channel,
                                "mux_address": f"0x{mux_address:02X}",
                                "interface": "I2C",
                                "status": "connected",
                                "measurements": ["differential_pressure"],
                                "units": {"differential_pressure": "Pa"},
                                "test_result": "SDP810 차압센서 확인됨"
                            }
                            sdp810_devices.append(sensor_data)
                            print(f"    ✅ Bus {bus_num} CH{channel}: SDP810 발견")
                        
                        self._disable_all_channels(bus_num)
                        
                    except Exception as e:
                        # 0x25 주소 응답 없음 - 정상적인 상황
                        continue
            
            else:
                # 직접 연결 스캔
                print(f"  🔍 Bus {bus_num} 직접 연결 스캔 중...")
                try:
                    bus.read_byte(0x25)
                    
                    if self._test_sdp810_communication(bus, 0x25):
                        sensor_data = {
                            "sensor_type": "SDP810",
                            "sensor_id": f"sdp810_{bus_num}_direct_25",
                            "bus": bus_num,
                            "address": "0x25",
                            "mux_channel": None,
                            "mux_address": None,
                            "interface": "I2C",
                            "status": "connected",
                            "measurements": ["differential_pressure"],
                            "units": {"differential_pressure": "Pa"},
                            "test_result": "SDP810 차압센서 확인됨"
                        }
                        sdp810_devices.append(sensor_data)
                        print(f"    ✅ Bus {bus_num} 직접: SDP810 발견")
                
                except Exception as e:
                    # 0x25 주소 응답 없음 - 정상적인 상황
                    continue
        
        print(f"📊 SDP810 스캔 결과: {len(sdp810_devices)}개 센서 발견")
        return sdp810_devices
    
    def _test_sdp810_communication(self, bus, address) -> bool:
        """SDP810 센서 통신 테스트"""
        try:
            # 3바이트 읽기 시도 (압력 데이터 + CRC)
            read_msg = smbus2.i2c_msg.read(address, 3)
            bus.i2c_rdwr(read_msg)
            raw_data = list(read_msg)
            
            if len(raw_data) == 3:
                # 압력 데이터 파싱
                import struct
                pressure_msb = raw_data[0]
                pressure_lsb = raw_data[1]
                
                # 압력 계산
                raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]
                pressure_pa = raw_pressure / 60.0
                
                # 합리적인 압력 범위 확인 (-500 ~ +500 Pa)
                if -500 <= pressure_pa <= 500:
                    return True
            
            return False
            
        except Exception as e:
            return False

    def scan_bh1750_sensors(self) -> List[Dict]:
        """BH1750 조도 센서 동적 스캔 (모든 채널 검색)"""
        print("🔍 BH1750 조도 센서 동적 스캔 시작...")
        bh1750_devices = []
        
        if not self.is_raspberry_pi or not I2C_AVAILABLE:
            # 라즈베리파이 환경이 아니면 빈 목록 반환
            print("⚠️ BH1750 센서 사용 불가: 라즈베리파이 환경에서만 사용 가능")
            return bh1750_devices
        
        print("🔗 라즈베리파이 환경: 실제 BH1750 센서 동적 검색")
        
        # 전체 버스와 채널에서 BH1750 센서 동적 발견
        for bus_num in [0, 1]:
            # 직접 연결 센서 먼저 스캔
            print(f"  🔍 Bus {bus_num} 직접 연결 스캔...")
            try:
                direct_sensors = self._scan_bh1750_direct(bus_num)
                
                # 추가 정보 보강
                for sensor in direct_sensors:
                    sensor["display_channel"] = None
                    sensor["location"] = f"Bus {bus_num}, 직접 연결"
                    sensor["discovered_at"] = time.time()
                
                bh1750_devices.extend(direct_sensors)
                if direct_sensors:
                    print(f"    ✅ Bus {bus_num} 직접 연결: {len(direct_sensors)}개 발견")
                
            except Exception as e:
                print(f"    ❌ Bus {bus_num} 직접 스캔 실패: {e}")
            
            # 멀티플렉서 채널별 스캔 (모든 채널 0-7)
            if bus_num in self.tca_info:
                mux_address = self.tca_info[bus_num]["address"]
                print(f"  🔍 Bus {bus_num} TCA9548A 채널별 스캔...")
                
                try:
                    # 모든 채널 스캔 (0-7)
                    for channel in range(8):
                        if not self._select_channel(bus_num, channel):
                            continue
                            
                        channel_sensors = self._scan_bh1750_direct(bus_num, channel, mux_address)
                        
                        # 추가 정보 보강 (display_channel, location 등)
                        for sensor in channel_sensors:
                            sensor['mux_channel'] = channel
                            sensor['mux_address'] = f"0x{mux_address:02X}"
                            display_channel = channel + (8 if bus_num == 1 else 0)
                            sensor["display_channel"] = display_channel
                            sensor["location"] = f"Bus {bus_num}, CH {display_channel}"
                            sensor["discovered_at"] = time.time()
                        
                        bh1750_devices.extend(channel_sensors)
                        if channel_sensors:
                            print(f"    ✅ Bus {bus_num} CH{channel}: {len(channel_sensors)}개 발견")
                        
                        self._disable_all_channels(bus_num)
                    
                except Exception as e:
                    print(f"    ❌ Bus {bus_num} 멀티플렉서 스캔 실패: {e}")
        
        print(f"📊 BH1750 동적 스캔 결과: {len(bh1750_devices)}개 센서 발견")
        
        # 발견된 센서 상세 정보 출력
        for i, sensor in enumerate(bh1750_devices, 1):
            print(f"  {i}. {sensor['location']} - {sensor['address']} ({sensor['test_result']})")
        
        return bh1750_devices
    
    def _scan_bh1750_direct(self, bus_num: int, channel: int = None, mux_address: int = None) -> List[Dict]:
        """BH1750 센서 직접 스캔 (test_bh1750_sensors.py 로직 기반)"""
        devices = []
        
        if bus_num not in self.buses:
            return devices
        
        bus = self.buses[bus_num]
        bh1750_addresses = [0x23, 0x5C]  # 기본 주소와 ADDR=HIGH 주소
        
        for address in bh1750_addresses:
            try:
                # BH1750 연결 테스트 (test_bh1750_sensors.py의 SimpleBH1750 로직)
                connection_success = False
                
                # 방법 1: Power On 명령
                try:
                    bus.write_byte(address, 0x01)  # Power On
                    time.sleep(0.01)
                    connection_success = True
                except:
                    pass
                
                # 방법 2: Reset 명령
                if not connection_success:
                    try:
                        bus.write_byte(address, 0x07)  # Reset
                        time.sleep(0.01)
                        connection_success = True
                    except:
                        pass
                
                # 방법 3: 직접 측정 명령
                if not connection_success:
                    try:
                        bus.write_byte(address, 0x20)  # One Time H-Resolution Mode
                        time.sleep(0.15)  # 150ms 대기
                        data = bus.read_i2c_block_data(address, 0x20, 2)
                        if len(data) == 2:
                            connection_success = True
                    except:
                        pass
                
                if connection_success:
                    # 실제 조도 측정 테스트
                    light_value = self._test_bh1750_measurement(bus, address)
                    
                    if light_value is not None:
                        sensor_id = f"bh1750_{bus_num}_{channel if channel is not None else 'direct'}_{address:02x}"
                        
                        sensor_data = {
                            "sensor_type": "BH1750",
                            "sensor_id": sensor_id,
                            "bus": bus_num,
                            "address": f"0x{address:02X}",
                            "mux_channel": channel,
                            "mux_address": f"0x{mux_address:02X}" if mux_address else None,
                            "interface": "I2C",
                            "status": "connected",
                            "measurements": ["light"],
                            "units": {"light": "lux"},
                            "test_result": f"조도: {light_value} lux"
                        }
                        devices.append(sensor_data)
                        
            except Exception as e:
                # 주소에 센서가 없는 경우 - 정상적인 상황
                continue
        
        return devices
    
    def _test_bh1750_measurement(self, bus, address) -> Optional[float]:
        """BH1750 조도 측정 테스트 (실제 값 반환)"""
        try:
            # One Time H-Resolution Mode로 측정
            bus.write_byte(address, 0x20)
            time.sleep(0.15)  # 150ms 대기
            
            # 데이터 읽기
            try:
                data = bus.read_i2c_block_data(address, 0x20, 2)
            except:
                # 개별 read_byte로 시도
                data = []
                for _ in range(2):
                    byte_val = bus.read_byte(address)
                    data.append(byte_val)
                    time.sleep(0.001)
            
            if len(data) >= 2:
                # 조도값 계산
                raw_value = (data[0] << 8) | data[1]
                lux = raw_value / 1.2  # BH1750 조도 계산 공식
                
                # 합리적인 범위 체크
                if 0 <= lux <= 65535:
                    return round(lux, 1)
            
            return None
            
        except Exception as e:
            return None

    def scan_sht40_sensors(self) -> List[Dict]:
        """SHT40 동적 센서 스캔 (모든 채널 검색)"""
        print("🔍 SHT40 동적 센서 스캔 시작...")
        sht40_devices = []
        
        if not self.is_raspberry_pi or not SHT40_AVAILABLE:
            # 라즈베리파이 환경이 아니거나 SHT40 모듈이 없으면 빈 목록 반환
            print("⚠️ SHT40 센서 사용 불가: 라즈베리파이 환경에서만 사용 가능")
            return sht40_devices
        
        print("🔗 라즈베리파이 환경: 실제 SHT40 센서 동적 검색")
        
        # SHT40 모듈이 사용 불가능하면 빈 리스트 반환
        if not SHT40_AVAILABLE:
            print("⚠️ SHT40 모듈 사용 불가능, 빈 결과 반환")
            return sht40_devices
        
        # 전체 버스와 채널에서 SHT40 센서 동적 발견
        for bus_num in [0, 1]:
            # 직접 연결 센서 먼저 스캔
            print(f"  🔍 Bus {bus_num} 직접 연결 스캔...")
            try:
                direct_sensors = scan_sht40_sensors(
                    bus_numbers=[bus_num],
                    addresses=[0x44, 0x45],
                    mux_channels=None
                )
                
                # 추가 정보 보강
                for sensor in direct_sensors:
                    sensor["display_channel"] = None
                    sensor["location"] = f"Bus {bus_num}, 직접 연결"
                    sensor["discovered_at"] = time.time()
                
                sht40_devices.extend(direct_sensors)
                if direct_sensors:
                    print(f"    ✅ Bus {bus_num} 직접 연결: {len(direct_sensors)}개 발견")
                
            except Exception as e:
                print(f"    ❌ Bus {bus_num} 직접 스캔 실패: {e}")
            
            # 멀티플렉서 채널별 스캔 (모든 채널 0-7)
            if bus_num in self.tca_info:
                mux_address = self.tca_info[bus_num]["address"]
                print(f"  🔍 Bus {bus_num} TCA9548A 채널별 스캔...")
                
                try:
                    # 모든 채널 스캔 (0-7)
                    all_channels = list(range(8))
                    found_sensors = scan_sht40_sensors(
                        bus_numbers=[bus_num],
                        addresses=[0x44, 0x45],
                        mux_channels=all_channels,
                        mux_address=mux_address
                    )
                    
                    # 추가 정보 보강 (display_channel, location 등)
                    for sensor in found_sensors:
                        if 'mux_channel' in sensor and sensor['mux_channel'] is not None:
                            channel = sensor['mux_channel']
                            display_channel = channel + (8 if bus_num == 1 else 0)
                            sensor["display_channel"] = display_channel
                            sensor["location"] = f"Bus {bus_num}, CH {display_channel}"
                            sensor["discovered_at"] = time.time()
                    
                    sht40_devices.extend(found_sensors)
                    if found_sensors:
                        print(f"    ✅ Bus {bus_num} 멀티플렉서: {len(found_sensors)}개 발견")
                    
                except Exception as e:
                    print(f"    ❌ Bus {bus_num} 멀티플렉서 스캔 실패: {e}")
        
        print(f"📊 SHT40 동적 스캔 결과: {len(sht40_devices)}개 센서 발견")
        
        # 발견된 센서 상세 정보 출력
        for i, sensor in enumerate(sht40_devices, 1):
            print(f"  {i}. {sensor['location']} - {sensor['address']} ({sensor['test_result']})")
        
        return sht40_devices
    
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
        
        # 주요 센서 주소 스캔 (TCA9548A 주소 제외)
        all_addresses = []
        for addresses in self.SENSOR_ADDRESSES.values():
            all_addresses.extend(addresses)
        
        # TCA9548A 주소 제외 (0x70-0x77)
        scan_addresses = sorted(set(all_addresses))
        scan_addresses = [addr for addr in scan_addresses if addr not in self.TCA9548A_ADDRESSES]
        print(f"  📋 스캔 대상 주소: {[f'0x{addr:02X}' for addr in scan_addresses]} (TCA9548A 제외)")
        
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
                            "status": device.get("status", "connected")
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
                        "status": device.get("status", "connected")
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
                        "status": uart_device.get("status", "connected"),
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
        """
        TCA9548A 이중 멀티플렉서 시스템 전체 스캔 (I2C + UART 통합)
        
        운영 시 중요사항:
        - I2C 버스 0, 1 모두에서 멀티플렉서 및 센서 검색
        - SHT40, SDP810 전용 스캔으로 특화된 센서 처리
        - UART 센서(SPS30) 검색 및 통합
        - 매 스캔마다 TCA9548A 재감지로 하드웨어 변경 대응
        - 센서 타입별 그룹화 및 표준화된 데이터 형식
        - 전체 시스템 상태 및 센서 개수 통계 제공
        
        Returns:
            Dict: 전체 시스템 스캔 결과 (모든 센서, 버스 정보, 통계 포함)
        """
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
                    
                    # 센서 목록 구성 (SHT40, SDP810 제외 - 전용 스캔에서 추가)
                    for channel, devices in channel_results.items():
                        for device in devices:
                            # SHT40, SDP810, BH1750은 전용 스캔에서 처리하므로 여기서 제외
                            if device["sensor_type"] in ["SHT40", "SDP810", "BH1750"]:
                                continue
                                
                            sensor_data = {
                                "bus": bus_num,
                                "mux_channel": channel,
                                "address": device["address"],
                                "sensor_name": device["sensor_type"],
                                "sensor_type": device["sensor_type"],
                                "status": device.get("status", "connected")
                            }
                            scan_result["sensors"].append(sensor_data)
                            scan_result["i2c_devices"].append(sensor_data)
                else:
                    # 직접 스캔
                    direct_devices = self.scan_bus_direct(bus_num)
                    bus_info["direct_devices"] = direct_devices
                    
                    for device in direct_devices:
                        # SHT40, SDP810, BH1750은 전용 스캔에서 처리하므로 여기서 제외
                        if device["sensor_type"] in ["SHT40", "SDP810", "BH1750"]:
                            continue
                            
                        sensor_data = {
                            "bus": bus_num,
                            "mux_channel": None,
                            "address": device["address"],
                            "sensor_name": device["sensor_type"],
                            "sensor_type": device["sensor_type"],
                            "status": device.get("status", "connected")
                        }
                        scan_result["sensors"].append(sensor_data)
                        scan_result["i2c_devices"].append(sensor_data)
                
                scan_result["buses"][bus_num] = bus_info
            
            # SHT40 전용 센서 스캔 추가
            sht40_devices = []
            try:
                print("🔍 SHT40 전용 센서 스캔 시작...")
                sht40_devices = self.scan_sht40_sensors()
                scan_result["sht40_devices"] = sht40_devices
                print(f"✅ SHT40 스캔 완료: {len(sht40_devices)}개 발견")
            except Exception as e:
                print(f"⚠️ SHT40 스캔 실패, 건너뛰기: {e}")
                scan_result["sht40_devices"] = []
            
            # SDP810 전용 센서 스캔 추가
            sdp810_devices = []
            try:
                print("🔍 SDP810 전용 센서 스캔 시작...")
                sdp810_devices = self.scan_sdp810_sensors()
                scan_result["sdp810_devices"] = sdp810_devices
                print(f"✅ SDP810 스캔 완료: {len(sdp810_devices)}개 발견")
            except Exception as e:
                print(f"⚠️ SDP810 스캔 실패, 건너뛰기: {e}")
                scan_result["sdp810_devices"] = []
            
            # BH1750 전용 센서 스캔 추가
            bh1750_devices = []
            try:
                print("🔍 BH1750 전용 센서 스캔 시작...")
                bh1750_devices = self.scan_bh1750_sensors()
                scan_result["bh1750_devices"] = bh1750_devices
                print(f"✅ BH1750 스캔 완료: {len(bh1750_devices)}개 발견")
            except Exception as e:
                print(f"⚠️ BH1750 스캔 실패, 건너뛰기: {e}")
                scan_result["bh1750_devices"] = []
            
            # UART 센서 스캔 (전체 시스템에서 한 번만)
            uart_devices = []
            try:
                print("🔍 UART 센서 스캔 시작...")
                uart_devices = self.scan_uart_sensors()
                scan_result["uart_devices"] = uart_devices
                print(f"✅ UART 스캔 완료: {len(uart_devices)}개 발견")
            except Exception as e:
                print(f"⚠️ UART 스캔 실패, 건너뛰기: {e}")
                scan_result["uart_devices"] = []
            
            # SHT40 센서도 전체 센서 목록에 추가
            for sht40_device in sht40_devices:
                sht40_sensor_data = {
                    "bus": sht40_device.get("bus"),
                    "mux_channel": sht40_device.get("mux_channel"),
                    "address": sht40_device.get("address"),
                    "sensor_name": sht40_device["sensor_type"],
                    "sensor_type": sht40_device["sensor_type"],
                    "sensor_id": sht40_device.get("sensor_id"),
                    "status": sht40_device.get("status", "connected"),
                    "interface": "I2C",
                    "measurements": sht40_device.get("measurements", []),
                    "units": sht40_device.get("units", {}),
                    "test_result": sht40_device.get("test_result", "")
                }
                scan_result["sensors"].append(sht40_sensor_data)
                scan_result["i2c_devices"].append(sht40_sensor_data)
            
            # SDP810 센서도 전체 센서 목록에 추가
            for sdp810_device in sdp810_devices:
                sdp810_sensor_data = {
                    "bus": sdp810_device.get("bus"),
                    "mux_channel": sdp810_device.get("mux_channel"),
                    "address": sdp810_device.get("address"),
                    "sensor_name": sdp810_device["sensor_type"],
                    "sensor_type": sdp810_device["sensor_type"],
                    "sensor_id": sdp810_device.get("sensor_id"),
                    "status": sdp810_device.get("status", "connected"),
                    "interface": "I2C",
                    "measurements": sdp810_device.get("measurements", []),
                    "units": sdp810_device.get("units", {}),
                    "test_result": sdp810_device.get("test_result", "")
                }
                scan_result["sensors"].append(sdp810_sensor_data)
                scan_result["i2c_devices"].append(sdp810_sensor_data)
            
            # BH1750 센서도 전체 센서 목록에 추가
            for bh1750_device in bh1750_devices:
                bh1750_sensor_data = {
                    "bus": bh1750_device.get("bus"),
                    "mux_channel": bh1750_device.get("mux_channel"),
                    "address": bh1750_device.get("address"),
                    "sensor_name": bh1750_device["sensor_type"],
                    "sensor_type": bh1750_device["sensor_type"],
                    "sensor_id": bh1750_device.get("sensor_id"),
                    "status": bh1750_device.get("status", "connected"),
                    "interface": "I2C",
                    "measurements": bh1750_device.get("measurements", []),
                    "units": bh1750_device.get("units", {}),
                    "test_result": bh1750_device.get("test_result", "")
                }
                scan_result["sensors"].append(bh1750_sensor_data)
                scan_result["i2c_devices"].append(bh1750_sensor_data)
            
            # UART 센서도 전체 센서 목록에 추가
            for uart_device in uart_devices:
                uart_sensor_data = {
                    "bus": None,
                    "mux_channel": None,
                    "address": None,
                    "port": uart_device["port"],
                    "sensor_name": uart_device["sensor_name"],
                    "sensor_type": uart_device["sensor_type"],
                    "status": uart_device.get("status", "connected"),
                    "interface": "UART",
                    "serial_number": uart_device.get("serial_number"),
                    "measurements": uart_device.get("measurements", []),
                    "units": uart_device.get("units", "")
                }
                scan_result["sensors"].append(uart_sensor_data)
            
            i2c_count = len([s for s in scan_result['sensors'] if s.get('interface') == 'I2C'])
            uart_count = len([s for s in scan_result['sensors'] if s.get('interface') == 'UART'])
            sht40_count = len([s for s in scan_result['sensors'] if s.get('sensor_type') == 'SHT40'])
            sdp810_count = len([s for s in scan_result['sensors'] if s.get('sensor_type') == 'SDP810'])
            bh1750_count = len([s for s in scan_result['sensors'] if s.get('sensor_type') == 'BH1750'])
            print(f"✅ 전체 시스템 스캔 완료: I2C {i2c_count}개 (SHT40 {sht40_count}개, SDP810 {sdp810_count}개, BH1750 {bh1750_count}개 포함), UART {uart_count}개 센서 발견")
            
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
    """
    전역 하드웨어 스캐너 싱글톤 인스턴스 반환
    
    운영 시 중요사항:
    - 애플리케이션 전체에서 단일 스캐너 인스턴스 공유
    - 첫 호출 시 자동으로 스캐너 인스턴스 생성
    - I2C 리소스 충돌 방지를 위한 싱글톤 패턴
    - 메모리 효율성 및 상태 일관성 보장
    
    Returns:
        HardwareScanner: 전역 스캐너 인스턴스
    """
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = HardwareScanner()
    return _scanner_instance

def cleanup_scanner():
    """
    전역 스캐너 인스턴스 정리 및 해제
    
    운영 시 중요사항:
    - 애플리케이션 종료 시 호출하여 리소스 정리
    - I2C 버스 및 멀티플렉서 연결 안전하게 해제
    - 전역 인스턴스 변수 초기화
    - 메모리 누수 방지
    """
    global _scanner_instance
    if _scanner_instance:
        _scanner_instance.close()
        _scanner_instance = None

def reset_scanner():
    """
    하드웨어 스캐너 강제 리셋 및 TCA9548A 재감지
    
    운영 시 중요사항:
    - 하드웨어 구성 변경 시 (센서 추가/제거) 사용
    - TCA9548A 멀티플렉서 정보 캐시 초기화
    - 다음 스캔에서 하드웨어 재감지 수행
    - API 엔드포인트에서 수동 리셋 기능 제공
    """
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