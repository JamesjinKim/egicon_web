#!/usr/bin/env python3
"""
SHT40 채널 0 정밀 진단 프로그램
============================
Bus 1, 채널 0에서 CRC 검증 실패하는 SHT40 센서의 상세 분석
타이밍, 전원, 명령어 등 다양한 조건으로 테스트
"""

import sys
import time
import smbus2

def calculate_crc(data):
    """CRC-8 체크섬 계산 (SHT40용)"""
    CRC = 0xFF
    for byte in data:
        CRC ^= byte
        for _ in range(8):
            if CRC & 0x80:
                CRC = (CRC << 1) ^ 0x31
            else:
                CRC = (CRC << 1) & 0xFF
    return CRC

def test_sht40_with_various_timings():
    """다양한 타이밍으로 SHT40 테스트"""
    print("🔍 SHT40 채널 0 타이밍 분석 테스트")
    print("=" * 60)
    
    bus_num = 1
    tca_address = 0x70
    channel = 0
    sht40_address = 0x44
    
    # 다양한 타이밍 조합
    timing_configs = [
        {"name": "빠른 타이밍", "reset_delay": 0.1, "measure_delay": 0.02, "channel_delay": 0.05},
        {"name": "표준 타이밍", "reset_delay": 0.2, "measure_delay": 0.5, "channel_delay": 0.1},
        {"name": "느린 타이밍", "reset_delay": 0.5, "measure_delay": 1.0, "channel_delay": 0.2},
        {"name": "매우 느린 타이밍", "reset_delay": 1.0, "measure_delay": 2.0, "channel_delay": 0.5},
    ]
    
    # 다양한 명령어
    commands = [
        {"name": "High Precision", "cmd": 0xFD, "expected_delay": 0.015},
        {"name": "Medium Precision", "cmd": 0xF6, "expected_delay": 0.005},
        {"name": "Low Precision", "cmd": 0xE0, "expected_delay": 0.002},
    ]
    
    try:
        bus = smbus2.SMBus(bus_num)
        
        for timing in timing_configs:
            print(f"\\n🧪 === {timing['name']} 테스트 ===")
            
            for cmd_info in commands:
                print(f"\\n  📍 {cmd_info['name']} 명령어 (0x{cmd_info['cmd']:02x})")
                
                try:
                    # 채널 선택
                    channel_mask = 1 << channel
                    bus.write_byte(tca_address, channel_mask)
                    time.sleep(timing['channel_delay'])
                    print(f"    ✅ 채널 {channel} 선택 (대기: {timing['channel_delay']}초)")
                    
                    # 소프트 리셋
                    reset_msg = smbus2.i2c_msg.write(sht40_address, [0x94])
                    bus.i2c_rdwr(reset_msg)
                    time.sleep(timing['reset_delay'])
                    print(f"    ✅ 소프트 리셋 (대기: {timing['reset_delay']}초)")
                    
                    # 측정 명령 전송
                    measure_msg = smbus2.i2c_msg.write(sht40_address, [cmd_info['cmd']])
                    bus.i2c_rdwr(measure_msg)
                    
                    # 명령어별 권장 대기시간 + 추가 타이밍
                    total_delay = cmd_info['expected_delay'] + timing['measure_delay']
                    time.sleep(total_delay)
                    print(f"    ✅ 측정 명령 (대기: {total_delay:.3f}초)")
                    
                    # 데이터 읽기
                    read_msg = smbus2.i2c_msg.read(sht40_address, 6)
                    bus.i2c_rdwr(read_msg)
                    data = list(read_msg)
                    
                    print(f"    📊 원시 데이터: {[f'0x{x:02x}' for x in data]}")
                    
                    # 상세 CRC 분석
                    t_data = data[0:2]
                    t_crc_received = data[2]
                    t_crc_calculated = calculate_crc(t_data)
                    
                    rh_data = data[3:5]
                    rh_crc_received = data[5]
                    rh_crc_calculated = calculate_crc(rh_data)
                    
                    print(f"    🔐 온도 CRC: 수신=0x{t_crc_received:02x}, 계산=0x{t_crc_calculated:02x}, 일치={t_crc_received == t_crc_calculated}")
                    print(f"    🔐 습도 CRC: 수신=0x{rh_crc_received:02x}, 계산=0x{rh_crc_calculated:02x}, 일치={rh_crc_received == rh_crc_calculated}")
                    
                    if t_crc_received == t_crc_calculated and rh_crc_received == rh_crc_calculated:
                        # 온습도 계산
                        t_raw = (t_data[0] << 8) | t_data[1]
                        rh_raw = (rh_data[0] << 8) | rh_data[1]
                        temperature = -45 + 175 * (t_raw / 65535.0)
                        humidity = max(0, min(100, -6 + 125 * (rh_raw / 65535.0)))
                        
                        print(f"    🎉 측정 성공: 온도={temperature:.2f}°C, 습도={humidity:.2f}%RH")
                        
                        # 성공한 설정 저장
                        success_config = {
                            "timing": timing,
                            "command": cmd_info,
                            "temperature": temperature,
                            "humidity": humidity
                        }
                        
                        # 연속 테스트로 안정성 확인
                        print(f"    🔄 안정성 확인을 위한 연속 3회 테스트...")
                        stable_count = 0
                        for test_num in range(3):
                            try:
                                # 같은 설정으로 재측정
                                bus.write_byte(tca_address, channel_mask)
                                time.sleep(timing['channel_delay'])
                                
                                measure_msg = smbus2.i2c_msg.write(sht40_address, [cmd_info['cmd']])
                                bus.i2c_rdwr(measure_msg)
                                time.sleep(total_delay)
                                
                                read_msg = smbus2.i2c_msg.read(sht40_address, 6)
                                bus.i2c_rdwr(read_msg)
                                test_data = list(read_msg)
                                
                                test_t_crc_ok = calculate_crc(test_data[0:2]) == test_data[2]
                                test_rh_crc_ok = calculate_crc(test_data[3:5]) == test_data[5]
                                
                                if test_t_crc_ok and test_rh_crc_ok:
                                    stable_count += 1
                                    print(f"      ✅ 테스트 {test_num + 1}: 성공")
                                else:
                                    print(f"      ❌ 테스트 {test_num + 1}: CRC 실패")
                                
                                time.sleep(0.5)
                                
                            except Exception as e:
                                print(f"      ❌ 테스트 {test_num + 1}: 통신 실패 - {e}")
                        
                        stability = (stable_count / 3) * 100
                        print(f"    📊 안정성: {stability:.1f}% ({stable_count}/3)")
                        
                        if stability >= 66:  # 2/3 이상 성공
                            print(f"    🎯 안정적인 설정 발견!")
                            print(f"       타이밍: {timing['name']}")
                            print(f"       명령어: {cmd_info['name']}")
                            print(f"       채널 대기: {timing['channel_delay']}초")
                            print(f"       리셋 대기: {timing['reset_delay']}초") 
                            print(f"       측정 대기: {total_delay:.3f}초")
                            
                            bus.write_byte(tca_address, 0x00)
                            bus.close()
                            return success_config
                    else:
                        print(f"    ❌ CRC 검증 실패")
                        
                        # CRC 오류 패턴 분석
                        if all(x == 0x00 for x in data):
                            print(f"    🔍 패턴 분석: 모든 데이터가 0x00 (센서 미응답)")
                        elif all(x == 0xFF for x in data):
                            print(f"    🔍 패턴 분석: 모든 데이터가 0xFF (버스 풀업 문제)")
                        else:
                            print(f"    🔍 패턴 분석: 부분적 데이터 수신 (타이밍 문제 가능성)")
                    
                    # 채널 비활성화
                    bus.write_byte(tca_address, 0x00)
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"    ❌ 테스트 실패: {e}")
                    try:
                        bus.write_byte(tca_address, 0x00)
                    except:
                        pass
        
        bus.close()
        print(f"\\n❌ 모든 설정에서 안정적인 통신 실패")
        return None
        
    except Exception as e:
        print(f"❌ 테스트 초기화 실패: {e}")
        return None

def test_power_and_signal_quality():
    """전원 및 신호 품질 테스트"""
    print("\\n🔋 전원 및 신호 품질 진단")
    print("=" * 40)
    
    bus_num = 1
    tca_address = 0x70
    
    try:
        bus = smbus2.SMBus(bus_num)
        
        # TCA9548A 상태 확인
        print("📡 TCA9548A 상태 확인:")
        for i in range(5):
            try:
                bus.write_byte(tca_address, 0x00)
                status = bus.read_byte(tca_address)
                print(f"  시도 {i+1}: 0x{status:02x} {'✅' if status == 0x00 else '⚠️'}")
                time.sleep(0.1)
            except Exception as e:
                print(f"  시도 {i+1}: 실패 - {e}")
        
        # 채널 전환 안정성 테스트
        print("\\n🔄 채널 전환 안정성:")
        for channel in range(8):
            try:
                channel_mask = 1 << channel
                bus.write_byte(tca_address, channel_mask)
                time.sleep(0.1)
                selected = bus.read_byte(tca_address)
                
                if selected == channel_mask:
                    print(f"  채널 {channel}: ✅ 정상")
                else:
                    print(f"  채널 {channel}: ⚠️ 불안정 (예상: 0x{channel_mask:02x}, 실제: 0x{selected:02x})")
            except Exception as e:
                print(f"  채널 {channel}: ❌ 실패 - {e}")
        
        bus.write_byte(tca_address, 0x00)
        bus.close()
        
    except Exception as e:
        print(f"❌ 진단 실패: {e}")

def main():
    """메인 실행 함수"""
    print("🔬 SHT40 채널 0 정밀 진단 프로그램")
    print("=" * 60)
    print("목적: Bus 1, 채널 0에서 CRC 검증 실패하는 원인 분석")
    print("=" * 60)
    
    # 전원 및 신호 품질 진단
    test_power_and_signal_quality()
    
    # 다양한 타이밍으로 테스트
    success_config = test_sht40_with_various_timings()
    
    print("\\n" + "="*60)
    print("🎯 진단 결과")
    print("="*60)
    
    if success_config:
        print("✅ 안정적인 통신 설정 발견!")
        print("\\n📋 권장 설정:")
        timing = success_config['timing']
        command = success_config['command']
        
        print(f"  - 명령어: {command['name']} (0x{command['cmd']:02x})")
        print(f"  - 채널 전환 대기: {timing['channel_delay']}초")
        print(f"  - 리셋 대기: {timing['reset_delay']}초")
        print(f"  - 측정 대기: {command['expected_delay'] + timing['measure_delay']:.3f}초")
        
        print(f"\\n🌡️ 측정값:")
        print(f"  - 온도: {success_config['temperature']:.2f}°C")
        print(f"  - 습도: {success_config['humidity']:.2f}%RH")
        
        print("\\n💡 다음 단계:")
        print("  1. 이 설정을 sht40_sensor.py에 적용")
        print("  2. hardware_scanner.py에서 Bus 1, 채널 0 사용하도록 수정")
        print("  3. 웹 대시보드에서 실시간 데이터 확인")
        
    else:
        print("❌ 안정적인 통신 설정을 찾지 못함")
        print("\\n🔧 추가 확인사항:")
        print("  1. SHT40 센서 하드웨어 불량 가능성")
        print("  2. 전원 공급 전압 확인 (3.3V)")
        print("  3. I2C 풀업 저항 확인 (4.7kΩ)")
        print("  4. 케이블 연결 및 접촉 불량 확인")
        print("  5. TCA9548A와 SHT40 간 신호 간섭 확인")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\\n⏹️ 사용자에 의해 진단 중단됨")
    except Exception as e:
        print(f"\\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)