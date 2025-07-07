/**
 * SPS30 센서 관리자
 * ==================
 * SPS30 미세먼지 센서의 발견, 상태 관리, 데이터 처리를 담당
 */

class SPS30SensorManager {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.sensor = null;
        this.chartHandler = null; // SPS30ChartHandler 인스턴스
        
        // SPS30SensorManager 초기화 완료
    }
    
    // 차트 핸들러 설정
    setChartHandler(chartHandler) {
        this.chartHandler = chartHandler;
        // SPS30 차트 핸들러 연결됨
    }
    
    // SPS30 센서 검색 및 상태 업데이트
    async processSensorData(apiResponse) {
        try {
            console.log('🌪️ SPS30 센서 데이터 처리 시작:', apiResponse);
            
            const groups = apiResponse.groups || apiResponse;
            console.log('📊 사용 가능한 센서 그룹들:', Object.keys(groups));
            
            // 모든 그룹에서 SPS30 센서 찾기
            let sps30Sensor = null;
            for (const [groupName, group] of Object.entries(groups)) {
                if (group && group.sensors && Array.isArray(group.sensors)) {
                    console.log(`🔍 ${groupName} 그룹에서 센서 검색:`, group.sensors.length, '개');
                    
                    const foundSPS30 = group.sensors.find(sensor => {
                        console.log(`   센서 확인: ${sensor.sensor_type}, 인터페이스: ${sensor.interface}`);
                        return sensor.sensor_type === 'SPS30' || 
                               (sensor.interface && sensor.interface.includes('UART'));
                    });
                    
                    if (foundSPS30) {
                        sps30Sensor = foundSPS30;
                        console.log(`✅ SPS30 센서 발견 (${groupName} 그룹):`, foundSPS30);
                        break;
                    }
                }
            }
            
            if (sps30Sensor) {
                this.sensor = sps30Sensor;
                this.updateStatus(sps30Sensor);
            } else {
                console.log('⚠️ 모든 그룹에서 SPS30 센서를 찾을 수 없음');
                this.setStatusDisconnected();
            }
            
        } catch (error) {
            console.error('❌ SPS30 센서 데이터 처리 실패:', error);
            this.setStatusDisconnected();
        }
    }
    
    // SPS30 센서 상태 업데이트
    updateStatus(sensor) {
        console.log('📊 SPS30 센서 상태 업데이트:', sensor);
        
        const statusElement = document.getElementById('sps30-status');
        if (statusElement) {
            // 더 유연한 연결 상태 판단
            const isConnected = sensor.status === 'connected' || 
                              sensor.interface === 'UART' || 
                              sensor.sensor_type === 'SPS30' ||
                              (sensor.interface && sensor.interface.includes('UART'));
            
            if (isConnected) {
                statusElement.textContent = '연결 활성중';
                statusElement.className = 'sensor-group-status online';
                console.log('✅ SPS30 상태 업데이트: 연결 활성중', sensor);
            } else {
                statusElement.textContent = '연결 확인 중...';
                statusElement.className = 'sensor-group-status offline';
                console.log('⚠️ SPS30 상태 업데이트: 연결 확인 중', sensor);
            }
        } else {
            console.warn('⚠️ sps30-status 엘리먼트를 찾을 수 없음');
        }

        const modelElement = document.getElementById('sps30-model');
        if (modelElement) {
            const serialDisplay = sensor.serial_number ? 
                sensor.serial_number.substring(0, 8) : 'UART';
            modelElement.textContent = `SPS30 ${serialDisplay}`;
            console.log(`✅ SPS30 모델 정보 업데이트: SPS30 ${serialDisplay}`);
        } else {
            console.warn('⚠️ sps30-model 엘리먼트를 찾을 수 없음');
        }
    }
    
    // SPS30 연결 해제 상태 설정
    setStatusDisconnected() {
        const statusElement = document.getElementById('sps30-status');
        if (statusElement) {
            statusElement.textContent = '연결 확인 중...';
            statusElement.className = 'sensor-group-status offline';
            console.log('⚠️ SPS30 상태를 연결 확인 중으로 설정');
        }
        
        const modelElement = document.getElementById('sps30-model');
        if (modelElement) {
            modelElement.textContent = 'SPS30 UART';
            console.log('📊 SPS30 모델 정보를 기본값으로 설정');
        }
    }
    
    // SPS30 연결 활성 상태 설정 (데이터 수신 시)
    setStatusConnected(sensorData) {
        const statusElement = document.getElementById('sps30-status');
        if (statusElement) {
            statusElement.textContent = '연결 활성중';
            statusElement.className = 'sensor-group-status online';
            console.log('✅ SPS30 상태를 연결 활성중으로 설정 (데이터 수신)');
        }
        
        const modelElement = document.getElementById('sps30-model');
        if (modelElement) {
            const serialDisplay = sensorData.serial_number ? 
                sensorData.serial_number.substring(0, 8) : 'UART';
            modelElement.textContent = `SPS30 ${serialDisplay}`;
            console.log(`✅ SPS30 모델 정보 업데이트: SPS30 ${serialDisplay}`);
        }
    }
    
    // SPS30 실시간 데이터 처리
    updateData(sensorData) {
        if (sensorData.sensor_type === 'SPS30' && sensorData.values) {
            const values = sensorData.values;
            
            // 데이터가 들어오면 연결 상태를 활성중으로 업데이트
            this.setStatusConnected(sensorData);
            
            // PM2.5 값 추출 및 업데이트
            if (values.pm25 !== undefined) {
                const pm25Element = document.getElementById('pm25-value');
                if (pm25Element) {
                    pm25Element.textContent = `${values.pm25.toFixed(1)} μg/m³`;
                }
                
                // PM2.5 공기질 등급 판정
                const pm25Level = this.getAirQualityLevel(values.pm25);
                const pm25LevelElement = document.getElementById('pm25-level');
                if (pm25LevelElement) {
                    pm25LevelElement.textContent = pm25Level.text;
                    pm25LevelElement.className = `summary-range ${pm25Level.class}`;
                }
            }
            
            // PM10 값 추출 및 업데이트
            if (values.pm10 !== undefined) {
                const pm10Element = document.getElementById('pm10-value');
                if (pm10Element) {
                    pm10Element.textContent = `${values.pm10.toFixed(1)} μg/m³`;
                }
                
                // PM10 공기질 등급 판정
                const pm10Level = this.getAirQualityLevel(values.pm10, 'pm10');
                const pm10LevelElement = document.getElementById('pm10-level');
                if (pm10LevelElement) {
                    pm10LevelElement.textContent = pm10Level.text;
                    pm10LevelElement.className = `summary-range ${pm10Level.class}`;
                }
            }
            
            // 전체 공기질 등급 (PM2.5 기준)
            if (values.pm25 !== undefined) {
                const overallLevel = this.getAirQualityLevel(values.pm25);
                const gradeElement = document.getElementById('air-quality-grade');
                const descElement = document.getElementById('air-quality-desc');
                
                if (gradeElement) {
                    gradeElement.textContent = overallLevel.grade;
                }
                if (descElement) {
                    descElement.textContent = overallLevel.description;
                    descElement.className = `summary-range ${overallLevel.class}`;
                }
            }

            // 차트 업데이트
            if (this.chartHandler) {
                this.chartHandler.updateChart(values);
            }
            
            // SPS30 메인 위젯 업데이트 완료
        }
    }
    
    // 공기질 등급 판정 함수
    getAirQualityLevel(value, type = 'pm25') {
        let thresholds, grades, descriptions, classes;
        
        if (type === 'pm10') {
            thresholds = [30, 80, 150, 300];
            grades = ['좋음', '보통', '나쁨', '매우나쁨', '위험'];
            descriptions = ['깨끗함', '무난함', '민감군 주의', '외출 자제', '외출 금지'];
            classes = ['good', 'moderate', 'bad', 'very-bad', 'dangerous'];
        } else {
            // PM2.5 기준
            thresholds = [15, 35, 75, 150];
            grades = ['좋음', '보통', '나쁨', '매우나쁨', '위험'];
            descriptions = ['깨끗함', '무난함', '민감군 주의', '외출 자제', '외출 금지'];
            classes = ['good', 'moderate', 'bad', 'very-bad', 'dangerous'];
        }
        
        let index = 0;
        for (let i = 0; i < thresholds.length; i++) {
            if (value <= thresholds[i]) {
                index = i;
                break;
            }
            index = thresholds.length;
        }
        
        return {
            grade: grades[index],
            text: grades[index],
            description: descriptions[index],
            class: classes[index]
        };
    }
    
    // WebSocket 데이터 처리에서 SPS30 감지
    processSensorFromWebSocket(sensor) {
        // SPS30 공기질 센서 처리
        if (sensor.sensor_type === 'SPS30' && sensor.interface === 'UART') {
            console.log('📊 SPS30 공기질 센서 발견:', sensor);
            this.updateStatus(sensor);
        }
    }
    
    // 센서 정보 반환
    getSensor() {
        return this.sensor;
    }
}

// 전역으로 내보내기
window.SPS30SensorManager = SPS30SensorManager;