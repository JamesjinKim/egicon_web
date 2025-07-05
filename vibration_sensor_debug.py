#!/usr/bin/env python3
"""
LIS3DH 진동센서 SPI 디버그 스크립트
==================================
SPI 연결 문제 진단 및 해결
"""

import time
import spidev
import sys

class LIS3DH_Debug:
    """LIS3DH SPI 디버그 클래스"""
    
    WHO_AM_I = 0x0F
    DEVICE_ID = 0x33
    
    def __init__(self):
        self.spi = None
    
    def test_spi_device(self, bus: int, device: int):
        """특정 SPI 디바이스 테스트"""
        print(f"\n🔧 SPI {bus}.{device} 테스트 중...")
        
        try:
            if self.spi:
                self.spi.close()
            
            self.spi = spidev.SpiDev()
            self.spi.open(bus, device)
            
            # 다양한 SPI 설정 시도
            spi_configs = [
                {"speed": 500000, "mode": 0b00, "name": "500kHz, Mode 0"},
                {"speed": 1000000, "mode": 0b00, "name": "1MHz, Mode 0"},
                {"speed": 500000, "mode": 0b11, "name": "500kHz, Mode 3"},
                {"speed": 100000, "mode": 0b00, "name": "100kHz, Mode 0"},
            ]
            
            for config in spi_configs:
                print(f"  📡 {config['name']} 시도...")
                
                self.spi.max_speed_hz = config["speed"]
                self.spi.mode = config["mode"]
                
                time.sleep(0.1)
                
                # WHO_AM_I 레지스터 읽기 시도
                device_id = self._read_who_am_i()
                
                print(f"    응답: 0x{device_id:02X}", end="")
                
                if device_id == self.DEVICE_ID:
                    print(" ✅ 성공!")
                    return True, config
                elif device_id == 0xFF:
                    print(" ❌ 연결 없음")
                elif device_id == 0x00:
                    print(" ❌ 단락 가능성")
                else:
                    print(f" ❌ 다른 디바이스 (예상: 0x{self.DEVICE_ID:02X})")
            
            return False, None
            
        except Exception as e:
            print(f"    ❌ SPI 오류: {e}")
            return False, None
        
        finally:
            if self.spi:
                try:
                    self.spi.close()
                except:
                    pass
    
    def _read_who_am_i(self):
        """WHO_AM_I 레지스터 읽기"""
        try:
            # 읽기 명령: MSB=1
            cmd = [0x80 | self.WHO_AM_I, 0x00]
            result = self.spi.xfer2(cmd)
            return result[1]
        except:
            return 0xFF
    
    def test_manual_pins(self):
        """GPIO를 통한 수동 핀 테스트"""
        print(f"\n🔧 GPIO 핀 수동 테스트")
        
        try:
            import RPi.GPIO as GPIO
            
            # SPI 핀 정의
            pins = {
                "CS0": 8,   # CE0
                "CS1": 7,   # CE1  
                "MOSI": 10, # MOSI
                "MISO": 9,  # MISO
                "SCLK": 11  # SCLK
            }
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            print("  📌 SPI 핀 상태:")
            for name, pin in pins.items():
                try:
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    state = GPIO.input(pin)
                    print(f"    {name} (GPIO {pin}): {'HIGH' if state else 'LOW'}")
                except Exception as e:
                    print(f"    {name} (GPIO {pin}): 오류 - {e}")
            
            GPIO.cleanup()
            
        except ImportError:
            print("  ❌ RPi.GPIO 라이브러리가 설치되지 않음")
        except Exception as e:
            print(f"  ❌ GPIO 테스트 실패: {e}")
    
    def check_system_info(self):
        """시스템 정보 확인"""
        print(f"\n🔧 시스템 정보 확인")
        
        try:
            # SPI 디바이스 트리 확인
            import os
            
            print("  📂 SPI 디바이스:")
            for f in os.listdir("/dev"):
                if f.startswith("spidev"):
                    print(f"    /dev/{f}")
            
            # 커널 모듈 확인
            print("  🔌 SPI 커널 모듈:")
            try:
                with open("/proc/modules", "r") as f:
                    modules = f.read()
                    spi_modules = ["spi_bcm2835", "spidev"]
                    for module in spi_modules:
                        if module in modules:
                            print(f"    ✅ {module} 로드됨")
                        else:
                            print(f"    ❌ {module} 로드 안됨")
            except:
                print("    ❌ 모듈 확인 실패")
            
            # 디바이스 트리 확인
            print("  🌳 디바이스 트리:")
            try:
                with open("/boot/config.txt", "r") as f:
                    config = f.read()
                    if "dtparam=spi=on" in config:
                        print("    ✅ SPI 활성화됨")
                    else:
                        print("    ❌ SPI 비활성화됨")
            except:
                print("    ❌ config.txt 확인 실패")
                
        except Exception as e:
            print(f"  ❌ 시스템 정보 확인 실패: {e}")

def main():
    """메인 디버그 함수"""
    print("🔧 LIS3DH SPI 연결 디버그")
    print("=" * 50)
    
    debug = LIS3DH_Debug()
    
    # 시스템 정보 확인
    debug.check_system_info()
    
    # GPIO 핀 테스트
    debug.test_manual_pins()
    
    # 각 SPI 디바이스 테스트
    found = False
    working_config = None
    
    for bus in [0]:  # 라즈베리파이는 보통 SPI 버스 0만 사용
        for device in [0, 1]:
            success, config = debug.test_spi_device(bus, device)
            if success:
                found = True
                working_config = config
                print(f"\n✅ 성공! SPI {bus}.{device}에서 LIS3DH 발견")
                print(f"   최적 설정: {config['name']}")
                break
        if found:
            break
    
    if not found:
        print(f"\n❌ 모든 SPI 디바이스에서 LIS3DH를 찾을 수 없습니다")
        print(f"\n🔧 해결 방법:")
        print(f"1. 하드웨어 연결 확인:")
        print(f"   - CS (Chip Select): GPIO 8 (Pin 24) 또는 GPIO 7 (Pin 26)")
        print(f"   - MOSI: GPIO 10 (Pin 19)")
        print(f"   - MISO: GPIO 9 (Pin 21)")
        print(f"   - SCLK: GPIO 11 (Pin 23)")
        print(f"   - VCC: 3.3V (Pin 1 또는 17)")
        print(f"   - GND: Ground (Pin 6, 9, 14, 20, 25, 30, 34, 39)")
        print(f"")
        print(f"2. SPI 활성화 확인:")
        print(f"   sudo raspi-config → Interface Options → SPI → Enable")
        print(f"")
        print(f"3. 재부팅 후 다시 시도:")
        print(f"   sudo reboot")
        print(f"")
        print(f"4. 다른 센서일 가능성:")
        print(f"   - MPU6050 (I2C): WHO_AM_I = 0x68")
        print(f"   - LSM6DS3 (I2C/SPI): WHO_AM_I = 0x69")
        print(f"   - ADXL345 (I2C/SPI): WHO_AM_I = 0xE5")
    else:
        print(f"\n🎉 테스트 완료! 다음 설정으로 진동센서를 사용하세요:")
        print(f"   spi_bus=0, spi_device={'0 또는 1'}")
        print(f"   speed={working_config['speed']}Hz, mode={working_config['mode']}")

if __name__ == "__main__":
    main()