#!/usr/bin/env python3
"""
SDP810 폴링 주기별 안정성 테스트
===============================
다양한 폴링 간격에서 CRC 오류율과 센서 반응성 비교
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

class PollingStabilityTest:
    """폴링 주기별 안정성 테스트"""
    
    SDP810_ADDRESS = 0x25
    TCA9548A_ADDRESS = 0x70
    MUX_CHANNEL = 0
    I2C_BUS = 1
    
    def __init__(self):
        """초기화"""
        print(f"🔧 SDP810 폴링 안정성 테스트 초기화")
        
        try:
            self.bus = smbus2.SMBus(self.I2C_BUS)
            print("✅ I2C 버스 연결 성공")
        except Exception as e:
            print(f"❌ I2C 버스 연결 실패: {e}")
            sys.exit(1)
    
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
                return None, "길이오류", f"데이터 길이 오류: {len(raw_data)}"
            
            pressure_msb = raw_data[0]
            pressure_lsb = raw_data[1]
            received_crc = raw_data[2]
            
            # CRC 검증
            calculated_crc = self._calculate_crc8([pressure_msb, pressure_lsb])
            crc_valid = calculated_crc == received_crc
            
            if not crc_valid:
                return None, "CRC오류", f"CRC 불일치: 계산={calculated_crc:02X}, 수신={received_crc:02X}"
            
            # 16비트 부호있는 정수로 변환
            raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]
            pressure_240 = raw_pressure / 240.0
            
            return pressure_240, "성공", "OK"
            
        except Exception as e:
            return None, "통신오류", f"센서 읽기 오류: {e}"
    
    def test_polling_interval(self, interval, duration=20, description=""):
        """특정 폴링 간격 테스트"""
        print(f"\n📊 폴링 간격 {interval}초 테스트 ({description})")
        print(f"   지속시간: {duration}초")
        print("-" * 60)
        
        if not self.select_mux_channel():
            return None
        
        results = {
            'interval': interval,
            'duration': duration,
            'total_attempts': 0,
            'successful_reads': 0,
            'crc_errors': 0,
            'comm_errors': 0,
            'length_errors': 0,
            'pressure_values': [],
            'timestamps': []
        }
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            results['total_attempts'] += 1
            
            pressure, status, message = self.read_single_pressure()
            current_time = datetime.now()
            
            if pressure is not None:
                results['successful_reads'] += 1
                results['pressure_values'].append(pressure)
                results['timestamps'].append(current_time)
                print(f"  #{results['total_attempts']:2d} | {current_time.strftime('%H:%M:%S.%f')[:-3]} | {pressure:8.4f} Pa | ✅")
            else:
                if status == "CRC오류":
                    results['crc_errors'] += 1
                elif status == "통신오류":
                    results['comm_errors'] += 1
                elif status == "길이오류":
                    results['length_errors'] += 1
                print(f"  #{results['total_attempts']:2d} | {current_time.strftime('%H:%M:%S.%f')[:-3]} | 오류: {status} | ❌")
            
            time.sleep(interval)
        
        return results
    
    def analyze_results(self, results):
        """결과 분석"""
        if not results:
            return
        
        total = results['total_attempts']
        success = results['successful_reads']
        crc_err = results['crc_errors']
        comm_err = results['comm_errors']
        len_err = results['length_errors']
        
        success_rate = (success / total * 100) if total > 0 else 0
        crc_error_rate = (crc_err / total * 100) if total > 0 else 0
        
        print(f"\n📈 결과 분석:")
        print(f"   총 시도: {total}회")
        print(f"   성공: {success}회 ({success_rate:.1f}%)")
        print(f"   CRC 오류: {crc_err}회 ({crc_error_rate:.1f}%)")
        print(f"   통신 오류: {comm_err}회")
        print(f"   길이 오류: {len_err}회")
        
        if results['pressure_values']:
            pressures = results['pressure_values']
            avg_pressure = sum(pressures) / len(pressures)
            min_pressure = min(pressures)
            max_pressure = max(pressures)
            pressure_range = max_pressure - min_pressure
            
            print(f"   압력 평균: {avg_pressure:.4f} Pa")
            print(f"   압력 범위: {min_pressure:.4f} ~ {max_pressure:.4f} Pa")
            print(f"   압력 변동: {pressure_range:.4f} Pa")
            
            # 변화 감지
            changes = 0
            if len(pressures) > 1:
                for i in range(1, len(pressures)):
                    if abs(pressures[i] - pressures[i-1]) > 0.001:
                        changes += 1
                change_rate = (changes / (len(pressures) - 1) * 100) if len(pressures) > 1 else 0
                print(f"   변화 감지: {changes}회 ({change_rate:.1f}%)")
        
        return {
            'interval': results['interval'],
            'success_rate': success_rate,
            'crc_error_rate': crc_error_rate,
            'total_errors': crc_err + comm_err + len_err
        }
    
    def run_comprehensive_test(self):
        """종합 안정성 테스트"""
        print("🚀 SDP810 폴링 주기별 안정성 종합 테스트")
        print("=" * 80)
        
        # 다양한 폴링 간격 테스트
        test_intervals = [
            (0.1, "매우 빠름 - 과부하 테스트"),
            (0.5, "빠름 - 현재 대시보드 설정"),
            (1.0, "보통 - 표준 폴링"),
            (2.0, "느림 - 안정성 우선"),
            (5.0, "매우 느림 - 최대 안정성")
        ]
        
        summary_results = []
        
        for interval, description in test_intervals:
            try:
                result = self.test_polling_interval(interval, duration=15, description=description)
                analysis = self.analyze_results(result)
                if analysis:
                    summary_results.append(analysis)
                
                # 센서 휴식 시간
                print(f"   💤 센서 휴식 중... (3초)")
                time.sleep(3)
                
            except KeyboardInterrupt:
                print(f"\n⏹️ 사용자가 테스트를 중단했습니다")
                break
            except Exception as e:
                print(f"❌ {interval}초 테스트 중 오류: {e}")
                continue
        
        # 종합 결과 분석
        self.print_summary(summary_results)
    
    def print_summary(self, results):
        """종합 결과 출력"""
        print("\n" + "=" * 80)
        print("📊 폴링 주기별 종합 분석 결과")
        print("=" * 80)
        
        if not results:
            print("❌ 분석할 결과가 없습니다")
            return
        
        print(f"{'간격':>6} | {'성공률':>8} | {'CRC오류율':>10} | {'총오류':>8} | {'추천도':>8}")
        print("-" * 60)
        
        best_interval = None
        best_score = 0
        
        for result in results:
            interval = result['interval']
            success_rate = result['success_rate']
            crc_error_rate = result['crc_error_rate']
            total_errors = result['total_errors']
            
            # 점수 계산 (성공률 - CRC오류율*2)
            score = success_rate - (crc_error_rate * 2)
            
            if score > best_score:
                best_score = score
                best_interval = interval
            
            # 추천도 표시
            if score >= 90:
                recommendation = "🟢 우수"
            elif score >= 80:
                recommendation = "🟡 양호" 
            elif score >= 70:
                recommendation = "🟠 보통"
            else:
                recommendation = "🔴 부족"
            
            print(f"{interval:>6.1f} | {success_rate:>7.1f}% | {crc_error_rate:>9.1f}% | {total_errors:>7d} | {recommendation}")
        
        print("-" * 60)
        print(f"🎯 최적 폴링 간격: {best_interval}초 (점수: {best_score:.1f})")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        if best_interval <= 0.5:
            print(f"   ✅ 현재 설정({best_interval}초)이 최적입니다")
            print(f"   📈 실시간성과 안정성의 좋은 균형")
        elif best_interval <= 1.0:
            print(f"   ⚡ {best_interval}초로 폴링 간격 조정 권장")
            print(f"   📊 안정성 개선하면서 실시간성 유지")
        else:
            print(f"   🐌 {best_interval}초로 폴링 간격 증가 권장")
            print(f"   🛡️ 안정성 우선 - CRC 오류 최소화")
    
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
    print("🔬 SDP810 센서 폴링 안정성 분석")
    print("📌 다양한 폴링 간격에서 센서 안정성을 테스트합니다")
    print("")
    
    tester = PollingStabilityTest()
    
    try:
        tester.run_comprehensive_test()
        
    except KeyboardInterrupt:
        print("\n⏹️ 전체 테스트가 중단되었습니다")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()