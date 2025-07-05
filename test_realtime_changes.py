#!/usr/bin/env python3
"""
SDP810 실시간 변화 감지 테스트
===========================
센서에서 실제로 변화하는 데이터를 받는지 확인
"""

import time
import json
import requests
from datetime import datetime

class RealtimeChangeTest:
    """실시간 변화 감지 테스트"""
    
    def __init__(self):
        self.api_url = "http://localhost:8001/api/sensors/sdp810/1/0"
        self.previous_values = []
        self.change_count = 0
        self.no_change_count = 0
        
    def get_sensor_data(self):
        """센서 데이터 1회 조회"""
        try:
            response = requests.get(self.api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data'):
                    pressure = data['data']['data']['differential_pressure']
                    timestamp = data['data']['timestamp']
                    return pressure, timestamp
            return None, None
        except Exception as e:
            print(f"❌ API 호출 실패: {e}")
            return None, None
    
    def test_continuous_changes(self, duration=30, interval=0.5):
        """연속 변화 감지 테스트"""
        print(f"🔄 {duration}초간 {interval}초 간격으로 실시간 변화 감지 테스트")
        print("=" * 80)
        
        start_time = time.time()
        measurement_count = 0
        
        while time.time() - start_time < duration:
            measurement_count += 1
            current_time = datetime.now()
            
            # 센서 데이터 조회
            pressure, api_timestamp = self.get_sensor_data()
            
            if pressure is not None:
                # 변화 감지
                if self.previous_values:
                    last_value = self.previous_values[-1]['pressure']
                    change = abs(pressure - last_value)
                    
                    if change > 0.001:  # 0.001 Pa 이상 변화
                        self.change_count += 1
                        change_indicator = f"📈 변화: {change:.4f} Pa"
                    else:
                        self.no_change_count += 1
                        change_indicator = "⏸️  변화없음"
                    
                    print(f"#{measurement_count:3d} | {current_time.strftime('%H:%M:%S.%f')[:-3]} | {pressure:8.4f} Pa | {change_indicator}")
                else:
                    print(f"#{measurement_count:3d} | {current_time.strftime('%H:%M:%S.%f')[:-3]} | {pressure:8.4f} Pa | 🎯 첫 측정")
                
                # 이전 값 저장 (최근 10개만 유지)
                self.previous_values.append({
                    'pressure': pressure,
                    'timestamp': current_time.isoformat(),
                    'api_timestamp': api_timestamp,
                    'measurement': measurement_count
                })
                
                if len(self.previous_values) > 10:
                    self.previous_values.pop(0)
            else:
                print(f"#{measurement_count:3d} | {current_time.strftime('%H:%M:%S.%f')[:-3]} | API 오류")
            
            time.sleep(interval)
        
        return measurement_count
    
    def analyze_results(self, total_measurements):
        """결과 분석"""
        print("\n" + "=" * 80)
        print("📊 실시간 변화 감지 분석 결과")
        print("=" * 80)
        
        if not self.previous_values:
            print("❌ 측정된 데이터가 없습니다")
            return
        
        # 기본 통계
        pressures = [v['pressure'] for v in self.previous_values]
        avg_pressure = sum(pressures) / len(pressures)
        min_pressure = min(pressures)
        max_pressure = max(pressures)
        pressure_range = max_pressure - min_pressure
        
        print(f"📈 총 측정 횟수: {total_measurements}")
        print(f"✅ 성공한 측정: {len(self.previous_values)}")
        print(f"📊 변화 감지: {self.change_count}회")
        print(f"⏸️  변화 없음: {self.no_change_count}회")
        print(f"📉 평균 압력: {avg_pressure:.4f} Pa")
        print(f"📏 압력 범위: {min_pressure:.4f} ~ {max_pressure:.4f} Pa ({pressure_range:.4f} Pa)")
        
        # 변화율 계산
        if total_measurements > 0:
            change_rate = (self.change_count / (self.change_count + self.no_change_count)) * 100 if (self.change_count + self.no_change_count) > 0 else 0
            print(f"🎯 변화 감지율: {change_rate:.1f}%")
        
        # 연속 변화 패턴 분석
        if len(self.previous_values) >= 2:
            print(f"\n🔍 연속 변화 패턴:")
            consecutive_changes = 0
            max_consecutive = 0
            
            for i in range(1, len(self.previous_values)):
                change = abs(self.previous_values[i]['pressure'] - self.previous_values[i-1]['pressure'])
                if change > 0.001:
                    consecutive_changes += 1
                    max_consecutive = max(max_consecutive, consecutive_changes)
                else:
                    consecutive_changes = 0
            
            print(f"   최대 연속 변화: {max_consecutive}회")
        
        # 최근 측정값들 출력
        print(f"\n📋 최근 측정값들:")
        for i, value in enumerate(self.previous_values[-5:], 1):
            print(f"   {i}. {value['pressure']:8.4f} Pa @ {value['timestamp'][-12:-3]}")
        
        # 결론
        print(f"\n🎯 결론:")
        if self.change_count > 0:
            print(f"   ✅ 센서가 실시간 변화를 감지하고 있습니다 ({self.change_count}회 변화)")
        else:
            print(f"   ❌ 센서 변화가 감지되지 않습니다 - 정적 데이터일 가능성")
        
        if pressure_range < 0.01:
            print(f"   ⚠️  압력 변화 범위가 매우 작습니다 ({pressure_range:.4f} Pa)")
        else:
            print(f"   📈 압력 변화 범위가 적절합니다 ({pressure_range:.4f} Pa)")

def main():
    """메인 테스트 실행"""
    print("🚀 SDP810 실시간 변화 감지 테스트 시작")
    print("📌 센서에 물리적 변화를 주면서 테스트하세요 (바람, 압력 변화 등)")
    print("")
    
    tester = RealtimeChangeTest()
    
    try:
        # 30초간 0.5초 간격으로 테스트
        total_measurements = tester.test_continuous_changes(duration=30, interval=0.5)
        
        # 결과 분석
        tester.analyze_results(total_measurements)
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자가 테스트를 중단했습니다")
        tester.analyze_results(len(tester.previous_values))
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    main()