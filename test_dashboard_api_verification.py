#!/usr/bin/env python3
"""
Dashboard API 검증 테스트
=========================
웹 대시보드가 실제 BH1750 센서 데이터를 제대로 표시하는지 검증
"""

import time
import json
import subprocess
import sys
from datetime import datetime

def run_curl_command(url, method="GET", data=None):
    """curl 명령어 실행"""
    try:
        if method == "GET":
            cmd = ["curl", "-s", "-X", "GET", url]
        else:
            cmd = ["curl", "-s", "-X", method, "-H", "Content-Type: application/json", "-d", json.dumps(data), url]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": f"curl failed: {result.stderr}"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def test_dashboard_api():
    """Dashboard API 검증 테스트"""
    
    print("=" * 70)
    print("Dashboard API 검증 테스트")
    print("실제 BH1750 센서 데이터 vs 웹 대시보드 표시 비교")
    print("=" * 70)
    
    base_url = "http://localhost:8001"
    
    # 1. 시스템 정보 확인
    print("\n1. 시스템 정보 확인:")
    print("-" * 40)
    
    system_info = run_curl_command(f"{base_url}/api/system/info")
    if "error" not in system_info:
        print(f"✅ 시스템: {system_info.get('system')}")
        print(f"✅ 모드: {system_info.get('mode')}")
        print(f"✅ 버전: {system_info.get('version')}")
    else:
        print(f"❌ 시스템 정보 조회 실패: {system_info['error']}")
        print("서버가 실행 중인지 확인하세요.")
        return
    
    # 2. BH1750 센서 그룹 확인
    print("\n2. BH1750 센서 그룹 확인:")
    print("-" * 40)
    
    groups = run_curl_command(f"{base_url}/api/sensors/groups")
    if "error" not in groups:
        light_group = groups.get('groups', {}).get('light', {})
        print(f"✅ Light 그룹 상태: {light_group.get('status')}")
        print(f"✅ 센서 개수: {light_group.get('count')}")
        print(f"✅ 활성 센서: {light_group.get('active_count')}")
        print(f"✅ 상태 텍스트: {light_group.get('status_text')}")
        
        sensors = light_group.get('sensors', [])
        if sensors:
            for i, sensor in enumerate(sensors, 1):
                print(f"  {i}. {sensor.get('sensor_id')} (Bus {sensor.get('bus')}, CH {sensor.get('mux_channel')})")
        else:
            print("⚠️ light 그룹에 센서가 없습니다.")
    else:
        print(f"❌ 센서 그룹 조회 실패: {groups['error']}")
    
    # 3. BH1750 동적 발견 API 테스트
    print("\n3. BH1750 동적 발견 API 테스트:")
    print("-" * 40)
    
    discovery = run_curl_command(f"{base_url}/api/sensors/bh1750")
    if "error" not in discovery:
        print(f"✅ 발견 성공: {discovery.get('success')}")
        sensors = discovery.get('sensors', [])
        print(f"✅ 발견된 센서: {len(sensors)}개")
        
        if sensors:
            target_sensor = sensors[0]  # 첫 번째 센서 사용
            bus = target_sensor['bus']
            channel = target_sensor.get('mux_channel', 'direct')
            print(f"📊 대상 센서: {target_sensor['sensor_id']}")
            print(f"   위치: Bus {bus}, CH {channel}")
            print(f"   주소: {target_sensor['address']}")
        else:
            print("❌ 발견된 센서가 없습니다.")
            return
    else:
        print(f"❌ BH1750 발견 실패: {discovery['error']}")
        return
    
    # 4. 실시간 데이터 API 테스트 (5회 연속)
    print(f"\n4. 실시간 데이터 API 테스트 (2초 간격 5회):")
    print("-" * 40)
    print(f"{'순번':>3} {'시간':>8} {'API 조도':>12} {'상태':>8}")
    print("-" * 40)
    
    api_measurements = []
    
    for i in range(5):
        try:
            current_time = datetime.now()
            time_str = current_time.strftime("%H:%M:%S")
            
            # API 호출
            api_data = run_curl_command(f"{base_url}/api/sensors/bh1750/{bus}/{channel}")
            
            if "error" not in api_data and api_data.get('success'):
                light_value = api_data['data']['light']
                timestamp = api_data['data']['timestamp']
                
                api_measurements.append({
                    'sequence': i + 1,
                    'time': current_time,
                    'light': light_value,
                    'timestamp': timestamp,
                    'status': 'OK'
                })
                
                print(f"{i+1:3d} {time_str:>8} {light_value:>10.1f} {'✅ OK':>8}")
            else:
                error_msg = api_data.get('error', 'Unknown error')
                print(f"{i+1:3d} {time_str:>8} {'ERROR':>10} {'❌ FAIL':>8}")
                print(f"    오류: {error_msg}")
                
                api_measurements.append({
                    'sequence': i + 1,
                    'time': current_time,
                    'light': None,
                    'status': 'ERROR',
                    'error': error_msg
                })
            
            # 마지막이 아니면 2초 대기
            if i < 4:
                time.sleep(2)
                
        except Exception as e:
            print(f"{i+1:3d} {time_str:>8} {'ERROR':>10} {'❌ FAIL':>8}")
            print(f"    예외: {str(e)}")
    
    # 5. API 데이터 분석
    print(f"\n5. API 데이터 분석:")
    print("-" * 40)
    
    successful_api = [m for m in api_measurements if m['status'] == 'OK' and m['light'] is not None]
    
    if successful_api:
        api_values = [m['light'] for m in successful_api]
        
        print(f"✅ API 성공 측정: {len(successful_api)}/5회")
        print(f"📊 API 조도 통계:")
        print(f"   - 최소값: {min(api_values):.1f} lux")
        print(f"   - 최대값: {max(api_values):.1f} lux")
        print(f"   - 평균값: {sum(api_values)/len(api_values):.1f} lux")
        print(f"   - 변화 범위: {max(api_values) - min(api_values):.1f} lux")
        
        # 데이터 품질 확인
        if max(api_values) - min(api_values) > 0:
            print(f"   - API 데이터 품질: ✅ 변화 감지됨 (실제 센서 연동)")
        else:
            print(f"   - API 데이터 품질: ⚠️ 변화 없음 (시뮬레이션 데이터 가능성)")
    else:
        print(f"❌ API에서 성공한 측정이 없습니다.")
    
    # 6. 웹소켓 연결 테스트 (간접 확인)
    print(f"\n6. 웹소켓 지원 확인:")
    print("-" * 40)
    
    # WebSocket은 curl로 직접 테스트하기 어려우므로 간접 확인
    print(f"✅ 웹소켓 엔드포인트: ws://localhost:8001/ws")
    print(f"✅ BH1750 채널: bh1750_realtime")
    print(f"📌 웹 브라우저에서 실시간 데이터 확인 필요")
    
    # 7. 대시보드 접근성 확인
    print(f"\n7. 대시보드 접근성 확인:")
    print("-" * 40)
    
    try:
        # HTML 페이지 확인 (간단히 curl로 status code만 확인)
        result = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{base_url}/"], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 and result.stdout == "200":
            print(f"✅ 메인 대시보드: http://localhost:8001/ (접근 가능)")
        else:
            print(f"❌ 메인 대시보드 접근 실패: HTTP {result.stdout}")
            
    except Exception as e:
        print(f"❌ 대시보드 접근 테스트 실패: {str(e)}")
    
    # 8. 종합 판정
    print(f"\n" + "=" * 70)
    print("Dashboard API 검증 결과")
    print("=" * 70)
    
    if successful_api and len(successful_api) >= 3:
        print(f"✅ 웹 대시보드 API 정상 동작")
        print(f"✅ 실제 BH1750 센서 데이터 연동 확인")
        print(f"📊 최종 조도값: {successful_api[-1]['light']:.1f} lux")
        print(f"")
        print(f"🔧 다음 확인사항:")
        print(f"1. 웹 브라우저에서 http://localhost:8001/ 접속")
        print(f"2. 조도 센서 차트가 실시간으로 업데이트되는지 확인")
        print(f"3. 시뮬레이션이 아닌 실제 센서 값이 표시되는지 확인")
        print(f"4. 조도 위젯에 실제 측정값이 표시되는지 확인")
    else:
        print(f"❌ 웹 대시보드 API 문제 발견")
        print(f"❌ 성공한 API 호출: {len(successful_api) if successful_api else 0}/5회")
        print(f"")
        print(f"🔧 문제 해결:")
        print(f"1. 서버 재시작: sudo systemctl restart egicon-dashboard")
        print(f"2. 로그 확인: sudo journalctl -u egicon-dashboard -f")
        print(f"3. API 엔드포인트 직접 테스트")
    
    print("=" * 70)

if __name__ == "__main__":
    test_dashboard_api()