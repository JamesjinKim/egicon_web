#!/usr/bin/env python3
"""
IIS3DWB 3축 진동 센서 테스트 프로그램
STMicroelectronics IIS3DWB 초광대역 저노이즈 3축 디지털 진동 센서
SPI 인터페이스를 통한 센서 스캔 및 데이터 읽기
"""

import spidev
import time
import struct
import sys

class IIS3DWB:
    # 레지스터 주소 정의
    WHO_AM_I = 0x0F
    CTRL1_XL = 0x10
    CTRL3_C = 0x12
    CTRL4_C = 0x13
    CTRL5_C = 0x14
    CTRL6_C = 0x15
    CTRL7_C = 0x16
    CTRL8_XL = 0x17
    STATUS_REG = 0x1E
    OUT_TEMP_L = 0x20
    OUT_TEMP_H = 0x21
    OUTX_L_A = 0x28
    OUTX_H_A = 0x29
    OUTY_L_A = 0x2A
    OUTY_H_A = 0x2B
    OUTZ_L_A = 0x2C
    OUTZ_H_A = 0x2D
    
    # 상수 정의
    DEVICE_ID = 0x7B  # WHO_AM_I 예상값
    READ_FLAG = 0x80  # 읽기 명령 플래그
    
    # 풀 스케일 설정값
    FS_2G = 0x00
    FS_16G = 0x04
    FS_4G = 0x08
    FS_8G = 0x0C
    
    def __init__(self, bus=0, device=0, max_speed_hz=1000000):
        """
        IIS3DWB 센서 초기화
        
        Args:
            bus: SPI 버스 번호 (보통 0)
            device: SPI 디바이스 번호 (CS 핀에 따라 0 또는 1)
            max_speed_hz: SPI 클럭 속도 (최대 10MHz)
        """
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = max_speed_hz
        self.spi.mode = 3  # SPI Mode 3 (CPOL=1, CPHA=1)
        self.spi.bits_per_word = 8
        
        # 센서 스케일 팩터 (mg/LSB)
        self.scale_factors = {
            self.FS_2G: 0.061,
            self.FS_4G: 0.122,
            self.FS_8G: 0.244,
            self.FS_16G: 0.488
        }
        self.current_scale = self.FS_2G
        
    def read_register(self, reg_addr):
        """단일 레지스터 읽기"""
        # 읽기 명령: MSB=1, 주소 7비트
        tx_data = [reg_addr | self.READ_FLAG, 0x00]
        rx_data = self.spi.xfer2(tx_data)
        return rx_data[1]
    
    def write_register(self, reg_addr, value):
        """단일 레지스터 쓰기"""
        # 쓰기 명령: MSB=0, 주소 7비트
        tx_data = [reg_addr & 0x7F, value]
        self.spi.xfer2(tx_data)
        
    def read_multiple_registers(self, start_addr, length):
        """연속된 여러 레지스터 읽기"""
        tx_data = [start_addr | self.READ_FLAG] + [0x00] * length
        rx_data = self.spi.xfer2(tx_data)
        return rx_data[1:]
    
    def scan_device(self):
        """센서 스캔 및 디바이스 ID 확인"""
        print("IIS3DWB 센서 스캔 중...")
        
        try:
            # WHO_AM_I 레지스터 읽기
            device_id = self.read_register(self.WHO_AM_I)
            print(f"디바이스 ID: 0x{device_id:02X}")
            
            if device_id == self.DEVICE_ID:
                print("✓ IIS3DWB 센서를 찾았습니다!")
                return True
            else:
                print(f"✗ 알 수 없는 디바이스 (예상: 0x{self.DEVICE_ID:02X}, 실제: 0x{device_id:02X})")
                return False
                
        except Exception as e:
            print(f"✗ 센서 스캔 실패: {e}")
            return False
    
    def reset_device(self):
        """소프트웨어 리셋"""
        print("센서 리셋 중...")
        # SW_RESET 비트 설정
        self.write_register(self.CTRL3_C, 0x01)
        time.sleep(0.1)  # 리셋 대기
        
    def configure_sensor(self, scale=FS_2G, odr_enabled=True):
        """센서 설정"""
        print("센서 설정 중...")
        
        # 가속도계 설정
        # XL_EN[2:0] = 101 (가속도계 활성화)
        # FS[1:0] = scale
        # LPF2_XL_EN = 0 (첫 번째 스테이지 필터 사용)
        ctrl1_val = 0xA0 | (scale >> 2)  # 101x xxxx
        self.write_register(self.CTRL1_XL, ctrl1_val)
        self.current_scale = scale
        
        # BDU (Block Data Update) 활성화
        ctrl3_val = self.read_register(self.CTRL3_C)
        ctrl3_val |= 0x40  # BDU = 1
        self.write_register(self.CTRL3_C, ctrl3_val)
        
        print(f"✓ 설정 완료 (스케일: ±{self._get_scale_g()}g, ODR: 26.7kHz)")
        
    def _get_scale_g(self):
        """현재 스케일을 g 단위로 반환"""
        scale_map = {self.FS_2G: 2, self.FS_4G: 4, self.FS_8G: 8, self.FS_16G: 16}
        return scale_map[self.current_scale]
    
    def read_status(self):
        """상태 레지스터 읽기"""
        status = self.read_register(self.STATUS_REG)
        return {
            'xlda': bool(status & 0x01),  # 가속도계 데이터 준비
            'tda': bool(status & 0x04)     # 온도 데이터 준비
        }
    
    def read_acceleration_raw(self):
        """원시 가속도 데이터 읽기"""
        # 6바이트 연속 읽기 (X_L, X_H, Y_L, Y_H, Z_L, Z_H)
        data = self.read_multiple_registers(self.OUTX_L_A, 6)
        
        # 16비트 부호있는 정수로 변환
        x = struct.unpack('<h', bytes([data[0], data[1]]))[0]
        y = struct.unpack('<h', bytes([data[2], data[3]]))[0]
        z = struct.unpack('<h', bytes([data[4], data[5]]))[0]
        
        return x, y, z
    
    def read_acceleration_mg(self):
        """가속도 데이터를 mg 단위로 읽기"""
        x_raw, y_raw, z_raw = self.read_acceleration_raw()
        scale = self.scale_factors[self.current_scale]
        
        x_mg = x_raw * scale
        y_mg = y_raw * scale
        z_mg = z_raw * scale
        
        return x_mg, y_mg, z_mg
    
    def read_acceleration_g(self):
        """가속도 데이터를 g 단위로 읽기"""
        x_mg, y_mg, z_mg = self.read_acceleration_mg()
        return x_mg / 1000.0, y_mg / 1000.0, z_mg / 1000.0
    
    def read_temperature_raw(self):
        """원시 온도 데이터 읽기"""
        data = self.read_multiple_registers(self.OUT_TEMP_L, 2)
        temp_raw = struct.unpack('<h', bytes([data[0], data[1]]))[0]
        return temp_raw
    
    def read_temperature_celsius(self):
        """온도를 섭씨로 읽기"""
        temp_raw = self.read_temperature_raw()
        # 256 LSB/°C, 25°C에서 0 LSB
        temp_celsius = 25.0 + (temp_raw / 256.0)
        return temp_celsius
    
    def close(self):
        """SPI 연결 종료"""
        self.spi.close()

def main():
    """메인 테스트 함수"""
    print("=== IIS3DWB 센서 테스트 프로그램 ===\n")
    
    # 센서 객체 생성 (CS1 핀 사용: GPIO 7)
    sensor = IIS3DWB(bus=0, device=1, max_speed_hz=1000000)
    
    try:
        # 1. 센서 스캔
        if not sensor.scan_device():
            print("센서를 찾을 수 없습니다. 연결을 확인하세요.")
            return
        
        # 2. 센서 리셋
        sensor.reset_device()
        time.sleep(0.1)
        
        # 3. 센서 설정 (±2g 스케일)
        sensor.configure_sensor(scale=sensor.FS_2G)
        time.sleep(0.1)
        
        # 4. 연속 데이터 읽기
        print("\n데이터 수집 시작 (Ctrl+C로 종료)\n")
        print("시간\t\tX(g)\t\tY(g)\t\tZ(g)\t\t온도(°C)")
        print("-" * 80)
        
        while True:
            # 상태 확인
            status = sensor.read_status()
            
            if status['xlda']:  # 가속도 데이터 준비됨
                # 가속도 읽기
                x, y, z = sensor.read_acceleration_g()
                
                # 온도 읽기
                temp = sensor.read_temperature_celsius()
                
                # 현재 시간
                timestamp = time.strftime("%H:%M:%S")
                
                # 데이터 출력
                print(f"{timestamp}\t{x:+8.4f}\t{y:+8.4f}\t{z:+8.4f}\t{temp:6.2f}")
                
            time.sleep(0.1)  # 100ms 간격
            
    except KeyboardInterrupt:
        print("\n\n프로그램을 종료합니다.")
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        
    finally:
        sensor.close()
        print("SPI 연결을 종료했습니다.")

if __name__ == "__main__":
    main()