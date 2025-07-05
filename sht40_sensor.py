#!/usr/bin/env python3
"""
SHT40 온습도 센서 모듈
===================
STMicroelectronics SHT40 온습도 센서용 I2C 통신 모듈
- CRC 검증 기능
- 재시도 메커니즘
- 멀티 버스 지원
- TCA9548A 멀티플렉서 통합 지원
"""

import time
import smbus2
import logging
from typing import Optional, Tuple

# 로거 설정
logger = logging.getLogger(__name__)

class SHT40Sensor:
    """SHT40 온습도 센서 클래스 (개선된 I2C 방식)"""
    
    # I2C addresses
    DEFAULT_I2C_ADDRESS = 0x44  # SHT40 표준 주소
    ALTERNATIVE_I2C_ADDRESS = 0x45  # SHT40 대안 주소
    
    # Commands
    CMD_MEASURE_HIGH_PRECISION = 0xFD  # High precision measurement
    CMD_MEASURE_MEDIUM_PRECISION = 0xF6  # Medium precision measurement
    CMD_MEASURE_LOW_PRECISION = 0xE0  # Low precision measurement
    CMD_READ_SERIAL_NUMBER = 0x89  # Read serial number
    CMD_SOFT_RESET = 0x94  # Soft reset
    
    def __init__(self, bus=1, address=DEFAULT_I2C_ADDRESS, mux_channel=None, mux_address=None):
        """
        SHT40 센서 초기화
        
        Args:
            bus: I2C 버스 번호 (0 또는 1)
            address: SHT40 센서 I2C 주소 (0x44 또는 0x45)
            mux_channel: TCA9548A 멀티플렉서 채널 (0-7, None이면 직접 연결)
            mux_address: TCA9548A 멀티플렉서 주소 (보통 0x70)
        """
        self.bus_num = bus
        self.address = address
        self.mux_channel = mux_channel
        self.mux_address = mux_address
        self.bus = None
        self.sensor_id = f"sht40_{bus}_{mux_channel if mux_channel is not None else 'direct'}_{address:02x}"
    
    def _select_mux_channel(self):
        """TCA9548A 멀티플렉서 채널 선택"""
        if self.mux_channel is not None and self.mux_address is not None:
            try:
                # 멀티플렉서 채널 선택 (해당 채널만 활성화)
                channel_mask = 1 << self.mux_channel
                self.bus.write_byte(self.mux_address, channel_mask)
                time.sleep(0.01)  # 채널 전환 대기
                logger.debug(f"멀티플렉서 채널 {self.mux_channel} 선택됨")
            except Exception as e:
                logger.error(f"멀티플렉서 채널 선택 실패: {e}")
                raise e
    
    def connect(self):
        """센서 연결 및 초기화"""
        try:
            self.bus = smbus2.SMBus(self.bus_num)
            
            # 멀티플렉서 채널 선택 (필요한 경우)
            if self.mux_channel is not None:
                self._select_mux_channel()
            
            # 연결 테스트 - 리셋 명령 전송
            write_msg = smbus2.i2c_msg.write(self.address, [self.CMD_SOFT_RESET])
            self.bus.i2c_rdwr(write_msg)
            time.sleep(0.1)  # 리셋 후 충분한 대기 시간
            
            logger.info(f"SHT40 센서 연결 완료 (버스: {self.bus_num}, 주소: 0x{self.address:02X}, "
                       f"채널: {self.mux_channel})")
            return True
            
        except Exception as e:
            if self.bus:
                self.bus.close()
                self.bus = None
            logger.error(f"SHT40 센서 연결 실패: {e}")
            raise e
    
    def calculate_crc(self, data):
        """CRC-8 체크섬 계산"""
        POLYNOMIAL = 0x31
        CRC = 0xFF
        
        for byte in data:
            CRC ^= byte
            for _ in range(8):
                if CRC & 0x80:
                    CRC = ((CRC << 1) ^ POLYNOMIAL) & 0xFF
                else:
                    CRC = (CRC << 1) & 0xFF
        
        return CRC
    
    def verify_crc(self, data, crc):
        """CRC 검증"""
        return self.calculate_crc(data) == crc
    
    def read_temperature_humidity(self, precision="high"):
        """
        온습도값 읽기 (개선된 방식)
        
        Args:
            precision: 측정 정밀도 ("high", "medium", "low")
            
        Returns:
            tuple: (temperature, humidity) 또는 None
        """
        if not self.bus:
            raise Exception("센서가 연결되지 않음")
            
        try:
            # 멀티플렉서 채널 선택 (필요한 경우)
            if self.mux_channel is not None:
                self._select_mux_channel()
            
            # 정밀도에 따른 명령 및 대기시간 설정
            if precision == "medium":
                cmd = self.CMD_MEASURE_MEDIUM_PRECISION
                wait_time = 0.01  # 10ms
            elif precision == "low":
                cmd = self.CMD_MEASURE_LOW_PRECISION
                wait_time = 0.005  # 5ms
            else:  # high precision (default)
                cmd = self.CMD_MEASURE_HIGH_PRECISION
                wait_time = 0.02  # 20ms
            
            # 1단계: 측정 명령 전송
            write_msg = smbus2.i2c_msg.write(self.address, [cmd])
            self.bus.i2c_rdwr(write_msg)
            
            # 2단계: 측정 완료까지 대기
            time.sleep(wait_time)
            
            # 3단계: 데이터 읽기 (6바이트: T_MSB, T_LSB, T_CRC, RH_MSB, RH_LSB, RH_CRC)
            read_msg = smbus2.i2c_msg.read(self.address, 6)
            self.bus.i2c_rdwr(read_msg)
            
            # 읽은 데이터 처리
            data = list(read_msg)
            
            # 온도 및 습도 데이터 분리
            t_data = [data[0], data[1]]
            t_crc = data[2]
            rh_data = [data[3], data[4]]
            rh_crc = data[5]
            
            # CRC 검증
            t_crc_ok = self.verify_crc(t_data, t_crc)
            rh_crc_ok = self.verify_crc(rh_data, rh_crc)
            
            if not t_crc_ok:
                logger.warning(f"SHT40 온도 데이터 CRC 검증 실패 (센서: {self.sensor_id})")
            if not rh_crc_ok:
                logger.warning(f"SHT40 습도 데이터 CRC 검증 실패 (센서: {self.sensor_id})")
            
            # 원시 데이터를 실제 값으로 변환
            t_raw = (t_data[0] << 8) | t_data[1]
            rh_raw = (rh_data[0] << 8) | rh_data[1]
            
            # 데이터시트의 변환 공식 적용
            temperature = -45 + 175 * (t_raw / 65535.0)
            humidity = -6 + 125 * (rh_raw / 65535.0)
            
            # 습도를 물리적 범위로 제한
            humidity = max(0, min(100, humidity))
            
            return round(temperature, 2), round(humidity, 2)
            
        except Exception as e:
            logger.error(f"SHT40 온습도 측정 실패 (센서: {self.sensor_id}): {e}")
            raise Exception(f"온습도 측정 실패: {e}")
    
    def read_with_retry(self, precision="high", max_retries=3):
        """
        재시도 기능이 있는 측정
        
        Args:
            precision: 측정 정밀도
            max_retries: 최대 재시도 횟수
            
        Returns:
            tuple: (temperature, humidity) 또는 None
        """
        for attempt in range(max_retries):
            try:
                result = self.read_temperature_humidity(precision)
                if result is not None:
                    logger.debug(f"SHT40 측정 성공 (센서: {self.sensor_id}, 시도: {attempt + 1})")
                    return result
                time.sleep(0.1)
            except Exception as e:
                logger.warning(f"SHT40 측정 시도 {attempt + 1} 실패 (센서: {self.sensor_id}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.1)
        
        logger.error(f"SHT40 {max_retries}번 시도 후 측정 실패 (센서: {self.sensor_id})")
        return None
    
    def read_serial_number(self):
        """센서 시리얼 번호 읽기"""
        try:
            if self.mux_channel is not None:
                self._select_mux_channel()
                
            # 시리얼 번호 읽기 명령 전송
            write_msg = smbus2.i2c_msg.write(self.address, [self.CMD_READ_SERIAL_NUMBER])
            self.bus.i2c_rdwr(write_msg)
            time.sleep(0.01)
            
            # 6바이트 읽기 (시리얼 번호 + CRC)
            read_msg = smbus2.i2c_msg.read(self.address, 6)
            self.bus.i2c_rdwr(read_msg)
            data = list(read_msg)
            
            # 시리얼 번호 추출 (32비트)
            serial_number = (data[0] << 24) | (data[1] << 16) | (data[3] << 8) | data[4]
            
            return serial_number
            
        except Exception as e:
            logger.error(f"SHT40 시리얼 번호 읽기 실패 (센서: {self.sensor_id}): {e}")
            return None
    
    def get_sensor_info(self):
        """센서 정보 반환"""
        return {
            "sensor_type": "SHT40",
            "sensor_id": self.sensor_id,
            "bus": self.bus_num,
            "address": f"0x{self.address:02X}",
            "mux_channel": self.mux_channel,
            "mux_address": f"0x{self.mux_address:02X}" if self.mux_address else None,
            "interface": "I2C",
            "measurements": ["temperature", "humidity"],
            "units": {"temperature": "°C", "humidity": "%RH"},
            "precision_modes": ["high", "medium", "low"]
        }
    
    def test_connection(self):
        """센서 연결 테스트"""
        try:
            temp, humidity = self.read_with_retry(precision="low", max_retries=1)
            if temp is not None and humidity is not None:
                return True, f"온도: {temp}°C, 습도: {humidity}%RH"
            else:
                return False, "데이터 읽기 실패"
        except Exception as e:
            return False, str(e)
    
    def close(self):
        """연결 종료"""
        if self.bus:
            try:
                self.bus.close()
                self.bus = None
                logger.info(f"SHT40 센서 연결 종료 (센서: {self.sensor_id})")
            except Exception as e:
                logger.error(f"SHT40 센서 연결 종료 실패: {e}")

def scan_sht40_sensors(bus_numbers=[0, 1], addresses=[0x44, 0x45], mux_channels=None, mux_address=0x70):
    """
    SHT40 센서 스캔
    
    Args:
        bus_numbers: 스캔할 I2C 버스 번호 리스트
        addresses: 스캔할 SHT40 주소 리스트
        mux_channels: 멀티플렉서 채널 리스트 (None이면 직접 연결만 스캔)
        mux_address: 멀티플렉서 주소
        
    Returns:
        list: 발견된 SHT40 센서 정보 리스트
    """
    found_sensors = []
    
    for bus_num in bus_numbers:
        logger.info(f"SHT40 센서 스캔 시작 - I2C 버스 {bus_num}")
        
        # 직접 연결된 센서 스캔
        if mux_channels is None:
            for address in addresses:
                try:
                    sensor = SHT40Sensor(bus=bus_num, address=address)
                    sensor.connect()
                    
                    # 연결 테스트
                    success, message = sensor.test_connection()
                    if success:
                        sensor_info = sensor.get_sensor_info()
                        sensor_info["test_result"] = message
                        found_sensors.append(sensor_info)
                        logger.info(f"SHT40 센서 발견: 버스 {bus_num}, 주소 0x{address:02X}")
                    
                    sensor.close()
                    
                except Exception as e:
                    logger.debug(f"SHT40 스캔 실패 - 버스 {bus_num}, 주소 0x{address:02X}: {e}")
        
        # 멀티플렉서 채널별 스캔
        else:
            for channel in mux_channels:
                for address in addresses:
                    try:
                        sensor = SHT40Sensor(
                            bus=bus_num, 
                            address=address, 
                            mux_channel=channel, 
                            mux_address=mux_address
                        )
                        sensor.connect()
                        
                        # 연결 테스트
                        success, message = sensor.test_connection()
                        if success:
                            sensor_info = sensor.get_sensor_info()
                            sensor_info["test_result"] = message
                            found_sensors.append(sensor_info)
                            logger.info(f"SHT40 센서 발견: 버스 {bus_num}, 채널 {channel}, 주소 0x{address:02X}")
                        
                        sensor.close()
                        
                    except Exception as e:
                        logger.debug(f"SHT40 스캔 실패 - 버스 {bus_num}, 채널 {channel}, 주소 0x{address:02X}: {e}")
    
    logger.info(f"SHT40 센서 스캔 완료: {len(found_sensors)}개 발견")
    return found_sensors

if __name__ == "__main__":
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("SHT40 센서 스캔 테스트")
    
    # 직접 연결 스캔
    sensors = scan_sht40_sensors(bus_numbers=[1], addresses=[0x44])
    
    if sensors:
        print(f"\n발견된 SHT40 센서: {len(sensors)}개")
        for sensor_info in sensors:
            print(f"- {sensor_info['sensor_id']}: {sensor_info['test_result']}")
    else:
        print("SHT40 센서를 찾을 수 없습니다.")