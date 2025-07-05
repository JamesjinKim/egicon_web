#!/usr/bin/env python3
"""
SPS30 UART 센서 진단 스크립트
============================
SPS30 센서 감지 문제를 진단하기 위한 독립 테스트 스크립트
"""

import glob
import os
import sys

def check_system_environment():
    """시스템 환경 확인"""
    print("🔍 시스템 환경 진단")
    print(f"  - Python 버전: {sys.version}")
    print(f"  - 운영체제: {os.uname().sysname} {os.uname().release}")
    print(f"  - 아키텍처: {os.uname().machine}")
    
    # 라즈베리파이 확인
    try:
        with open('/proc/cpuinfo', 'r') as f:
            content = f.read()
            if 'Raspberry Pi' in content or 'BCM' in content:
                print("  ✅ 라즈베리파이 환경 확인됨")
                return True
    except:
        pass
    
    print("  ❌ 라즈베리파이가 아닌 환경")
    return False

def check_sps30_library():
    """SPS30 라이브러리 설치 확인"""
    print("\n📚 SPS30 라이브러리 확인")
    
    try:
        import shdlc_sps30
        print("  ✅ shdlc_sps30 설치됨")
        print(f"     버전: {getattr(shdlc_sps30, '__version__', 'Unknown')}")
    except ImportError as e:
        print(f"  ❌ shdlc_sps30 설치 안됨: {e}")
        print("     설치 명령: pip install sensirion-shdlc-sps30")
        return False
    
    try:
        from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
        print("  ✅ sensirion_shdlc_driver 설치됨")
    except ImportError as e:
        print(f"  ❌ sensirion_shdlc_driver 설치 안됨: {e}")
        return False
    
    return True

def check_serial_ports():
    """시리얼 포트 확인"""
    print("\n🔌 시리얼 포트 검색")
    
    usb_ports = glob.glob('/dev/ttyUSB*')
    acm_ports = glob.glob('/dev/ttyACM*') 
    ama_ports = glob.glob('/dev/ttyAMA*')
    
    print(f"  📋 USB 포트: {usb_ports}")
    print(f"  📋 ACM 포트: {acm_ports}")
    print(f"  📋 AMA 포트: {ama_ports}")
    
    all_ports = usb_ports + acm_ports + ama_ports
    
    if not all_ports:
        print("  ❌ 시리얼 포트를 찾을 수 없습니다")
        print("     확인사항:")
        print("     1. SPS30이 USB로 연결되었는지 확인")
        print("     2. USB 케이블 상태 확인")
        print("     3. 'lsusb' 명령으로 USB 장치 확인")
        return []
    
    # 포트 권한 확인
    accessible_ports = []
    for port in all_ports:
        if os.access(port, os.R_OK | os.W_OK):
            print(f"  ✅ {port} - 접근 가능")
            accessible_ports.append(port)
        else:
            print(f"  ❌ {port} - 권한 없음")
            print(f"     해결방법: sudo usermod -a -G dialout $USER")
    
    return accessible_ports

def test_sps30_on_ports(ports):
    """포트별 SPS30 테스트"""
    print(f"\n🧪 SPS30 센서 테스트 ({len(ports)}개 포트)")
    
    if not ports:
        print("  ❌ 테스트할 포트가 없습니다")
        return False
    
    try:
        from shdlc_sps30 import Sps30ShdlcDevice
        from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
    except ImportError:
        print("  ❌ SPS30 라이브러리가 없어 테스트 불가")
        return False
    
    for port_path in ports:
        print(f"\n  🔌 포트 테스트: {port_path}")
        
        try:
            print(f"     - 포트 열기 시도...")
            with ShdlcSerialPort(port=port_path, baudrate=115200) as port:
                print(f"     - 포트 열기 성공")
                
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                print(f"     - SPS30 장치 생성 완료")
                
                print(f"     - 시리얼 번호 읽기 시도...")
                serial_number = device.device_information_serial_number()
                
                if serial_number:
                    print(f"     ✅ SPS30 센서 발견!")
                    print(f"        포트: {port_path}")
                    print(f"        시리얼 번호: {serial_number}")
                    
                    # 추가 정보 읽기 시도
                    try:
                        print(f"     - 제품 타입 읽기 시도...")
                        product_type = device.device_information_product_type()
                        print(f"        제품 타입: {product_type}")
                    except Exception as e:
                        print(f"        제품 타입 읽기 실패: {e}")
                    
                    return True
                else:
                    print(f"     ❌ 시리얼 번호 읽기 실패")
                    
        except Exception as e:
            print(f"     ❌ 테스트 실패: {type(e).__name__}: {e}")
            continue
    
    return False

def check_user_groups():
    """사용자 그룹 확인"""
    print("\n👤 사용자 권한 확인")
    
    import subprocess
    try:
        result = subprocess.run(['groups'], capture_output=True, text=True)
        groups = result.stdout.strip()
        print(f"  현재 사용자 그룹: {groups}")
        
        if 'dialout' in groups:
            print("  ✅ dialout 그룹에 속해있음")
            return True
        else:
            print("  ❌ dialout 그룹에 속해있지 않음")
            print("     해결방법:")
            print("     1. sudo usermod -a -G dialout $USER")
            print("     2. 로그아웃 후 다시 로그인")
            return False
    except Exception as e:
        print(f"  ❌ 그룹 확인 실패: {e}")
        return False

def main():
    """메인 진단 함수"""
    print("🔧 SPS30 UART 센서 진단 시작")
    print("=" * 50)
    
    # 1. 시스템 환경 확인
    is_rpi = check_system_environment()
    
    # 2. 라이브러리 설치 확인
    lib_ok = check_sps30_library()
    
    # 3. 사용자 권한 확인
    groups_ok = check_user_groups()
    
    # 4. 시리얼 포트 확인
    accessible_ports = check_serial_ports()
    
    # 5. SPS30 테스트 (라이브러리가 있는 경우만)
    sensor_found = False
    if lib_ok and accessible_ports:
        sensor_found = test_sps30_on_ports(accessible_ports)
    
    # 진단 결과 요약
    print("\n" + "=" * 50)
    print("📋 진단 결과 요약")
    print(f"  라즈베리파이 환경: {'✅' if is_rpi else '❌'}")
    print(f"  SPS30 라이브러리: {'✅' if lib_ok else '❌'}")
    print(f"  사용자 권한: {'✅' if groups_ok else '❌'}")
    print(f"  접근 가능한 포트: {len(accessible_ports)}개")
    print(f"  SPS30 센서 감지: {'✅' if sensor_found else '❌'}")
    
    if sensor_found:
        print("\n🎉 SPS30 센서가 정상적으로 감지되었습니다!")
    else:
        print("\n❌ SPS30 센서를 찾을 수 없습니다")
        print("   다음 단계를 확인해보세요:")
        if not is_rpi:
            print("   1. 라즈베리파이 환경에서 실행하세요")
        if not lib_ok:
            print("   2. pip install sensirion-shdlc-sps30")
        if not groups_ok:
            print("   3. sudo usermod -a -G dialout $USER 실행 후 재로그인")
        if not accessible_ports:
            print("   4. SPS30 USB 연결 상태 확인")
        print("   5. 라즈베리파이 재부팅 후 재시도")

if __name__ == "__main__":
    main()