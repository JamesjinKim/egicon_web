#!/usr/bin/env python3
"""
LIS3DH 진동센서 SPI 테스트 스크립트
=================================
STMicroelectronics LIS3DH 3축 가속도계를 이용한 진동 감지 (SPI 통신)
SPI 설정: CS0 (GPIO 8), MOSI (GPIO 10), MISO (GPIO 9), SCLK (GPIO 11)
"""

import time
import spidev
import math
from typing import Optional, Tuple

class LIS3DH_SPI:
    """LIS3DH 3축 가속도계 SPI 클래스"""
    
    # 레지스터 주소 (SPI 읽기: MSB=1, 쓰기: MSB=0)
    WHO_AM_I = 0x0F
    CTRL_REG1 = 0x20
    CTRL_REG2 = 0x21
    CTRL_REG3 = 0x22
    CTRL_REG4 = 0x23
    CTRL_REG5 = 0x24
    CTRL_REG6 = 0x25
    
    STATUS_REG = 0x27
    OUT_X_L = 0x28
    OUT_X_H = 0x29
    OUT_Y_L = 0x2A
    OUT_Y_H = 0x2B
    OUT_Z_L = 0x2C
    OUT_Z_H = 0x2D
    
    # WHO_AM_I 응답값
    DEVICE_ID = 0x33
    
    def __init__(self, spi_bus: int = 0, spi_device: int = 0):
        """
        LIS3DH SPI 초기화
        
        Args:
            spi_bus: SPI 버스 번호 (일반적으로 0)
            spi_device: SPI 디바이스 번호 (CS0=0, CS1=1)
        """
        self.spi = spidev.SpiDev()
        self.spi_bus = spi_bus
        self.spi_device = spi_device
        
        try:
            # SPI 연결
            self.spi.open(spi_bus, spi_device)
            
            # SPI 설정
            self.spi.max_speed_hz = 1000000  # 1MHz
            self.spi.mode = 0b00  # CPOL=0, CPHA=0
            
            print(f"🔧 SPI 연결 성공: 버스 {spi_bus}, 디바이스 {spi_device}")
            
            # 센서 확인 및 초기화
            self._check_sensor()
            self._initialize()
            
        except Exception as e:
            raise Exception(f"SPI 초기화 실패: {e}")
    
    def _spi_read_register(self, register: int) -> int:
        """SPI로 단일 레지스터 읽기"""
        # 읽기 명령: MSB=1, 다중바이트=0
        cmd = [0x80 | register, 0x00]
        result = self.spi.xfer2(cmd)
        return result[1]
    
    def _spi_write_register(self, register: int, value: int):
        """SPI로 단일 레지스터 쓰기"""
        # 쓰기 명령: MSB=0
        cmd = [register & 0x7F, value]
        self.spi.xfer2(cmd)
    
    def _spi_read_multiple(self, register: int, length: int) -> list:
        """SPI로 다중 레지스터 읽기"""
        # 읽기 명령: MSB=1, 다중바이트=1
        cmd = [0x80 | 0x40 | register] + [0x00] * length
        result = self.spi.xfer2(cmd)
        return result[1:]
    
    def _check_sensor(self):
        """센서 연결 및 식별 확인"""
        try:
            device_id = self._spi_read_register(self.WHO_AM_I)
            
            if device_id == self.DEVICE_ID:
                print(f"✅ LIS3DH 센서 확인됨 (Device ID: 0x{device_id:02X})")
            else:
                raise Exception(f"잘못된 디바이스 ID: 0x{device_id:02X} (예상: 0x{self.DEVICE_ID:02X})")
                
        except Exception as e:
            raise Exception(f"센서 확인 실패: {e}")
    
    def _initialize(self):
        """센서 초기화 및 설정"""
        try:
            # CTRL_REG1: 정상 모드, 100Hz, 모든 축 활성화 (0x57)
            # ODR[3:0]=0101 (100Hz), LPen=0, Zen=Yen=Xen=1
            self._spi_write_register(self.CTRL_REG1, 0x57)
            
            # CTRL_REG4: ±2g 범위, 고해상도 모드 (0x08)
            # BDU=0, BLE=0, FS[1:0]=00 (±2g), HR=1, ST[1:0]=00, SIM=0
            self._spi_write_register(self.CTRL_REG4, 0x08)
            
            time.sleep(0.1)  # 초기화 대기
            
            # 설정 확인
            ctrl1 = self._spi_read_register(self.CTRL_REG1)
            ctrl4 = self._spi_read_register(self.CTRL_REG4)
            
            print(f"✅ LIS3DH 초기화 완료")
            print(f"   CTRL_REG1: 0x{ctrl1:02X} (100Hz, 모든축 활성)")
            print(f"   CTRL_REG4: 0x{ctrl4:02X} (±2g, 고해상도)")
            
        except Exception as e:
            raise Exception(f"LIS3DH 초기화 실패: {e}")
    
    def read_raw_data(self) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """원시 가속도 데이터 읽기 (12비트)"""
        try:
            # 상태 레지스터 확인
            status = self._spi_read_register(self.STATUS_REG)
            if not (status & 0x08):  # ZYXDA 비트 확인
                return None, None, None
            
            # 6바이트 연속 읽기 (X, Y, Z 각각 2바이트)
            data = self._spi_read_multiple(self.OUT_X_L, 6)
            
            # 12비트 데이터 변환 (상위 4비트 무시)
            x_raw = (data[1] << 8 | data[0]) >> 4
            y_raw = (data[3] << 8 | data[2]) >> 4
            z_raw = (data[5] << 8 | data[4]) >> 4
            
            # 2의 보수 변환 (12비트)
            if x_raw > 2047: x_raw -= 4096
            if y_raw > 2047: y_raw -= 4096
            if z_raw > 2047: z_raw -= 4096
            
            return x_raw, y_raw, z_raw
            
        except Exception as e:
            print(f"❌ 데이터 읽기 실패: {e}")
            return None, None, None
    
    def read_acceleration(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """가속도 데이터 읽기 (g 단위)"""
        x_raw, y_raw, z_raw = self.read_raw_data()
        
        if x_raw is None:
            return None, None, None
        
        # ±2g 범위에서 12비트 해상도: 1 LSB = 4mg
        scale = 4.0 / 1000.0  # mg를 g로 변환
        
        x_g = x_raw * scale
        y_g = y_raw * scale
        z_g = z_raw * scale
        
        return x_g, y_g, z_g
    
    def calculate_vibration_magnitude(self) -> Optional[float]:
        """진동 강도 계산 (벡터 크기)"""
        x, y, z = self.read_acceleration()
        
        if x is None:
            return None
        
        # 중력 제거 (Z축에서 1g 제거)
        z_no_gravity = z - 1.0
        
        # 진동 벡터 크기 계산
        magnitude = math.sqrt(x**2 + y**2 + z_no_gravity**2)
        
        return magnitude
    
    def close(self):
        """SPI 연결 종료"""
        if self.spi:
            self.spi.close()

def test_spi_connection():
    """SPI 연결 테스트"""
    print("🔧 SPI 연결 테스트")
    print("=" * 40)
    
    try:
        # SPI 디바이스 확인
        import os
        spi_devices = []
        
        for bus in [0, 1]:
            for device in [0, 1]:
                spi_path = f"/dev/spidev{bus}.{device}"
                if os.path.exists(spi_path):
                    spi_devices.append((bus, device))
                    print(f"✅ SPI 디바이스 발견: {spi_path}")
        
        if not spi_devices:
            print("❌ SPI 디바이스를 찾을 수 없습니다")
            print("💡 해결 방법: sudo raspi-config에서 SPI 활성화")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ SPI 테스트 실패: {e}")
        return False

def test_vibration_sensor():
    """진동센서 테스트 메인 함수"""
    print("🔧 LIS3DH 진동센서 SPI 테스트 시작")
    print("=" * 50)
    
    # SPI 연결 테스트
    if not test_spi_connection():
        return
    
    sensor = None
    try:
        # LIS3DH 센서 초기화 (기본적으로 SPI0.0 사용)
        sensor = LIS3DH_SPI(spi_bus=0, spi_device=0)
        
        print(f"\n📊 진동 데이터 모니터링 시작...")
        print("Ctrl+C로 종료")
        print("-" * 70)
        print(f"{'Time':<8} {'X(g)':<8} {'Y(g)':<8} {'Z(g)':<8} {'Magnitude':<10} {'Status':<10}")
        print("-" * 70)
        
        # 기준 진동값 측정 (처음 50회 평균)
        print("📏 기준값 측정 중... (5초)")
        baseline_samples = []
        for i in range(50):
            mag = sensor.calculate_vibration_magnitude()
            if mag is not None:
                baseline_samples.append(mag)
            time.sleep(0.1)
        
        if not baseline_samples:
            print("❌ 기준값 측정 실패")
            return
        
        baseline = sum(baseline_samples) / len(baseline_samples)
        threshold = baseline + 0.1  # 기준값 + 0.1g를 진동 임계값으로 설정
        
        print(f"📏 기준 진동값: {baseline:.3f}g, 임계값: {threshold:.3f}g")
        print("-" * 70)
        
        vibration_count = 0
        sample_count = 0
        max_vibration = 0
        
        while True:
            x, y, z = sensor.read_acceleration()
            magnitude = sensor.calculate_vibration_magnitude()
            
            if x is not None and magnitude is not None:
                sample_count += 1
                current_time = time.strftime("%H:%M:%S")
                
                # 최대 진동값 업데이트
                if magnitude > max_vibration:
                    max_vibration = magnitude
                
                # 진동 감지
                vibration_detected = magnitude > threshold
                if vibration_detected:
                    vibration_count += 1
                    status = "🔴 진동!"
                else:
                    status = "🟢 정상"
                
                print(f"{current_time} {x:+6.3f} {y:+6.3f} {z:+6.3f} {magnitude:8.3f} {status}")
                
                # 30초마다 통계 출력
                if sample_count % 300 == 0:  # 10Hz에서 30초
                    vibration_rate = vibration_count/sample_count*100
                    print(f"📈 통계: 진동 {vibration_count}/{sample_count}회 ({vibration_rate:.1f}%), 최대: {max_vibration:.3f}g")
            
            time.sleep(0.1)  # 10Hz 샘플링
            
    except KeyboardInterrupt:
        print("\n\n🛑 테스트 종료")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("\n🔧 문제 해결 방법:")
        print("1. SPI가 활성화되어 있는지 확인: sudo raspi-config")
        print("2. 센서 SPI 연결 상태 확인 (CS, MOSI, MISO, SCLK)")
        print("3. 권한 확인: sudo 권한으로 실행 필요할 수 있음")
        print("4. 다른 SPI 디바이스 시도: spi_device=1")
        
    finally:
        if sensor:
            sensor.close()

if __name__ == "__main__":
    test_vibration_sensor()