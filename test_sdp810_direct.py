#!/usr/bin/env python3
"""
SDP810 센서 직접 테스트 코드
=========================
실제 센서 데이터를 직접 읽어서 API 응답과 비교 검증
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

class DirectSDP810Test:
    """SDP810 센서 직접 테스트 클래스"""
    
    SDP810_ADDRESS = 0x25
    TCA9548A_ADDRESS = 0x70  # Bus 1의 TCA9548A
    MUX_CHANNEL = 0         # Channel 0
    I2C_BUS = 1             # Bus 1
    
    def __init__(self):
        """테스트 초기화"""
        print(f"🔧 SDP810 직접 테스트 초기화")
        print(f"   I2C Bus: {self.I2C_BUS}")
        print(f"   TCA9548A: 0x{self.TCA9548A_ADDRESS:02X}")
        print(f"   MUX Channel: {self.MUX_CHANNEL}")
        print(f"   SDP810 Address: 0x{self.SDP810_ADDRESS:02X}")
        
        try:
            self.bus = smbus2.SMBus(self.I2C_BUS)
            print("✅ I2C 버스 연결 성공")
        except Exception as e:
            print(f"❌ I2C 버스 연결 실패: {e}")
            sys.exit(1)
    
    def _calculate_crc8(self, data):
        """CRC8 체크섬 계산 (SDP810용)"""
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
            print(f"✅ MUX 채널 {self.MUX_CHANNEL} 선택 완료")
            return True
        except Exception as e:
            print(f"❌ MUX 채널 선택 실패: {e}")
            return False
    
    def read_raw_sensor_data(self):
        """센서에서 원시 데이터 직접 읽기"""
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
            
            print(f"📊 원시 데이터: MSB=0x{pressure_msb:02X}, LSB=0x{pressure_lsb:02X}, CRC=0x{received_crc:02X}")
            
            # CRC 검증
            calculated_crc = self._calculate_crc8([pressure_msb, pressure_lsb])
            crc_valid = calculated_crc == received_crc
            print(f"🔍 CRC 검증: 계산값=0x{calculated_crc:02X}, 수신값=0x{received_crc:02X}, 유효={crc_valid}")
            
            # 16비트 부호있는 정수로 변환
            raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]
            print(f"🔢 원시 압력값: {raw_pressure}")
            
            return {
                'raw_data': raw_data,
                'pressure_msb': pressure_msb,
                'pressure_lsb': pressure_lsb,
                'received_crc': received_crc,
                'calculated_crc': calculated_crc,
                'crc_valid': crc_valid,
                'raw_pressure': raw_pressure
            }, "OK"
            
        except Exception as e:
            return None, f"센서 읽기 오류: {e}"
    
    def convert_to_pressure(self, raw_pressure):
        """원시 압력값을 Pa로 변환"""
        # SDP810 스케일링 팩터들 테스트
        scaling_factors = {
            "60": 60.0,      # 일반적인 SDP810-500Pa 값
            "120": 120.0,    # 대안 스케일링
            "240": 240.0,    # 더 높은 해상도
            "1": 1.0,        # 원시값 그대로
        }
        
        print(f"\n📐 압력값 변환 테스트:")
        conversions = {}
        
        for name, factor in scaling_factors.items():
            pressure_pa = raw_pressure / factor
            conversions[name] = pressure_pa
            print(f"   스케일링 {name:>3}: {raw_pressure} / {factor} = {pressure_pa:.4f} Pa")
        
        return conversions
    
    def test_multiple_readings(self, count=5):
        """여러 번 읽어서 안정성 확인"""
        print(f"\n🔄 {count}회 연속 측정 테스트")
        print("=" * 60)
        
        if not self.select_mux_channel():
            return []
        
        results = []
        
        for i in range(count):
            print(f"\n📊 측정 #{i+1}")
            print("-" * 30)
            
            raw_result, message = self.read_raw_sensor_data()
            
            if raw_result:
                conversions = self.convert_to_pressure(raw_result['raw_pressure'])
                
                result = {
                    'measurement': i + 1,
                    'timestamp': datetime.now().isoformat(),
                    'raw_data': raw_result,
                    'conversions': conversions,
                    'status': 'success'
                }
                results.append(result)
                
                # 가장 합리적인 값 추정 (0.01~0.05 Pa 범위에 가까운 것)
                best_match = min(conversions.items(), 
                               key=lambda x: abs(x[1]) if abs(x[1]) < 1 else float('inf'))
                print(f"✅ 가장 합리적인 변환: {best_match[0]} = {best_match[1]:.4f} Pa")
                
            else:
                print(f"❌ 측정 실패: {message}")
                result = {
                    'measurement': i + 1,
                    'timestamp': datetime.now().isoformat(),
                    'error': message,
                    'status': 'failed'
                }
                results.append(result)
            
            if i < count - 1:
                time.sleep(0.5)  # 0.5초 간격
        
        return results
    
    def summarize_results(self, results):
        """결과 요약"""
        print(f"\n📈 테스트 결과 요약")
        print("=" * 60)
        
        successful = [r for r in results if r['status'] == 'success']
        if not successful:
            print("❌ 성공한 측정이 없습니다")
            return
        
        print(f"✅ 성공률: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")
        
        # 각 스케일링 방법별 통계
        scaling_methods = ['60', '120', '240', '1']
        
        for method in scaling_methods:
            values = [r['conversions'][method] for r in successful]
            if values:
                avg = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                range_val = max_val - min_val
                
                print(f"\n📊 스케일링 {method}:")
                print(f"   평균: {avg:.4f} Pa")
                print(f"   범위: {min_val:.4f} ~ {max_val:.4f} Pa")
                print(f"   변동: {range_val:.4f} Pa")
                
                # 사용자 기대값(0.01~0.05 Pa)과 비교
                if 0.005 <= abs(avg) <= 0.1:  # 0.01~0.05 Pa 근처
                    print(f"   🎯 사용자 기대 범위(0.01~0.05 Pa)에 근접!")
    
    def cleanup(self):
        """리소스 정리"""
        try:
            # MUX 채널 비활성화
            self.bus.write_byte(self.TCA9548A_ADDRESS, 0x00)
            self.bus.close()
            print("🔧 리소스 정리 완료")
        except:
            pass

def main():
    """메인 테스트 실행"""
    print("🚀 SDP810 센서 직접 테스트 시작")
    print("=" * 60)
    
    tester = DirectSDP810Test()
    
    try:
        # 5회 연속 측정
        results = tester.test_multiple_readings(5)
        
        # 결과 요약
        tester.summarize_results(results)
        
        print(f"\n🎯 결론:")
        print("   1. 가장 합리적인 스케일링 팩터를 찾았나요?")
        print("   2. API 응답과 직접 측정값을 비교해보세요")
        print("   3. 센서 환경 조건을 확인해보세요 (온도, 기류 등)")
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자가 테스트를 중단했습니다")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()