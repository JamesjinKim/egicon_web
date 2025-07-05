#!/usr/bin/env python3
"""
IIS3DWB 진동센서 SPI 테스트 스크립트
===================================
STMicroelectronics IIS3DWB 3축 진동센서 (SPI 통신)
특징: 6kHz 대역폭, 초저노이즈, 진동 전용 설계
"""

import time
import spidev
import math
from typing import Optional, Tuple

class IIS3DWB_SPI:
    """IIS3DWB 3축 진동센서 SPI 클래스"""
    
    # 레지스터 주소 (SPI 읽기: MSB=1, 쓰기: MSB=0)
    WHO_AM_I = 0x0F
    CTRL1_XL = 0x10
    CTRL3_C = 0x12
    CTRL4_C = 0x13
    CTRL5_C = 0x14
    CTRL6_C = 0x15
    CTRL7_G = 0x16
    CTRL8_XL = 0x17
    CTRL9_XL = 0x18
    CTRL10_C = 0x19
    
    STATUS_REG = 0x1E
    OUT_TEMP_L = 0x20
    OUT_TEMP_H = 0x21
    OUTX_L_A = 0x28
    OUTX_H_A = 0x29
    OUTY_L_A = 0x2A
    OUTY_H_A = 0x2B
    OUTZ_L_A = 0x2C
    OUTZ_H_A = 0x2D
    
    # WHO_AM_I 응답값
    DEVICE_ID = 0x7B
    
    def __init__(self, spi_bus: int = 0, spi_device: int = 0):
        """
        IIS3DWB SPI 초기화
        
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
            
            # SPI 설정 (IIS3DWB는 최대 10MHz 지원)
            self.spi.max_speed_hz = 1000000  # 1MHz로 시작
            self.spi.mode = 0b00  # CPOL=0, CPHA=0
            
            print(f"🔧 SPI 연결 성공: 버스 {spi_bus}, 디바이스 {spi_device}")
            
            # 센서 확인 및 초기화
            self._check_sensor()
            self._initialize()
            
        except Exception as e:
            raise Exception(f"SPI 초기화 실패: {e}")
    
    def _spi_read_register(self, register: int) -> int:
        """SPI로 단일 레지스터 읽기"""
        # 읽기 명령: MSB=1
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
        # 읽기 명령: MSB=1, 다중바이트=1 (자동 증가)
        cmd = [0x80 | register] + [0x00] * length
        result = self.spi.xfer2(cmd)
        return result[1:]
    
    def _check_sensor(self):
        """센서 연결 및 식별 확인"""
        try:
            device_id = self._spi_read_register(self.WHO_AM_I)
            
            if device_id == self.DEVICE_ID:
                print(f"✅ IIS3DWB 센서 확인됨 (Device ID: 0x{device_id:02X})")
            else:
                raise Exception(f"잘못된 디바이스 ID: 0x{device_id:02X} (예상: 0x{self.DEVICE_ID:02X})")
                
        except Exception as e:
            raise Exception(f"센서 확인 실패: {e}")
    
    def _initialize(self):
        """센서 초기화 및 설정"""
        try:
            # 소프트웨어 리셋
            self._spi_write_register(self.CTRL3_C, 0x01)
            time.sleep(0.1)
            
            # CTRL1_XL: 가속도계 설정
            # ODR=26.7kHz (1111), FS=±2g (00), LPF2_XL_EN=0
            self._spi_write_register(self.CTRL1_XL, 0xF0)
            
            # CTRL3_C: 제어 레지스터 3
            # BDU=1 (Block Data Update), IF_INC=1 (자동 증가)
            self._spi_write_register(self.CTRL3_C, 0x44)
            
            # CTRL6_C: 고성능 모드 활성화
            self._spi_write_register(self.CTRL6_C, 0x00)
            
            # CTRL8_XL: 저역통과 필터 설정
            # LPF2_XL_EN=1, HPCF_XL=00 (ODR/800)
            self._spi_write_register(self.CTRL8_XL, 0x00)
            
            time.sleep(0.1)  # 초기화 대기
            
            # 설정 확인
            ctrl1 = self._spi_read_register(self.CTRL1_XL)
            ctrl3 = self._spi_read_register(self.CTRL3_C)
            
            print(f"✅ IIS3DWB 초기화 완료")
            print(f"   CTRL1_XL: 0x{ctrl1:02X} (26.7kHz, ±2g)")
            print(f"   CTRL3_C: 0x{ctrl3:02X} (BDU, 자동증가)")
            
        except Exception as e:
            raise Exception(f"IIS3DWB 초기화 실패: {e}")
    
    def read_raw_data(self) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """원시 가속도 데이터 읽기 (16비트)"""
        try:
            # 상태 레지스터 확인
            status = self._spi_read_register(self.STATUS_REG)
            if not (status & 0x01):  # XLDA 비트 확인
                return None, None, None
            
            # 6바이트 연속 읽기 (X, Y, Z 각각 2바이트)
            data = self._spi_read_multiple(self.OUTX_L_A, 6)
            
            # 16비트 데이터 변환
            x_raw = (data[1] << 8) | data[0]
            y_raw = (data[3] << 8) | data[2]
            z_raw = (data[5] << 8) | data[4]
            
            # 2의 보수 변환 (16비트)
            if x_raw > 32767: x_raw -= 65536
            if y_raw > 32767: y_raw -= 65536
            if z_raw > 32767: z_raw -= 65536
            
            return x_raw, y_raw, z_raw
            
        except Exception as e:
            print(f"❌ 데이터 읽기 실패: {e}")
            return None, None, None
    
    def read_acceleration(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """가속도 데이터 읽기 (g 단위)"""
        x_raw, y_raw, z_raw = self.read_raw_data()
        
        if x_raw is None:
            return None, None, None
        
        # ±2g 범위에서 16비트 해상도: 1 LSB = 0.061 mg
        scale = 0.061 / 1000.0  # mg를 g로 변환
        
        x_g = x_raw * scale
        y_g = y_raw * scale
        z_g = z_raw * scale
        
        return x_g, y_g, z_g
    
    def read_temperature(self) -> Optional[float]:
        """온도 데이터 읽기 (섭씨)"""
        try:
            temp_data = self._spi_read_multiple(self.OUT_TEMP_L, 2)
            temp_raw = (temp_data[1] << 8) | temp_data[0]
            
            # 2의 보수 변환
            if temp_raw > 32767:
                temp_raw -= 65536
            
            # 온도 변환: 25°C에서 0, 1 LSB = 1/256 °C
            temperature = 25.0 + (temp_raw / 256.0)
            
            return temperature
            
        except Exception as e:
            print(f"❌ 온도 읽기 실패: {e}")
            return None
    
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

def test_iis3dwb_sensor():
    """IIS3DWB 진동센서 테스트 메인 함수"""
    print("🔧 IIS3DWB 진동센서 SPI 테스트 시작")
    print("=" * 50)
    
    sensor = None
    try:
        # 먼저 SPI 활성화 상태 확인
        print("🔧 SPI 상태 확인...")
        try:
            with open("/boot/config.txt", "r") as f:
                config = f.read()
                if "dtparam=spi=on" not in config:
                    print("❌ SPI가 비활성화되어 있습니다")
                    print("💡 해결: sudo raspi-config → Interface Options → SPI → Enable")
                    return
                else:
                    print("✅ SPI 활성화됨")
        except:
            print("⚠️ SPI 상태 확인 불가")
        
        # IIS3DWB 센서 초기화 (CS0 시도)
        try:
            sensor = IIS3DWB_SPI(spi_bus=0, spi_device=0)
        except:
            print("❌ SPI0.0 실패, SPI0.1 시도 중...")
            sensor = IIS3DWB_SPI(spi_bus=0, spi_device=1)
        
        print(f"\n📊 진동 데이터 모니터링 시작...")
        print("Ctrl+C로 종료")
        print("-" * 80)
        print(f"{'Time':<8} {'X(g)':<8} {'Y(g)':<8} {'Z(g)':<8} {'Magnitude':<10} {'Temp(°C)':<8} {'Status'}")
        print("-" * 80)
        
        # 기준 진동값 측정 (처음 100회 평균)
        print("📏 기준값 측정 중... (5초)")
        baseline_samples = []
        for i in range(100):
            mag = sensor.calculate_vibration_magnitude()
            if mag is not None:
                baseline_samples.append(mag)
            time.sleep(0.05)  # 20Hz 샘플링
        
        if not baseline_samples:
            print("❌ 기준값 측정 실패")
            return
        
        baseline = sum(baseline_samples) / len(baseline_samples)
        threshold = baseline + 0.05  # 더 민감한 임계값 (0.05g)
        
        print(f"📏 기준 진동값: {baseline:.4f}g, 임계값: {threshold:.4f}g")
        print("-" * 80)
        
        vibration_count = 0
        sample_count = 0
        max_vibration = 0
        
        while True:
            x, y, z = sensor.read_acceleration()
            magnitude = sensor.calculate_vibration_magnitude()
            temperature = sensor.read_temperature()
            
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
                
                temp_str = f"{temperature:.1f}" if temperature else "--"
                
                print(f"{current_time} {x:+7.4f} {y:+7.4f} {z:+7.4f} {magnitude:9.4f} {temp_str:<8} {status}")
                
                # 60초마다 통계 출력 (20Hz에서 1200 샘플)
                if sample_count % 1200 == 0:
                    vibration_rate = vibration_count/sample_count*100
                    print(f"📈 통계: 진동 {vibration_count}/{sample_count}회 ({vibration_rate:.1f}%), 최대: {max_vibration:.4f}g")
            
            time.sleep(0.05)  # 20Hz 샘플링 (IIS3DWB는 26.7kHz까지 지원하지만 적정 속도로)
            
    except KeyboardInterrupt:
        print("\n\n🛑 테스트 종료")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("\n🔧 문제 해결 방법:")
        print("1. SPI 활성화: sudo raspi-config → Interface Options → SPI → Enable")
        print("2. 하드웨어 연결 확인:")
        print("   - CS: GPIO 8 (Pin 24) 또는 GPIO 7 (Pin 26)")
        print("   - MOSI: GPIO 10 (Pin 19)")
        print("   - MISO: GPIO 9 (Pin 21)")
        print("   - SCLK: GPIO 11 (Pin 23)")
        print("   - VCC: 3.3V, GND: Ground")
        print("3. 재부팅: sudo reboot")
        
    finally:
        if sensor:
            sensor.close()

if __name__ == "__main__":
    test_iis3dwb_sensor()