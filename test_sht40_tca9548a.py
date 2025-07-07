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
    
    def test_continuous_measurement(self, test_count: int = 10) -> bool:
        """연속 측정 테스트 (10회 측정)"""
        if not self.found_sensors:
            print("❌ 연속 측정 테스트를 위한 센서가 없습니다")
            return False
        
        # 첫 번째 발견된 센서로 테스트
        sensor_info = self.found_sensors[0]
        
        print(f"\n🔄 SHT40 센서 정확성 테스트 ({test_count}회 측정)")
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
            print("   순번 |   시간   | 온도(°C) | 습도(%RH) |        상태        | 실패 원인")
            print("-" * 85)
            
            success_count = 0
            total_measurements = 0
            temp_values = []
            humidity_values = []
            failure_reasons = {}
            
            measurement_interval = 2  # 2초 간격으로 측정
            
            for i in range(test_count):
                measurement_num = i + 1
                current_time = datetime.now().strftime('%H:%M:%S')
                
                try:
                    print(f"   {measurement_num:2d}   | {current_time} |", end="", flush=True)
                    
                    # 상세한 에러 추적을 위한 측정
                    result = None
                    error_detail = None
                    
                    try:
                        # 정규 호출 사이클에 따른 측정 (CRC 에러 시 스킵하고 다음 사이클 대기)
                        result = sensor.read_with_retry(precision="medium", max_retries=3, base_delay=0.2)
                    except Exception as sensor_error:
                        error_detail = f"센서 통신 실패: {str(sensor_error)}"
                        logger.error(f"측정 {measurement_num} 센서 통신 오류: {sensor_error}")
                    
                    if result is not None:
                        temp, humidity = result
                        success_count += 1
                        temp_values.append(temp)
                        humidity_values.append(humidity)
                        
                        print(f" {temp:6.1f}   | {humidity:7.1f}   |     ✅ 성공      |")
                        logger.info(f"측정 {measurement_num} 성공: 온도={temp:.1f}°C, 습도={humidity:.1f}%RH")
                    else:
                        # 실패 원인 분석
                        if error_detail:
                            failure_reason = error_detail
                        else:
                            # CRC 검증 실패 또는 비정상값
                            try:
                                # 직접 I2C 통신 테스트
                                import smbus2
                                bus = smbus2.SMBus(sensor_info['bus'])
                                
                                # 멀티플렉서 채널 선택 (있는 경우)
                                if sensor_info['connection_type'] == 'multiplexed':
                                    mux_address = int(sensor_info['mux_address'], 16)
                                    channel_mask = 1 << sensor_info['mux_channel']
                                    bus.write_byte(mux_address, channel_mask)
                                    time.sleep(0.01)
                                
                                # SHT40 센서 직접 통신 테스트
                                sensor_address = int(sensor_info['address'], 16)
                                bus.write_i2c_block_data(sensor_address, 0xFD, [])  # Soft reset
                                time.sleep(0.01)
                                
                                # 측정 명령 전송
                                bus.write_i2c_block_data(sensor_address, 0xFD, [])  # Medium precision
                                time.sleep(0.01)
                                
                                # 데이터 읽기 시도
                                raw_data = bus.read_i2c_block_data(sensor_address, 0x00, 6)
                                
                                # CRC 검증
                                def crc8(data):
                                    crc = 0xFF
                                    for byte in data:
                                        crc ^= byte
                                        for _ in range(8):
                                            if crc & 0x80:
                                                crc = (crc << 1) ^ 0x31
                                            else:
                                                crc = crc << 1
                                    return crc & 0xFF
                                
                                temp_crc_ok = crc8(raw_data[0:2]) == raw_data[2]
                                humidity_crc_ok = crc8(raw_data[3:5]) == raw_data[5]
                                
                                if not temp_crc_ok or not humidity_crc_ok:
                                    failure_reason = f"CRC 검증 실패 (온도:{temp_crc_ok}, 습도:{humidity_crc_ok})"
                                else:
                                    # 값 계산
                                    temp_raw = (raw_data[0] << 8) | raw_data[1]
                                    humidity_raw = (raw_data[3] << 8) | raw_data[4]
                                    temp_celsius = -45 + 175 * temp_raw / 65535
                                    humidity_percent = -6 + 125 * humidity_raw / 65535
                                    
                                    if temp_celsius < -40 or temp_celsius > 125 or humidity_percent < 0 or humidity_percent > 100:
                                        failure_reason = f"비정상 값 (온도:{temp_celsius:.1f}°C, 습도:{humidity_percent:.1f}%RH)"
                                    else:
                                        failure_reason = "알 수 없는 필터링 원인"
                                
                                bus.close()
                                
                            except Exception as comm_error:
                                failure_reason = f"I2C 통신 오류: {str(comm_error)}"
                        
                        # 실패 원인 기록
                        if failure_reason in failure_reasons:
                            failure_reasons[failure_reason] += 1
                        else:
                            failure_reasons[failure_reason] = 1
                        
                        print(f"    --    |    --     | ⚠️ 실패 ({len(failure_reason)}) | {failure_reason[:35]}")
                        logger.warning(f"측정 {measurement_num} 실패: {failure_reason}")
                    
                    total_measurements += 1
                    
                except KeyboardInterrupt:
                    print("\n⏹️  사용자에 의해 측정 중단됨")
                    break
                except Exception as e:
                    error_msg = str(e)
                    failure_reason = f"예외 발생: {error_msg}"
                    if failure_reason in failure_reasons:
                        failure_reasons[failure_reason] += 1
                    else:
                        failure_reasons[failure_reason] = 1
                    
                    print(f"    --    |    --     | ❌ 예외 오류    | {error_msg[:35]}")
                    logger.error(f"측정 {measurement_num} 예외 오류: {e}")
                    total_measurements += 1
                
                # 다음 측정까지 대기
                if i < test_count - 1:
                    time.sleep(measurement_interval)
            
            sensor.close()
            
            # 통계 출력
            print("-" * 85)
            success_rate = (success_count / total_measurements) * 100 if total_measurements > 0 else 0
            print(f"📊 측정 통계:")
            print(f"   총 측정 횟수: {total_measurements}")
            print(f"   성공 횟수: {success_count}")
            print(f"   실패 횟수: {total_measurements - success_count}")
            print(f"   성공률: {success_rate:.1f}%")
            
            if temp_values and humidity_values:
                print(f"   온도 범위: {min(temp_values):.1f}°C ~ {max(temp_values):.1f}°C (평균: {sum(temp_values)/len(temp_values):.1f}°C)")
                print(f"   습도 범위: {min(humidity_values):.1f}%RH ~ {max(humidity_values):.1f}%RH (평균: {sum(humidity_values)/len(humidity_values):.1f}%RH)")
            
            # 실패 원인 분석
            if failure_reasons:
                print(f"\n🔍 실패 원인 분석:")
                for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / (total_measurements - success_count)) * 100
                    print(f"   • {reason}: {count}회 ({percentage:.1f}%)")
            
            # 권장사항
            print(f"\n💡 권장사항:")
            if success_rate >= 80:
                print("   ✅ 센서 상태 양호 - Dashboard 통합 가능")
            elif success_rate >= 50:
                print("   ⚠️ 센서 상태 보통 - 하드웨어 점검 권장")
                print("   📋 확인사항:")
                print("      - 전원 공급 안정성")
                print("      - I2C 케이블 연결 상태")
                print("      - 멀티플렉서 접점 확인")
            else:
                print("   ❌ 센서 상태 불량 - 하드웨어 교체 필요")
                print("   📋 필수 확인사항:")
                print("      - SHT40 센서 불량 가능성")
                print("      - I2C 주소 충돌 확인")
                print("      - 배선 및 접지 상태")
            
            return success_rate >= 70  # 70% 이상 성공률을 기준으로 판정
            
        except Exception as e:
            logger.error(f"연속 측정 테스트 전체 실패: {e}")
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
    
    def run_complete_test(self, test_count: int = 10) -> bool:
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
                continuous_success = self.test_continuous_measurement(test_count)
                if continuous_success:
                    print("\n✅ SHT40 센서 정확성 테스트 성공")
                else:
                    print("\n⚠️ SHT40 센서 정확성 테스트에서 문제 발견")
            
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
        # 측정 횟수 설정
        test_count = 10  # 기본 10회
        if len(sys.argv) > 1:
            try:
                test_count = int(sys.argv[1])
                if test_count < 5 or test_count > 50:
                    print("⚠️ 측정 횟수는 5회~50회 사이로 설정하세요.")
                    test_count = 10
            except ValueError:
                print("⚠️ 잘못된 횟수 형식. 기본값 10회로 설정합니다.")
        
        print(f"🔧 SHT40 정확성 테스트 횟수: {test_count}회")
        print("📋 테스트 내용:")
        print("   - 각 측정마다 실패 원인을 상세 분석")
        print("   - CRC 검증 상태 및 통신 오류 원인 추적")
        print("   - 온도/습도 값의 정상 범위 확인")
        print("\n시작하려면 Enter를 누르세요 (Ctrl+C로 중단 가능)...")
        input()
        
        # 테스트 실행
        tester = SHT40TCA9548ATest()
        success = tester.run_complete_test(test_count=test_count)
        
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