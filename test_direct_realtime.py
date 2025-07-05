#!/usr/bin/env python3
"""
SDP810 직접 센서 실시간 변화 감지 테스트
=====================================
API 없이 센서에서 직접 읽어서 실시간 변화 확인
"""

import time
import struct
import sys
from datetime import datetime

try:
    import smbus2
    I2C_AVAILABLE = True
    print("✅ smbus2 라이브러리 로드 성공")
except ImportError:
    I2C_AVAILABLE = False
    print("❌ smbus2 라이브러리 없음 - 라즈베리파이에서 실행하세요")
    sys.exit(1)

class DirectRealtimeTest:
    """직접 센서 실시간 변화 감지"""
    
    SDP810_ADDRESS = 0x25
    TCA9548A_ADDRESS = 0x70
    MUX_CHANNEL = 0
    I2C_BUS = 1
    
    def __init__(self):
        """초기화"""
        print(f"🔧 SDP810 직접 실시간 테스트 초기화")
        
        try:
            self.bus = smbus2.SMBus(self.I2C_BUS)
            print("✅ I2C 버스 연결 성공")
        except Exception as e:
            print(f"❌ I2C 버스 연결 실패: {e}")
            sys.exit(1)
            
        self.previous_values = []
        self.change_count = 0
        self.no_change_count = 0
    
    def _calculate_crc8(self, data):
        """CRC8 체크섬 계산"""
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return crc & 0xFF
    
    def select_mux_channel(self):
        """TCA9548A 멀티플렉서 채널 선택"""
        try:
            channel_mask = 1 << self.MUX_CHANNEL
            self.bus.write_byte(self.TCA9548A_ADDRESS, channel_mask)
            time.sleep(0.01)
            return True
        except Exception as e:
            print(f"❌ MUX 채널 선택 실패: {e}")
            return False
    
    def read_single_pressure(self):
        """단일 압력 읽기"""
        try:
            # 3바이트 읽기: [pressure_msb, pressure_lsb, crc]
            read_msg = smbus2.i2c_msg.read(self.SDP810_ADDRESS, 3)
            self.bus.i2c_rdwr(read_msg)
            raw_data = list(read_msg)
            
            if len(raw_data) != 3:
                return None, f"데이터 길이 오류: {len(raw_data)}"
            
            pressure_msb = raw_data[0]
            pressure_lsb = raw_data[1]
            received_crc = raw_data[2]
            
            # CRC 검증
            calculated_crc = self._calculate_crc8([pressure_msb, pressure_lsb])
            if calculated_crc != received_crc:
                return None, f"CRC 오류: 계산={calculated_crc:02X}, 수신={received_crc:02X}"
            
            # 16비트 부호있는 정수로 변환
            raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]
            
            # 다양한 스케일링으로 변환
            pressure_240 = raw_pressure / 240.0  # 추천 스케일링
            pressure_60 = raw_pressure / 60.0    # 현재 API 스케일링
            
            return {
                'raw': raw_pressure,
                'pressure_240': pressure_240,
                'pressure_60': pressure_60,
                'timestamp': datetime.now()
            }, "OK"
            
        except Exception as e:
            return None, f"센서 읽기 오류: {e}"
    
    def test_realtime_changes(self, duration=30, interval=0.5):
        """실시간 변화 감지 테스트"""
        print(f"\n🔄 {duration}초간 {interval}초 간격으로 직접 센서 실시간 변화 테스트")
        print("📌 센서에 물리적 변화를 주면서 테스트하세요 (바람, 압력 변화 등)")
        print("=" * 90)
        
        if not self.select_mux_channel():
            return
        
        start_time = time.time()
        measurement_count = 0
        
        print(f"{'#':>3} | {'시간':>12} | {'Raw':>6} | {'240스케일':>10} | {'60스케일':>9} | {'변화':>10}")
        print("-" * 90)
        
        while time.time() - start_time < duration:
            measurement_count += 1
            current_time = datetime.now()
            
            # 센서 데이터 읽기
            result, message = self.read_single_pressure()
            
            if result:
                pressure_240 = result['pressure_240']
                pressure_60 = result['pressure_60']
                raw_value = result['raw']
                
                # 변화 감지 (240 스케일링 기준)
                change_indicator = "🎯 첫 측정"
                if self.previous_values:
                    last_value = self.previous_values[-1]['pressure_240']
                    change = abs(pressure_240 - last_value)
                    
                    if change > 0.001:  # 0.001 Pa 이상 변화
                        self.change_count += 1
                        if change > 0.01:
                            change_indicator = f"🚨 큰변화: {change:.4f}"
                        elif change > 0.005:
                            change_indicator = f"📈 중변화: {change:.4f}"
                        else:
                            change_indicator = f"📊 소변화: {change:.4f}"
                    else:
                        self.no_change_count += 1
                        change_indicator = f"⏸️ 변화없음"
                
                print(f"{measurement_count:3d} | {current_time.strftime('%H:%M:%S.%f')[:-3]} | {raw_value:6d} | {pressure_240:10.4f} | {pressure_60:9.2f} | {change_indicator}")
                
                # 이전 값 저장 (최근 10개만 유지)
                self.previous_values.append(result)
                if len(self.previous_values) > 10:
                    self.previous_values.pop(0)
                    
            else:
                print(f"{measurement_count:3d} | {current_time.strftime('%H:%M:%S.%f')[:-3]} | 센서 오류: {message}")
            
            time.sleep(interval)
        
        return measurement_count
    
    def analyze_results(self, total_measurements):
        """결과 분석"""
        print("\n" + "=" * 90)
        print("📊 직접 센서 실시간 변화 분석 결과")
        print("=" * 90)
        
        if not self.previous_values:
            print("❌ 측정된 데이터가 없습니다")
            return
        
        # 기본 통계 (240 스케일링 기준)
        pressures = [v['pressure_240'] for v in self.previous_values]
        raw_values = [v['raw'] for v in self.previous_values]
        
        avg_pressure = sum(pressures) / len(pressures)
        min_pressure = min(pressures)
        max_pressure = max(pressures)
        pressure_range = max_pressure - min_pressure
        
        avg_raw = sum(raw_values) / len(raw_values)
        raw_range = max(raw_values) - min(raw_values)
        
        print(f"📈 총 측정 횟수: {total_measurements}")
        print(f"✅ 성공한 측정: {len(self.previous_values)}")
        print(f"📊 변화 감지: {self.change_count}회")
        print(f"⏸️ 변화 없음: {self.no_change_count}회")
        
        if total_measurements > 0:
            success_rate = (len(self.previous_values) / total_measurements) * 100
            change_rate = (self.change_count / (self.change_count + self.no_change_count)) * 100 if (self.change_count + self.no_change_count) > 0 else 0
            print(f"✅ 측정 성공률: {success_rate:.1f}%")
            print(f"🎯 변화 감지율: {change_rate:.1f}%")
        
        print(f"\n📏 원시값 통계:")
        print(f"   평균: {avg_raw:.1f}")
        print(f"   범위: {min(raw_values)} ~ {max(raw_values)} (변동: {raw_range})")
        
        print(f"\n📏 압력값 통계 (240 스케일링):")
        print(f"   평균: {avg_pressure:.4f} Pa")
        print(f"   범위: {min_pressure:.4f} ~ {max_pressure:.4f} Pa")
        print(f"   변동: {pressure_range:.4f} Pa")
        
        # 최근 5개 값 표시
        print(f"\n📋 최근 측정값들:")
        for i, value in enumerate(self.previous_values[-5:], 1):
            timestamp = value['timestamp'].strftime('%H:%M:%S.%f')[:-3]
            print(f"   {i}. Raw={value['raw']:4d}, 240스케일={value['pressure_240']:8.4f} Pa @ {timestamp}")
        
        # 결론
        print(f"\n🎯 결론:")
        if self.change_count > 0:
            print(f"   ✅ 센서가 실시간 변화를 감지하고 있습니다 ({self.change_count}회 변화)")
            if pressure_range > 0.01:
                print(f"   📈 충분한 압력 변화가 감지됩니다 ({pressure_range:.4f} Pa)")
            else:
                print(f"   ⚠️ 압력 변화가 작습니다 ({pressure_range:.4f} Pa) - 더 큰 물리적 변화 필요")
        else:
            print(f"   ❌ 센서 변화가 감지되지 않습니다")
            print(f"   💡 센서에 더 큰 물리적 변화를 주어보세요 (바람, 압력 등)")
        
        if raw_range > 0:
            print(f"   🔧 원시값 변동: {raw_range} (센서가 정상적으로 반응)")
        else:
            print(f"   ⚠️ 원시값 변동 없음 - 센서 연결 상태 확인 필요")
    
    def cleanup(self):
        """리소스 정리"""
        try:
            self.bus.write_byte(self.TCA9548A_ADDRESS, 0x00)
            self.bus.close()
            print("🔧 리소스 정리 완료")
        except:
            pass

def main():
    """메인 테스트 실행"""
    print("🚀 SDP810 직접 센서 실시간 변화 감지 테스트")
    print("📌 이 테스트는 API 없이 센서에서 직접 데이터를 읽습니다")
    print("")
    
    tester = DirectRealtimeTest()
    
    try:
        # 30초간 0.5초 간격으로 테스트
        total_measurements = tester.test_realtime_changes(duration=30, interval=0.5)
        
        # 결과 분석
        tester.analyze_results(total_measurements)
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자가 테스트를 중단했습니다")
        tester.analyze_results(len(tester.previous_values))
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()