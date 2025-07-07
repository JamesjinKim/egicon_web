#!/usr/bin/env python3
"""
BH1750 API Integration Test
===========================
Frontend-Backend 통합 테스트 및 실시간 데이터 검증
"""

import asyncio
import json
import requests
import time
from datetime import datetime

class BH1750APIIntegrationTester:
    """BH1750 API 통합 테스트 클래스"""
    
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 5
        
    def test_api_endpoints(self):
        """모든 BH1750 API 엔드포인트 테스트"""
        
        print("=" * 70)
        print("BH1750 API Integration Test")
        print("=" * 70)
        
        # 1. Dynamic Discovery Test
        print("\n1. Dynamic Discovery Test:")
        print("-" * 40)
        
        try:
            response = self.session.get(f"{self.base_url}/api/sensors/bh1750")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Discovery successful: {data['success']}")
                print(f"Found sensors: {len(data.get('sensors', []))}")
                
                if data.get('sensors'):
                    for sensor in data['sensors']:
                        print(f"  - {sensor['sensor_id']}: {sensor['location']}")
                        
                    # Store first sensor for individual tests
                    self.test_sensor = data['sensors'][0]
                else:
                    print("⚠️ No sensors found in discovery")
                    self.test_sensor = None
            else:
                print(f"❌ Discovery failed with status {response.status_code}")
                self.test_sensor = None
                
        except Exception as e:
            print(f"❌ Discovery request failed: {e}")
            self.test_sensor = None
        
        # 2. Individual Sensor Data Test
        print("\n2. Individual Sensor Data Test:")
        print("-" * 40)
        
        if self.test_sensor:
            bus = self.test_sensor['bus']
            channel = self.test_sensor.get('mux_channel', 'direct')
            
            try:
                response = self.session.get(f"{self.base_url}/api/sensors/bh1750/{bus}/{channel}")
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Data read successful: {data['success']}")
                    
                    if data['success']:
                        light_value = data['data']['light']
                        timestamp = data['data']['timestamp']
                        print(f"Light: {light_value} lux")
                        print(f"Timestamp: {timestamp}")
                        
                        # Sensor info
                        sensor_info = data.get('sensor_info', {})
                        print(f"Bus: {sensor_info.get('bus')}")
                        print(f"Channel: {sensor_info.get('mux_channel')}")
                        print(f"Address: {sensor_info.get('address')}")
                    else:
                        print(f"❌ Data read failed: {data.get('error', 'Unknown error')}")
                else:
                    print(f"❌ Data request failed with status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Data request failed: {e}")
        else:
            print("⚠️ No sensor available for individual test")
        
        # 3. Sensor Test Endpoint
        print("\n3. Sensor Test Endpoint:")
        print("-" * 40)
        
        if self.test_sensor:
            test_payload = {
                "i2c_bus": self.test_sensor['bus'],
                "mux_channel": self.test_sensor.get('mux_channel'),
                "address": self.test_sensor['address']
            }
            
            try:
                response = self.session.post(
                    f"{self.base_url}/api/sensors/bh1750/test",
                    json=test_payload
                )
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Test successful: {data['success']}")
                    
                    if data['success']:
                        test_result = data['test_result']
                        print(f"Test result: {test_result}")
                        
                        if 'light' in test_result:
                            print(f"Light measurement: {test_result['light']} lux")
                        
                        sensor_info = data.get('sensor_info', {})
                        print(f"Sensor: {sensor_info.get('sensor_type')} at {sensor_info.get('location')}")
                    else:
                        print(f"❌ Test failed: {data.get('error', 'Unknown error')}")
                else:
                    print(f"❌ Test request failed with status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Test request failed: {e}")
        else:
            print("⚠️ No sensor available for test")
            
        # 4. Real-time Data Polling Test
        print("\n4. Real-time Data Polling Test:")
        print("-" * 40)
        
        if self.test_sensor:
            bus = self.test_sensor['bus']
            channel = self.test_sensor.get('mux_channel', 'direct')
            
            print(f"Polling sensor {self.test_sensor['sensor_id']} for 10 seconds...")
            
            start_time = time.time()
            measurements = []
            
            while time.time() - start_time < 10:
                try:
                    response = self.session.get(f"{self.base_url}/api/sensors/bh1750/{bus}/{channel}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data['success']:
                            light_value = data['data']['light']
                            timestamp = data['data']['timestamp']
                            measurements.append({
                                'light': light_value,
                                'timestamp': timestamp,
                                'time': time.time()
                            })
                            print(f"  {len(measurements):2d}. {light_value:7.2f} lux at {timestamp}")
                        else:
                            print(f"  ❌ Read failed: {data.get('error', 'Unknown')}")
                    else:
                        print(f"  ❌ HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"  ❌ Request failed: {e}")
                
                time.sleep(1)
            
            # Statistics
            if measurements:
                light_values = [m['light'] for m in measurements]
                print(f"\n📊 Polling Statistics:")
                print(f"  Total measurements: {len(measurements)}")
                print(f"  Min light: {min(light_values):.2f} lux")
                print(f"  Max light: {max(light_values):.2f} lux")
                print(f"  Avg light: {sum(light_values)/len(light_values):.2f} lux")
                
                # Check for variation (real sensor should have some variation)
                light_range = max(light_values) - min(light_values)
                print(f"  Light range: {light_range:.2f} lux")
                
                if light_range > 0:
                    print(f"  ✅ Sensor shows variation (likely real sensor)")
                else:
                    print(f"  ⚠️ Sensor shows no variation (likely mock data)")
            else:
                print("  ❌ No successful measurements")
        else:
            print("⚠️ No sensor available for polling test")
        
        # 5. System Integration Test
        print("\n5. System Integration Test:")
        print("-" * 40)
        
        try:
            # Test system info
            response = self.session.get(f"{self.base_url}/api/system/info")
            if response.status_code == 200:
                system_info = response.json()
                print(f"✅ System: {system_info['system']}")
                print(f"Mode: {system_info['mode']}")
                print(f"Features: {system_info['features']}")
            else:
                print(f"❌ System info failed: {response.status_code}")
                
            # Test sensor groups (light group)
            response = self.session.get(f"{self.base_url}/api/sensors/groups")
            if response.status_code == 200:
                groups = response.json()
                light_group = groups.get('groups', {}).get('light', {})
                print(f"✅ Light group: {light_group.get('status')} - {light_group.get('status_text')}")
                print(f"Light sensors: {light_group.get('count', 0)}")
            else:
                print(f"❌ Sensor groups failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ System integration test failed: {e}")
        
        # 6. Final Summary
        print("\n" + "=" * 70)
        print("BH1750 API Integration Test Summary")
        print("=" * 70)
        
        if self.test_sensor:
            print(f"✅ Test completed with sensor: {self.test_sensor['sensor_id']}")
            print(f"Location: {self.test_sensor['location']}")
            print(f"Address: {self.test_sensor['address']}")
            print(f"Status: {self.test_sensor['status']}")
            print("\n🔧 Next steps:")
            print("1. Update BH1750SensorManager.js to use real API endpoints")
            print("2. Replace simulation data with API calls")
            print("3. Test complete frontend-backend integration")
        else:
            print("❌ No BH1750 sensors found")
            print("\n🔧 Troubleshooting:")
            print("1. Check sensor connections")
            print("2. Verify I2C bus status")
            print("3. Test with hardware scanner directly")
            print("4. Check TCA9548A multiplexer")
        
        print("=" * 70)

def main():
    """메인 테스트 실행"""
    tester = BH1750APIIntegrationTester()
    tester.test_api_endpoints()

if __name__ == "__main__":
    main()