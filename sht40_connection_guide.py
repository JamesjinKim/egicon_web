#!/usr/bin/env python3
"""
SHT40 연결 가이드 및 테스트
========================
Bus 1 Channel 1에 SHT40 센서 연결을 위한 가이드
"""

import sys
from datetime import datetime

def analyze_scan_results():
    """스캔 결과 분석"""
    
    print("=" * 70)
    print("📊 SHT40 센서 연결 상태 분석")
    print("=" * 70)
    
    print("🔍 현재 스캔 결과 분석:")
    print("   Bus 1 Channel 1: BME688 (0x77) 발견")
    print("   Bus 1 Channel 1: SHT40 (0x44, 0x45) 없음")
    print()
    
    print("⚠️ 문제 진단:")
    print("   1. SHT40 센서가 Channel 1에 연결되어 있지 않음")
    print("   2. 현재 Channel 1에는 BME688이 연결되어 있음")
    print("   3. SHT40는 다른 위치에 있거나 연결되지 않음")
    print()

def hardware_connection_guide():
    """하드웨어 연결 가이드"""
    
    print("🔧 SHT40 하드웨어 연결 가이드")
    print("=" * 50)
    
    print("📋 SHT40 센서 사양:")
    print("   - I2C 주소: 0x44 (기본) 또는 0x45")
    print("   - 전원: 3.3V")
    print("   - 통신: I2C (SCL, SDA)")
    print("   - 패키지: 4핀 (VCC, GND, SCL, SDA)")
    print()
    
    print("🔌 TCA9548A 연결 방법:")
    print("   1. TCA9548A 멀티플렉서 준비")
    print("   2. Bus 1에 연결된 TCA9548A 확인")
    print("   3. Channel 1 포트에 SHT40 연결:")
    print("      - VCC → 3.3V")
    print("      - GND → GND") 
    print("      - SCL → Channel 1 SCL")
    print("      - SDA → Channel 1 SDA")
    print()
    
    print("⚡ 전원 및 신호 확인:")
    print("   1. 3.3V 전원 공급 확인")
    print("   2. I2C 풀업 저항 (4.7kΩ) 연결 확인")
    print("   3. 케이블 연결 상태 점검")
    print("   4. 단락 또는 접촉 불량 확인")
    print()

def address_conflict_check():
    """주소 충돌 확인"""
    
    print("🚨 I2C 주소 충돌 분석")
    print("=" * 40)
    
    print("📍 현재 발견된 주소들:")
    print("   Bus 1 CH0: 0x77 (BME688)")
    print("   Bus 1 CH1: 0x77 (BME688) ← 여기에 SHT40 추가 예정")
    print("   Bus 1 CH2: 0x77 (BME688)")
    print("   Bus 1 CH4: 0x77 (BME688)")
    print("   Bus 1 CH5: 0x77 (BME688)")
    print("   Bus 1 CH6: 0x77 (BME688)")
    print("   Bus 1 CH7: 0x77 (BME688)")
    print()
    
    print("✅ 주소 충돌 상태:")
    print("   - SHT40 (0x44/0x45) vs BME688 (0x77): 충돌 없음")
    print("   - 같은 채널에서 동시 사용 가능")
    print("   - 멀티플렉서 채널 분리로 격리됨")
    print()
    
    print("🎯 권장 구성:")
    print("   Bus 1 CH1에 동시 연결 가능:")
    print("   - BME688 (0x77) - 온습도, 압력, 공기질")
    print("   - SHT40 (0x44) - 고정밀 온습도")
    print("   ※ 두 센서 모두 사용하여 데이터 비교 가능")
    print()

def connection_verification_steps():
    """연결 확인 단계"""
    
    print("🔍 SHT40 연결 확인 단계")
    print("=" * 45)
    
    print("1️⃣ 물리적 연결 확인:")
    print("   □ SHT40 센서 모듈 준비됨")
    print("   □ 4핀 케이블 연결 (VCC, GND, SCL, SDA)")
    print("   □ Bus 1 TCA9548A Channel 1에 연결됨")
    print("   □ 전원 LED 점등 확인 (있는 경우)")
    print()
    
    print("2️⃣ 전기적 연결 확인:")
    print("   □ 멀티미터로 3.3V 전원 측정")
    print("   □ SCL, SDA 라인 연속성 확인")
    print("   □ GND 연결 확인")
    print("   □ 풀업 저항 (4.7kΩ) 연결 확인")
    print()
    
    print("3️⃣ 소프트웨어 확인:")
    print("   □ 라즈베리파이에서 I2C 활성화")
    print("   □ TCA9548A 멀티플렉서 응답 확인")
    print("   □ Channel 1 선택 후 0x44/0x45 스캔")
    print("   □ SHT40 식별 및 통신 테스트")
    print()

def recommended_testing_sequence():
    """권장 테스트 순서"""
    
    print("🧪 권장 테스트 순서")
    print("=" * 35)
    
    print("Step 1: 하드웨어 점검")
    print("   python3 scan_all_channels.py")
    print("   → 전체 채널 스캔으로 현재 상태 확인")
    print()
    
    print("Step 2: SHT40 연결 후 재스캔")
    print("   python3 scan_all_channels.py")
    print("   → Bus 1 CH1에서 0x44 또는 0x45 확인")
    print()
    
    print("Step 3: SHT40 전용 테스트")
    print("   python3 test_sht40_ch1.py")
    print("   → SHT40 센서 기능 테스트")
    print()
    
    print("Step 4: 웹 대시보드 확인")
    print("   1. 대시보드 새로고침")
    print("   2. SHT40 센서 그룹 확인")
    print("   3. 실시간 데이터 수신 확인")
    print()

def troubleshooting_guide():
    """문제 해결 가이드"""
    
    print("🛠️ 문제 해결 가이드")
    print("=" * 35)
    
    print("❌ 문제: SHT40가 스캔되지 않음")
    print("🔧 해결 방법:")
    print("   1. 전원 확인: 3.3V (NOT 5V!)")
    print("   2. 연결 확인: SCL, SDA 올바른 핀에 연결")
    print("   3. 주소 확인: ADDR 핀 상태 (0x44/0x45)")
    print("   4. 케이블 확인: 단선이나 접촉 불량")
    print("   5. 풀업 확인: SCL, SDA에 4.7kΩ 저항")
    print()
    
    print("❌ 문제: 주소 충돌")
    print("🔧 해결 방법:")
    print("   1. SHT40는 0x44/0x45만 사용")
    print("   2. BME688는 0x76/0x77만 사용")
    print("   3. 동일 채널에서 동시 사용 가능")
    print("   4. ADDR 핀으로 주소 변경 가능")
    print()
    
    print("❌ 문제: 통신 오류")
    print("🔧 해결 방법:")
    print("   1. I2C 속도 낮추기 (100kHz)")
    print("   2. 케이블 길이 줄이기 (<30cm)")
    print("   3. 노이즈 차폐 확인")
    print("   4. 다른 채널에서 테스트")
    print()

if __name__ == "__main__":
    print("🚀 SHT40 연결 가이드")
    print(f"⏰ 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    analyze_scan_results()
    hardware_connection_guide()
    address_conflict_check()
    connection_verification_steps()
    recommended_testing_sequence()
    troubleshooting_guide()
    
    print("=" * 70)
    print("📝 요약")
    print("=" * 70)
    print("현재 상태: Bus 1 CH1에 BME688(0x77)만 있음")
    print("필요 작업: SHT40(0x44)를 CH1에 추가 연결")
    print("예상 결과: BME688 + SHT40 동시 사용 가능")
    print("다음 단계: 물리적 연결 후 재스캔")
    print("=" * 70)