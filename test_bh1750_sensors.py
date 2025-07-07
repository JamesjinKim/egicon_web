#!/usr/bin/env python3
"""
BH1750 조도 센서 테스트 스크립트
라즈베리파이에서 실제 BH1750 센서 상태 확인
ref/gui_bh1750.py 코드를 기반으로 작성
"""

import asyncio
import json
import time
import os
import smbus2
from datetime import datetime

class SimpleBH1750:
    """BH1750 조도 센서 클래스 - ref/gui_bh1750.py에서 추출"""
    
    def __init__(self, bus=1, address=0x23, mux_channel=None, mux_address=0x70):
        self.bus_num = bus
        self.address = address
        self.mux_channel = mux_channel  # TCA9548A 멀티플렉서 채널
        self.mux_address = mux_address  # TCA9548A 주소
        self.bus = None
        self.debug = True
    
    def log_debug(self, message):
        """디버그 로그"""
        if self.debug:
            print(f"[BH1750] {message}")
    
    def test_i2c_availability(self):
        """I2C 버스 사용 가능성 테스트"""
        try:
            # I2C 디바이스 파일 존재 확인
            i2c_device = f"/dev/i2c-{self.bus_num}"
            if not os.path.exists(i2c_device):
                raise Exception(f"I2C 디바이스 {i2c_device}가 존재하지 않습니다")
            
            # 읽기/쓰기 권한 확인
            if not os.access(i2c_device, os.R_OK | os.W_OK):
                raise Exception(f"I2C 디바이스 {i2c_device}에 대한 권한이 없습니다")
            
            self.log_debug(f"I2C 디바이스 {i2c_device} 사용 가능")
            return True
            
        except Exception as e:
            self.log_debug(f"I2C 가용성 테스트 실패: {e}")
            return False
    
    def set_mux_channel(self):
        """TCA9548A 멀티플렉서 채널 설정"""
        if self.mux_channel is None:
            return True  # 멀티플렉서를 사용하지 않는 경우
        
        try:
            self.log_debug(f"TCA9548A 채널 {self.mux_channel} 설정 중...")
            # 채널 선택 (비트 마스크)
            channel_mask = 1 << self.mux_channel
            self.bus.write_byte(self.mux_address, channel_mask)
            time.sleep(0.001)  # 채널 전환 대기
            self.log_debug(f"TCA9548A 채널 {self.mux_channel} 설정 완료")
            return True
        except Exception as e:
            self.log_debug(f"TCA9548A 채널 설정 실패: {e}")
            return False
    
    def connect(self):
        """센서 연결 - 개선된 버전"""
        try:
            # I2C 가용성 먼저 테스트
            if not self.test_i2c_availability():
                raise Exception("I2C 버스를 사용할 수 없습니다")
            
            # 기존 연결이 있으면 종료
            if self.bus:
                self.bus.close()
                self.bus = None
            
            mux_info = f", MUX 채널 {self.mux_channel}" if self.mux_channel is not None else ""
            self.log_debug(f"I2C 버스 {self.bus_num}, 주소 0x{self.address:02X}{mux_info} 연결 시도...")
            
            # SMBus 연결
            self.bus = smbus2.SMBus(self.bus_num)
            
            # 멀티플렉서 채널 설정
            if not self.set_mux_channel():
                raise Exception("멀티플렉서 채널 설정 실패")
            
            # 연결 테스트 (여러 방법 시도)
            connection_success = False
            
            # 방법 1: Power On 명령
            try:
                self.log_debug("Power On 명령 시도...")
                self.bus.write_byte(self.address, 0x01)  # Power On
                time.sleep(0.01)
                connection_success = True
                self.log_debug("Power On 명령 성공")
            except Exception as e:
                self.log_debug(f"Power On 명령 실패: {e}")
            
            # 방법 2: Reset 명령
            if not connection_success:
                try:
                    self.log_debug("Reset 명령 시도...")
                    self.bus.write_byte(self.address, 0x07)  # Reset
                    time.sleep(0.01)
                    connection_success = True
                    self.log_debug("Reset 명령 성공")
                except Exception as e:
                    self.log_debug(f"Reset 명령 실패: {e}")
            
            # 방법 3: 직접 측정 명령 (가장 확실한 방법)
            if not connection_success:
                try:
                    self.log_debug("직접 측정 명령 시도...")
                    self.bus.write_byte(self.address, 0x20)  # One Time H-Resolution Mode
                    time.sleep(0.15)  # 150ms 대기
                    
                    # 데이터 읽기 시도
                    data = self.bus.read_i2c_block_data(self.address, 0x20, 2)
                    if len(data) == 2:
                        connection_success = True
                        self.log_debug("직접 측정 명령 성공")
                except Exception as e:
                    self.log_debug(f"직접 측정 명령 실패: {e}")
            
            if not connection_success:
                raise Exception("모든 연결 방법 실패")
            
            self.log_debug("BH1750 센서 연결 성공")
            return True
            
        except Exception as e:
            self.log_debug(f"센서 연결 실패: {e}")
            if self.bus:
                self.bus.close()
                self.bus = None
            raise e
    
    def read_light_safe(self):
        """안전한 조도값 읽기 (다양한 방법 시도)"""
        if not self.bus:
            raise Exception("센서가 연결되지 않음")
        
        # 멀티플렉서 채널 재설정
        if not self.set_mux_channel():
            raise Exception("멀티플렉서 채널 설정 실패")
        
        methods = [
            ("One Time H-Resolution", 0x20, 0.15),
            ("One Time H-Resolution2", 0x21, 0.15),
            ("One Time L-Resolution", 0x23, 0.02),
            ("Continuously H-Resolution", 0x10, 0.15)
        ]
        
        for method_name, command, wait_time in methods:
            try:
                self.log_debug(f"{method_name} 방식으로 측정 시도...")
                
                # 측정 명령 전송
                self.bus.write_byte(self.address, command)
                time.sleep(wait_time)
                
                # 데이터 읽기 방법 1: read_i2c_block_data
                try:
                    data = self.bus.read_i2c_block_data(self.address, command, 2)
                    self.log_debug(f"read_i2c_block_data 성공: {[f'0x{b:02X}' for b in data]}")
                except:
                    # 데이터 읽기 방법 2: 개별 read_byte
                    self.log_debug("read_i2c_block_data 실패, 개별 read_byte 시도...")
                    data = []
                    for _ in range(2):
                        byte_val = self.bus.read_byte(self.address)
                        data.append(byte_val)
                        time.sleep(0.001)
                    self.log_debug(f"개별 read_byte 성공: {[f'0x{b:02X}' for b in data]}")
                
                if len(data) >= 2:
                    # 조도값 계산
                    raw_value = (data[0] << 8) | data[1]
                    
                    # BH1750 조도 계산 공식
                    if command in [0x20, 0x21]:  # High resolution
                        lux = raw_value / 1.2
                    else:  # Low resolution
                        lux = raw_value / 1.2
                    
                    # 합리적인 범위 체크
                    if 0 <= lux <= 65535:
                        self.log_debug(f"{method_name} 측정 성공: {lux:.1f} lux (원시값: 0x{raw_value:04X})")
                        return round(lux, 1)
                    else:
                        self.log_debug(f"측정값이 범위를 벗어남: {lux}")
                        continue
                        
            except Exception as e:
                self.log_debug(f"{method_name} 방식 실패: {e}")
                continue
        
        raise Exception("모든 측정 방법 실패")
    
    def read_light(self):
        """조도값 읽기 (호환성을 위한 래퍼)"""
        return self.read_light_safe()
    
    def close(self):
        """연결 종료"""
        if self.bus:
            try:
                # 멀티플렉서 채널 설정
                if self.mux_channel is not None:
                    self.set_mux_channel()
                
                # Power Down 명령 전송
                self.bus.write_byte(self.address, 0x00)
                self.log_debug("Power Down 명령 전송")
            except:
                pass
            
            self.bus.close()
            self.bus = None
            self.log_debug("센서 연결 종료")

async def test_bh1750_sensors():
    """BH1750 센서 발견 및 데이터 읽기 테스트"""
    
    print("=" * 60)
    print("BH1750 조도 센서 테스트 시작")
    print("=" * 60)
    
    # 테스트할 설정들 (멀티플렉서와 직접 연결 모두 테스트)
    test_configs = [
        {"name": "Bus 1, Channel 4 (TCA9548A)", "bus": 1, "address": 0x23, "mux_channel": 4, "mux_address": 0x70},
        {"name": "Bus 0, Channel 4 (TCA9548A)", "bus": 0, "address": 0x23, "mux_channel": 4, "mux_address": 0x70},
        {"name": "Bus 1 직접 연결", "bus": 1, "address": 0x23, "mux_channel": None},
        {"name": "Bus 0 직접 연결", "bus": 0, "address": 0x23, "mux_channel": None},
        {"name": "Bus 1, ADDR=HIGH", "bus": 1, "address": 0x5C, "mux_channel": None},
        {"name": "Bus 0, ADDR=HIGH", "bus": 0, "address": 0x5C, "mux_channel": None},
    ]
    
    found_sensors = []
    
    print("\n1. BH1750 센서 검색 및 연결 테스트:")
    for i, config in enumerate(test_configs):
        print(f"\n  테스트 {i+1}: {config['name']}")
        print(f"    - I2C 버스: {config['bus']}")
        print(f"    - I2C 주소: 0x{config['address']:02X}")
        if config['mux_channel'] is not None:
            print(f"    - MUX 채널: {config['mux_channel']}")
        
        try:
            sensor = SimpleBH1750(
                bus=config['bus'],
                address=config['address'],
                mux_channel=config['mux_channel'],
                mux_address=config.get('mux_address', 0x70)
            )
            
            # 연결 테스트
            sensor.connect()
            
            # 조도 측정 테스트
            light_value = sensor.read_light()
            
            if light_value is not None:
                print(f"    ✅ 연결 성공: {light_value} lux")
                found_sensors.append({
                    "config": config,
                    "sensor": sensor,
                    "initial_value": light_value
                })
            else:
                print(f"    ❌ 측정 실패")
                sensor.close()
                
        except Exception as e:
            print(f"    ❌ 연결 실패: {e}")
    
    print(f"\n총 발견된 BH1750 센서 개수: {len(found_sensors)}")
    
    # 2. 발견된 센서들의 상세 테스트
    if found_sensors:
        print("\n2. 발견된 센서 상세 테스트:")
        
        for i, sensor_info in enumerate(found_sensors):
            config = sensor_info['config']
            sensor = sensor_info['sensor']
            
            print(f"\n  센서 {i+1}: {config['name']}")
            print(f"    초기값: {sensor_info['initial_value']} lux")
            
            # 5회 연속 측정 테스트
            print("    연속 측정 테스트 (5회):")
            measurements = []
            
            for j in range(5):
                try:
                    light_value = sensor.read_light()
                    measurements.append(light_value)
                    print(f"      {j+1}회: {light_value} lux")
                    time.sleep(1)  # 1초 간격
                except Exception as e:
                    print(f"      {j+1}회: 측정 실패 - {e}")
            
            # 통계 계산
            if measurements:
                avg_light = sum(measurements) / len(measurements)
                min_light = min(measurements)
                max_light = max(measurements)
                print(f"    통계: 평균 {avg_light:.1f} lux, 최소 {min_light:.1f} lux, 최대 {max_light:.1f} lux")
                
                # 조도 레벨 판정
                if avg_light < 1:
                    level = "매우 어두움"
                elif avg_light < 10:
                    level = "어두움"
                elif avg_light < 50:
                    level = "희미함"
                elif avg_light < 200:
                    level = "실내조명"
                elif avg_light < 500:
                    level = "밝은실내"
                elif avg_light < 1000:
                    level = "흐린날"
                else:
                    level = "밝음"
                
                print(f"    조도 레벨: {level}")
    
    # 3. 프론트엔드 API 호환 데이터 생성
    print("\n3. 프론트엔드 API 호환 데이터 구조:")
    api_sensors = []
    
    for i, sensor_info in enumerate(found_sensors):
        config = sensor_info['config']
        sensor = sensor_info['sensor']
        
        try:
            # 최종 측정
            light_value = sensor.read_light()
            
            # API 호환 센서 정보 생성
            sensor_data = {
                "sensor_type": "BH1750",
                "bus": config['bus'],
                "mux_channel": config.get('mux_channel'),
                "address": config['address'],
                "sensor_id": f"bh1750_{config['bus']}_{config.get('mux_channel', 'direct')}",
                "light": light_value,
                "timestamp": datetime.now().isoformat(),
                "status": "online"
            }
            
            api_sensors.append(sensor_data)
            print(f"  센서 {i+1}: {sensor_data['sensor_id']} = {light_value} lux")
            
        except Exception as e:
            print(f"  센서 {i+1}: 측정 실패 - {e}")
    
    # 4. light 그룹 API 응답 시뮬레이션
    print("\n4. /api/sensors/groups API 응답 시뮬레이션:")
    light_group = {
        "success": True,
        "groups": {
            "light": {
                "sensors": api_sensors,
                "count": len(api_sensors),
                "active_count": len(api_sensors),
                "status": "online" if api_sensors else "offline",
                "status_text": f"{len(api_sensors)}개 연결됨" if api_sensors else "센서 없음",
                "types_summary": f"BH1750×{len(api_sensors)}" if api_sensors else "센서 없음"
            }
        }
    }
    
    print(json.dumps(light_group, indent=2, ensure_ascii=False))
    
    # 5. 개별 센서 API 엔드포인트 테스트
    print("\n5. 개별 센서 API 엔드포인트 테스트:")
    for sensor_info in found_sensors:
        config = sensor_info['config']
        sensor = sensor_info['sensor']
        
        try:
            light_value = sensor.read_light()
            
            # API 응답 형식
            api_response = {
                "success": True,
                "data": {
                    "light": light_value,
                    "timestamp": datetime.now().isoformat()
                },
                "sensor_info": {
                    "bus": config['bus'],
                    "mux_channel": config.get('mux_channel'),
                    "address": f"0x{config['address']:02X}"
                }
            }
            
            endpoint = f"/api/sensors/bh1750/{config['bus']}/{config.get('mux_channel', 'direct')}"
            print(f"  {endpoint}:")
            print(f"    응답: {json.dumps(api_response, indent=4, ensure_ascii=False)}")
            
        except Exception as e:
            print(f"  API 테스트 실패: {e}")
    
    # 6. 센서 정리
    print("\n6. 센서 연결 정리:")
    for sensor_info in found_sensors:
        try:
            sensor_info['sensor'].close()
            print(f"  {sensor_info['config']['name']}: 연결 종료됨")
        except:
            pass
    
    print("\n" + "=" * 60)
    print("BH1750 조도 센서 테스트 완료")
    print(f"발견된 센서: {len(found_sensors)}개")
    if found_sensors:
        print("센서들:")
        for i, sensor_info in enumerate(found_sensors):
            config = sensor_info['config']
            print(f"  {i+1}. {config['name']} - {sensor_info['initial_value']} lux")
    else:
        print("⚠️  발견된 센서가 없습니다.")
        print("   - I2C가 활성화되어 있는지 확인하세요 (sudo raspi-config)")
        print("   - BH1750 센서가 올바르게 연결되어 있는지 확인하세요")
        print("   - sudo i2cdetect -y 1 명령으로 I2C 스캔을 해보세요")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_bh1750_sensors())