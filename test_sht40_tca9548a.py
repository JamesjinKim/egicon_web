#!/usr/bin/env python3
"""
SHT40 온습도 센서 TCA9548A 멀티플렉서 테스트
===========================================
현재 EG-ICON 시스템의 이중 TCA9548A 환경에서 SHT40 센서 테스트

테스트 환경:
- I2C Bus 0 → TCA9548A #1 (0x70) → 8채널 (CH 0-7)
- I2C Bus 1 → TCA9548A #2 (0x70) → 8채널 (CH 8-15)
- SHT40 센서 주소: 0x44, 0x45

운영 시 중요사항:
- 라즈베리파이에서만 실행 가능 (Mac에서는 I2C 불가)
- 실행 전 i2cdetect로 하드웨어 연결 확인 필요
- sudo 권한 필요할 수 있음
"""

import sys
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional

# 기존 SHT40 센서 모듈 import
try:
    from sht40_sensor import SHT40Sensor, scan_sht40_sensors
    import smbus2
    I2C_AVAILABLE = True
except ImportError as e:
    print(f"❌ I2C 라이브러리 또는 SHT40 모듈 import 실패: {e}")
    print("필요한 라이브러리:")
    print("  pip install smbus2")
    print("또는 sht40_sensor.py 파일이 없는 경우 확인하세요.")
    I2C_AVAILABLE = False

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SHT40TCA9548ATest:
    """SHT40 센서 TCA9548A 멀티플렉서 테스트 클래스"""
    
    def __init__(self):
        """테스트 환경 초기화"""
        # TCA9548A 멀티플렉서 설정 (EG-ICON 시스템 환경)
        self.tca_config = {
            0: {"address": 0x70, "channels": list(range(8))},    # I2C Bus 0 → CH 0-7
            1: {"address": 0x70, "channels": list(range(8))}     # I2C Bus 1 → CH 8-15
        }
        
        # SHT40 센서 주소
        self.sht40_addresses = [0x44, 0x45]
        
        # 발견된 센서 정보 저장
        self.found_sensors = []
        
        print("🔬 SHT40 TCA9548A 멀티플렉서 테스트 시작")
        print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    
    def check_i2c_environment(self) -> bool:
        """I2C 환경 및 라이브러리 확인"""
        print("\n🔍 I2C 환경 확인")
        
        if not I2C_AVAILABLE:
            print("❌ I2C 라이브러리가 사용 불가능합니다")
            print("  해결 방법:")
            print("  1. 라즈베리파이에서 실행하세요")
            print("  2. pip install smbus2")
            print("  3. I2C가 활성화되어 있는지 확인하세요 (sudo raspi-config)")
            return False
        
        print("✅ I2C 라이브러리 사용 가능")
        
        # I2C 버스 접근 테스트
        for bus_num in [0, 1]:
            try:
                bus = smbus2.SMBus(bus_num)
                bus.close()
                print(f"✅ I2C Bus {bus_num} 접근 가능")
            except Exception as e:
                print(f"❌ I2C Bus {bus_num} 접근 실패: {e}")
                return False
        
        return True
    
    def scan_tca9548a_multiplexers(self) -> bool:
        """TCA9548A 멀티플렉서 검색 및 상태 확인"""
        print("\n🔍 TCA9548A 멀티플렉서 스캔")
        
        tca_found = False
        
        for bus_num, config in self.tca_config.items():
            tca_address = config["address"]
            print(f"\n📡 I2C Bus {bus_num} → TCA9548A (0x{tca_address:02X}) 확인 중...")
            
            try:
                bus = smbus2.SMBus(bus_num)
                
                # TCA9548A 응답 테스트
                try:
                    # 모든 채널 비활성화
                    bus.write_byte(tca_address, 0x00)
                    time.sleep(0.01)
                    
                    # 현재 채널 상태 읽기
                    current_channels = bus.read_byte(tca_address)
                    
                    print(f"  ✅ TCA9548A 응답 확인 (현재 채널: 0x{current_channels:02X})")
                    tca_found = True
                    
                    # 각 채널 테스트
                    print(f"  🔧 채널 테스트 중...")
                    for channel in range(8):
                        try:
                            # 채널 선택
                            channel_mask = 1 << channel
                            bus.write_byte(tca_address, channel_mask)
                            time.sleep(0.01)
                            
                            # 채널 선택 확인
                            selected = bus.read_byte(tca_address)
                            if selected == channel_mask:
                                display_channel = channel if bus_num == 0 else channel + 8
                                print(f"    ✅ CH {display_channel} (Bus {bus_num}, Channel {channel}) 정상")
                            else:
                                print(f"    ❌ CH {channel} 선택 실패")
                        
                        except Exception as e:
                            print(f"    ⚠️ CH {channel} 테스트 실패: {e}")
                    
                    # 모든 채널 비활성화
                    bus.write_byte(tca_address, 0x00)
                
                except Exception as e:
                    print(f"  ❌ TCA9548A 통신 실패: {e}")
                
                bus.close()
                
            except Exception as e:
                print(f"  ❌ I2C Bus {bus_num} 연결 실패: {e}")
        
        if tca_found:
            print("\n✅ TCA9548A 멀티플렉서 스캔 완료")
        else:
            print("\n❌ TCA9548A 멀티플렉서를 찾을 수 없습니다")
            print("  확인사항:")
            print("  1. TCA9548A가 올바르게 연결되었는지 확인")
            print("  2. I2C 주소가 0x70인지 확인")
            print("  3. 전원 공급이 정상인지 확인")
        
        return tca_found
    
    def scan_sht40_sensors_comprehensive(self) -> List[Dict]:
        """모든 버스와 채널에서 SHT40 센서 검색"""
        print("\n🔍 SHT40 센서 전체 스캔")
        
        found_sensors = []
        
        for bus_num, config in self.tca_config.items():
            tca_address = config["address"]
            channels = config["channels"]
            
            print(f"\n📡 I2C Bus {bus_num} 스캔 중...")
            
            try:
                bus = smbus2.SMBus(bus_num)
                
                # 직접 연결 센서 스캔 (멀티플렉서 없이)
                print(f"  🔍 직접 연결 센서 스캔...")
                for address in self.sht40_addresses:
                    try:
                        # 직접 SHT40 센서 연결 테스트
                        sensor = SHT40Sensor(bus=bus_num, address=address)
                        sensor.connect()
                        
                        success, message = sensor.test_connection()
                        if success:
                            sensor_info = {
                                "bus": bus_num,
                                "address": f"0x{address:02X}",
                                "mux_channel": None,
                                "connection_type": "direct",
                                "test_result": message,
                                "sensor_type": "SHT40",
                                "interface": "I2C"
                            }
                            found_sensors.append(sensor_info)
                            print(f"    ✅ Bus {bus_num} 직접 연결: SHT40 발견 (0x{address:02X}) - {message}")
                        
                        sensor.close()
                        
                    except Exception as e:
                        print(f"    ⚪ Bus {bus_num} 직접 (0x{address:02X}): 응답 없음")
                
                # 멀티플렉서 채널별 스캔
                print(f"  🔍 TCA9548A 채널별 스캔...")
                for channel in channels:
                    display_channel = channel if bus_num == 0 else channel + 8
                    print(f"    📡 CH {display_channel} (Bus {bus_num}, Channel {channel}) 스캔...")
                    
                    try:
                        # 채널 선택
                        channel_mask = 1 << channel
                        bus.write_byte(tca_address, channel_mask)
                        time.sleep(0.01)
                        
                        # 해당 채널에서 SHT40 센서 검색
                        for address in self.sht40_addresses:
                            try:
                                sensor = SHT40Sensor(
                                    bus=bus_num, 
                                    address=address, 
                                    mux_channel=channel, 
                                    mux_address=tca_address
                                )
                                sensor.connect()
                                
                                success, message = sensor.test_connection()
                                if success:
                                    sensor_info = {
                                        "bus": bus_num,
                                        "address": f"0x{address:02X}",
                                        "mux_channel": channel,
                                        "display_channel": display_channel,
                                        "mux_address": f"0x{tca_address:02X}",
                                        "connection_type": "multiplexed",
                                        "test_result": message,
                                        "sensor_type": "SHT40",
                                        "interface": "I2C"
                                    }
                                    found_sensors.append(sensor_info)
                                    print(f"      ✅ SHT40 발견 (0x{address:02X}) - {message}")
                                
                                sensor.close()
                                
                            except Exception as e:
                                # 센서가 없는 것은 정상이므로 debug 레벨로만 로깅
                                logger.debug(f"CH {display_channel} (0x{address:02X}): {e}")
                        
                        # 채널 비활성화
                        bus.write_byte(tca_address, 0x00)
                        
                    except Exception as e:
                        print(f"      ❌ CH {display_channel} 스캔 실패: {e}")
                
                bus.close()
                
            except Exception as e:
                print(f"  ❌ Bus {bus_num} 스캔 실패: {e}")
        
        self.found_sensors = found_sensors
        print(f"\n📊 SHT40 센서 스캔 결과: {len(found_sensors)}개 센서 발견")
        
        return found_sensors
    
    def test_continuous_measurement(self, duration: int = 30) -> bool:
        """연속 측정 테스트"""
        if not self.found_sensors:
            print("❌ 연속 측정 테스트를 위한 센서가 없습니다")
            return False
        
        # 첫 번째 발견된 센서로 테스트
        sensor_info = self.found_sensors[0]
        
        print(f"\n🔄 연속 측정 테스트 ({duration}초)")
        print(f"📡 테스트 센서: Bus {sensor_info['bus']}, CH {sensor_info.get('display_channel', 'Direct')}, {sensor_info['address']}")
        
        try:
            # 센서 연결
            if sensor_info['connection_type'] == 'direct':
                sensor = SHT40Sensor(
                    bus=sensor_info['bus'], 
                    address=int(sensor_info['address'], 16)
                )
            else:
                sensor = SHT40Sensor(
                    bus=sensor_info['bus'], 
                    address=int(sensor_info['address'], 16),
                    mux_channel=sensor_info['mux_channel'],
                    mux_address=int(sensor_info['mux_address'], 16)
                )
            
            sensor.connect()
            
            print(f"⏰ 시작 시간: {datetime.now().strftime('%H:%M:%S')}")
            print("📊 측정 데이터:")
            print("   시간     | 온도(°C) | 습도(%RH) | 상태")
            print("-" * 45)
            
            success_count = 0
            total_measurements = 0
            temp_values = []
            humidity_values = []
            
            for i in range(duration):
                try:
                    temp, humidity = sensor.read_with_retry(precision="high", max_retries=2)
                    
                    if temp is not None and humidity is not None:
                        current_time = datetime.now().strftime('%H:%M:%S')
                        status = "✅ 성공"
                        success_count += 1
                        temp_values.append(temp)
                        humidity_values.append(humidity)
                        
                        print(f"   {current_time} | {temp:6.1f}   | {humidity:7.1f}   | {status}")
                    else:
                        current_time = datetime.now().strftime('%H:%M:%S')
                        status = "❌ 실패"
                        print(f"   {current_time} |    --    |    --     | {status}")
                    
                    total_measurements += 1
                    time.sleep(1)  # 1초 간격
                    
                except KeyboardInterrupt:
                    print("\n⏹️  사용자에 의해 측정 중단됨")
                    break
                except Exception as e:
                    current_time = datetime.now().strftime('%H:%M:%S')
                    print(f"   {current_time} |    --    |    --     | ❌ 오류: {e}")
                    total_measurements += 1
            
            sensor.close()
            
            # 통계 출력
            print("-" * 45)
            success_rate = (success_count / total_measurements) * 100 if total_measurements > 0 else 0
            print(f"📊 측정 통계:")
            print(f"   총 측정 횟수: {total_measurements}")
            print(f"   성공 횟수: {success_count}")
            print(f"   성공률: {success_rate:.1f}%")
            
            if temp_values and humidity_values:
                print(f"   온도 범위: {min(temp_values):.1f}°C ~ {max(temp_values):.1f}°C (평균: {sum(temp_values)/len(temp_values):.1f}°C)")
                print(f"   습도 범위: {min(humidity_values):.1f}%RH ~ {max(humidity_values):.1f}%RH (평균: {sum(humidity_values)/len(humidity_values):.1f}%RH)")
            
            return success_rate > 80  # 80% 이상 성공률을 기준으로 판정
            
        except Exception as e:
            print(f"❌ 연속 측정 테스트 실패: {e}")
            return False
    
    def generate_test_report(self) -> str:
        """테스트 결과 리포트 생성"""
        report = []
        report.append("=" * 60)
        report.append("SHT40 TCA9548A 멀티플렉서 테스트 리포트")
        report.append("=" * 60)
        report.append(f"테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"발견된 센서 수: {len(self.found_sensors)}개")
        report.append("")
        
        if self.found_sensors:
            report.append("📋 발견된 SHT40 센서 목록:")
            for i, sensor in enumerate(self.found_sensors, 1):
                report.append(f"  {i}. Bus {sensor['bus']}")
                if sensor['connection_type'] == 'direct':
                    report.append(f"     연결: 직접 연결")
                else:
                    report.append(f"     연결: TCA9548A {sensor['mux_address']} CH {sensor['display_channel']}")
                report.append(f"     주소: {sensor['address']}")
                report.append(f"     테스트: {sensor['test_result']}")
                report.append("")
        else:
            report.append("❌ SHT40 센서를 찾을 수 없습니다.")
            report.append("")
            report.append("문제 해결 방법:")
            report.append("1. SHT40 센서가 올바르게 연결되었는지 확인")
            report.append("2. I2C 주소가 0x44 또는 0x45인지 확인")
            report.append("3. TCA9548A 멀티플렉서 연결 상태 확인")
            report.append("4. 전원 공급 및 배선 확인")
            report.append("5. i2cdetect -y 0, i2cdetect -y 1 명령으로 하드웨어 확인")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def run_complete_test(self, continuous_test_duration: int = 10) -> bool:
        """전체 테스트 실행"""
        try:
            # 1. I2C 환경 확인
            if not self.check_i2c_environment():
                return False
            
            # 2. TCA9548A 멀티플렉서 스캔
            if not self.scan_tca9548a_multiplexers():
                print("\n⚠️ TCA9548A 스캔 실패. 직접 연결 센서만 검색합니다.")
            
            # 3. SHT40 센서 스캔
            self.scan_sht40_sensors_comprehensive()
            
            # 4. 연속 측정 테스트 (센서가 발견된 경우)
            if self.found_sensors:
                continuous_success = self.test_continuous_measurement(continuous_test_duration)
                if continuous_success:
                    print("\n✅ 연속 측정 테스트 성공")
                else:
                    print("\n⚠️ 연속 측정 테스트에서 일부 문제 발견")
            
            # 5. 테스트 리포트 출력
            report = self.generate_test_report()
            print("\n" + report)
            
            return len(self.found_sensors) > 0
            
        except KeyboardInterrupt:
            print("\n⏹️  사용자에 의해 테스트 중단됨")
            return False
        except Exception as e:
            print(f"\n❌ 테스트 실행 중 오류 발생: {e}")
            return False

def main():
    """메인 함수"""
    print("🚀 SHT40 TCA9548A 멀티플렉서 테스트 프로그램")
    print("=" * 60)
    print("이 프로그램은 다음을 테스트합니다:")
    print("1. I2C 환경 및 라이브러리 확인")
    print("2. TCA9548A 이중 멀티플렉서 스캔")
    print("3. 모든 채널에서 SHT40 센서 검색")
    print("4. 발견된 센서의 연속 측정 테스트")
    print("=" * 60)
    
    if not I2C_AVAILABLE:
        print("❌ 이 프로그램은 라즈베리파이에서만 실행 가능합니다.")
        print("Mac에서는 센서 연동 테스트가 불가능합니다.")
        sys.exit(1)
    
    try:
        # 연속 측정 시간 설정
        duration = 10  # 기본 10초
        if len(sys.argv) > 1:
            try:
                duration = int(sys.argv[1])
                if duration < 5 or duration > 300:
                    print("⚠️ 연속 측정 시간은 5초~300초 사이로 설정하세요.")
                    duration = 10
            except ValueError:
                print("⚠️ 잘못된 시간 형식. 기본값 10초로 설정합니다.")
        
        print(f"🔧 연속 측정 테스트 시간: {duration}초")
        print("\n시작하려면 Enter를 누르세요 (Ctrl+C로 중단 가능)...")
        input()
        
        # 테스트 실행
        tester = SHT40TCA9548ATest()
        success = tester.run_complete_test(continuous_test_duration=duration)
        
        if success:
            print("\n🎉 SHT40 센서 테스트 완료! 센서가 정상적으로 작동합니다.")
            print("이제 대시보드 시스템에 통합할 수 있습니다.")
        else:
            print("\n⚠️ SHT40 센서 테스트에서 문제가 발견되었습니다.")
            print("하드웨어 연결을 확인한 후 다시 시도하세요.")
            
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  테스트가 사용자에 의해 중단되었습니다.")
        return 1
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)