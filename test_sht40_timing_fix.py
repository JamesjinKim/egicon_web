#!/usr/bin/env python3
"""
SHT40 센서 타이밍 개선 테스트 프로그램
=======================================
Remote I/O error 해결을 위한 개선사항 적용 테스트:
1. 더 긴 대기시간: 0.5초 이상 대기
2. 정밀도 낮추기: 'low' 모드 사용
3. 재시도 간격 늘리기: 1초 이상 간격

목적: 기존 센서 모듈 수정 전 개선안 검증
"""

import sys
import time
import smbus2
import logging
from datetime import datetime
from typing import Optional, Tuple

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SHT40SensorImproved:
    """SHT40 센서 클래스 (타이밍 개선 버전)"""
    
    # I2C addresses
    DEFAULT_I2C_ADDRESS = 0x44
    ALTERNATIVE_I2C_ADDRESS = 0x45
    
    # Commands
    CMD_MEASURE_HIGH_PRECISION = 0xFD
    CMD_MEASURE_MEDIUM_PRECISION = 0xF6
    CMD_MEASURE_LOW_PRECISION = 0xE0    # 낮은 정밀도 우선 사용
    CMD_SOFT_RESET = 0x94
    
    def __init__(self, bus=1, address=DEFAULT_I2C_ADDRESS, mux_channel=None, mux_address=None):
        """SHT40 센서 초기화"""
        self.bus_num = bus
        self.address = address
        self.mux_channel = mux_channel
        self.mux_address = mux_address
        self.bus = None
        self.sensor_id = f"sht40_{bus}_{mux_channel if mux_channel is not None else 'direct'}_{address:02x}"
    
    def connect(self):
        """I2C 버스 연결"""
        try:
            self.bus = smbus2.SMBus(self.bus_num)
            logger.info(f"SHT40 센서 연결 완료 (버스: {self.bus_num}, 주소: 0x{self.address:02x}, 채널: {self.mux_channel})")
            return True
        except Exception as e:
            logger.error(f"SHT40 센서 연결 실패: {e}")
            return False
    
    def close(self):
        """I2C 버스 연결 해제"""
        if self.bus:
            self.bus.close()
            self.bus = None
            logger.info(f"SHT40 센서 연결 종료 (센서: {self.sensor_id})")
    
    def _select_mux_channel(self):
        """TCA9548A 멀티플렉서 채널 선택"""
        if self.mux_channel is not None and self.mux_address is not None:
            channel_mask = 1 << self.mux_channel
            self.bus.write_byte(self.mux_address, channel_mask)
            time.sleep(0.05)  # 🔧 개선1: 채널 전환 대기시간 증가 (0.02→0.05초)
    
    def calculate_crc(self, data):
        """CRC-8 체크섬 계산 (다항식: 0x31)"""
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
    
    def read_temperature_humidity_improved(self, precision="low"):
        """
        개선된 온습도값 읽기
        
        Args:
            precision: 측정 정밀도 ("low"를 기본값으로 사용)
            
        Returns:
            tuple: (temperature, humidity) 또는 None
        """
        if not self.bus:
            raise Exception("센서가 연결되지 않음")
        
        try:
            # 멀티플렉서 채널 선택
            if self.mux_channel is not None:
                self._select_mux_channel()
            
            # 🔧 개선2: 낮은 정밀도 우선 사용 + 대기시간 대폭 증가
            if precision == "low":
                cmd = self.CMD_MEASURE_LOW_PRECISION
                wait_time = 0.5  # 500ms (기존 10ms → 500ms)
                print(f"📊 LOW 정밀도 모드 사용 (대기시간: {wait_time}초)")
            elif precision == "medium":
                cmd = self.CMD_MEASURE_MEDIUM_PRECISION
                wait_time = 0.6  # 600ms (기존 20ms → 600ms)
                print(f"📊 MEDIUM 정밀도 모드 사용 (대기시간: {wait_time}초)")
            else:  # high precision
                cmd = self.CMD_MEASURE_HIGH_PRECISION
                wait_time = 0.8  # 800ms (기존 50ms → 800ms)
                print(f"📊 HIGH 정밀도 모드 사용 (대기시간: {wait_time}초)")
            
            # 소프트 리셋 추가 (안정성 향상)
            try:
                reset_msg = smbus2.i2c_msg.write(self.address, [self.CMD_SOFT_RESET])
                self.bus.i2c_rdwr(reset_msg)
                time.sleep(0.1)  # 리셋 후 안정화
                print("🔄 센서 소프트 리셋 완료")
            except:
                print("⚠️ 소프트 리셋 실패 (계속 진행)")
            
            # 측정 명령 전송
            print(f"📡 측정 명령 전송: 0x{cmd:02x}")
            write_msg = smbus2.i2c_msg.write(self.address, [cmd])
            self.bus.i2c_rdwr(write_msg)
            
            # 🔧 개선1: 대폭 증가된 측정 완료 대기시간
            print(f"⏳ 측정 완료 대기 중... ({wait_time}초)")
            time.sleep(wait_time)
            
            # 데이터 읽기
            print("📖 데이터 읽기 시도")
            read_msg = smbus2.i2c_msg.read(self.address, 6)
            self.bus.i2c_rdwr(read_msg)
            
            # 읽은 데이터 처리
            data = list(read_msg)
            print(f"📊 원시 데이터: {[hex(x) for x in data]}")
            
            # 온도 및 습도 데이터 분리
            t_data = [data[0], data[1]]
            t_crc = data[2]
            rh_data = [data[3], data[4]]
            rh_crc = data[5]
            
            # CRC 검증
            t_crc_ok = self.verify_crc(t_data, t_crc)
            rh_crc_ok = self.verify_crc(rh_data, rh_crc)
            
            print(f"🔐 CRC 검증: 온도={t_crc_ok}, 습도={rh_crc_ok}")
            
            if not t_crc_ok or not rh_crc_ok:
                print(f"❌ CRC 검증 실패")
                return None
            
            # 원시 데이터를 실제 값으로 변환
            t_raw = (t_data[0] << 8) | t_data[1]
            rh_raw = (rh_data[0] << 8) | rh_data[1]
            
            temperature = -45 + 175 * (t_raw / 65535.0)
            humidity = max(0, min(100, -6 + 125 * (rh_raw / 65535.0)))
            
            # 비정상적인 값 필터링
            if temperature > 80 or temperature < -20:
                print(f"❌ 비정상적인 온도: {temperature}°C")
                return None
            
            if humidity > 100:
                print(f"❌ 비정상적인 습도: {humidity}%")
                return None
            
            print(f"✅ 성공: 온도={temperature:.2f}°C, 습도={humidity:.2f}%")
            return round(temperature, 2), round(humidity, 2)
            
        except Exception as e:
            print(f"❌ 측정 실패: {e}")
            raise Exception(f"온습도 측정 실패: {e}")
    
    def read_with_improved_retry(self, precision="low", max_retries=3):
        """
        🔧 개선3: 재시도 간격 대폭 증가된 측정
        
        Args:
            precision: 측정 정밀도 (기본값: "low")
            max_retries: 최대 재시도 횟수
        """
        for attempt in range(max_retries):
            try:
                print(f"\\n🔄 시도 {attempt + 1}/{max_retries}")
                result = self.read_temperature_humidity_improved(precision)
                
                if result:
                    print(f"✅ 시도 {attempt + 1}에서 성공!")
                    return result
                else:
                    print(f"⚠️ 시도 {attempt + 1}: CRC 에러")
                    
            except Exception as e:
                print(f"❌ 시도 {attempt + 1}: {e}")
            
            # 🔧 개선3: 재시도 간격 대폭 증가 (0.2초 → 1.5초)
            if attempt < max_retries - 1:
                retry_delay = 1.5
                print(f"⏳ {retry_delay}초 후 재시도...")
                time.sleep(retry_delay)
        
        print(f"❌ 모든 재시도 실패")
        return None
    
    def test_connection_improved(self):
        """개선된 연결 테스트"""
        try:
            if self.mux_channel is not None:
                self._select_mux_channel()
            
            # 센서 응답 테스트 (소프트 리셋으로)
            reset_msg = smbus2.i2c_msg.write(self.address, [self.CMD_SOFT_RESET])
            self.bus.i2c_rdwr(reset_msg)
            time.sleep(0.1)
            
            return True, "센서 응답 확인"
        except Exception as e:
            return False, f"연결 실패: {e}"

def main():
    """개선된 SHT40 테스트 실행"""
    print("🧪 SHT40 센서 타이밍 개선 테스트")
    print("=" * 50)
    print("적용된 개선사항:")
    print("1. 더 긴 대기시간: 0.5~0.8초")
    print("2. 낮은 정밀도 우선: 'low' 모드")
    print("3. 재시도 간격: 1.5초")
    print("=" * 50)
    
    # 기존 테스트에서 발견된 센서 사용
    bus = 1
    address = 0x44
    mux_channel = 1
    mux_address = 0x70
    
    print(f"\\n📡 테스트 대상: Bus {bus}, CH {mux_channel}, 0x{address:02x}")
    
    # 센서 연결
    sensor = SHT40SensorImproved(bus=bus, address=address, mux_channel=mux_channel, mux_address=mux_address)
    
    try:
        if not sensor.connect():
            print("❌ 센서 연결 실패")
            return False
        
        # 연결 테스트
        print("\\n🔗 연결 테스트")
        success, message = sensor.test_connection_improved()
        print(f"결과: {success} - {message}")
        
        if not success:
            print("❌ 연결 테스트 실패")
            return False
        
        # 개선된 측정 테스트 (5회)
        print("\\n📊 개선된 측정 테스트 (5회)")
        print("-" * 50)
        
        success_count = 0
        test_count = 5
        
        for i in range(test_count):
            print(f"\\n=== 측정 {i+1}/{test_count} ===")
            start_time = time.time()
            
            result = sensor.read_with_improved_retry(precision="low", max_retries=2)
            
            elapsed = time.time() - start_time
            
            if result:
                temp, humidity = result
                success_count += 1
                print(f"🎉 측정 {i+1} 성공: 온도={temp}°C, 습도={humidity}% (소요시간: {elapsed:.2f}초)")
            else:
                print(f"💥 측정 {i+1} 실패 (소요시간: {elapsed:.2f}초)")
            
            # 측정 간 간격
            if i < test_count - 1:
                print("⏳ 다음 측정까지 2초 대기...")
                time.sleep(2)
        
        # 결과 요약
        print("\\n" + "=" * 50)
        print("📊 테스트 결과 요약")
        print("=" * 50)
        success_rate = (success_count / test_count) * 100
        print(f"총 측정 횟수: {test_count}")
        print(f"성공 횟수: {success_count}")
        print(f"실패 횟수: {test_count - success_count}")
        print(f"성공률: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\\n🎉 테스트 성공! 개선사항이 효과적입니다.")
            print("✅ 이제 실제 센서 모듈에 적용할 수 있습니다.")
            return True
        elif success_rate >= 40:
            print("\\n⚠️ 부분적 개선. 추가 조정이 필요합니다.")
            return False
        else:
            print("\\n❌ 개선 효과 없음. 하드웨어 문제일 가능성이 높습니다.")
            return False
            
    except Exception as e:
        print(f"\\n❌ 테스트 실행 오류: {e}")
        return False
    finally:
        sensor.close()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n⏹️ 사용자에 의해 테스트 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)