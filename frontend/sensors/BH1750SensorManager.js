/**
 * BH1750 센서 관리자
 * ===================
 * BH1750 조도 센서의 발견, 폴링, 데이터 처리를 담당
 */

class BH1750SensorManager {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.sensors = [];
        this.pollingIntervals = [];
        this.chartHandler = null; // BH1750ChartHandler 인스턴스
        this.latestData = []; // 각 센서의 최신 데이터 저장
        
        // BH1750SensorManager 초기화 완료
    }
    
    // 차트 핸들러 설정
    setChartHandler(chartHandler) {
        this.chartHandler = chartHandler;
        // BH1750 차트 핸들러 연결됨
    }
    
    // BH1750 센서 그룹에 센서 추가
    addSensorToGroup(sensorData, sensorId) {
        // BH1750 센서 발견
        
        const dashboard = this.dashboard;
        
        if (!dashboard.sensorGroups['light']) {
            console.warn('⚠️ light 그룹이 존재하지 않음');
            return;
        }

        // sensors가 객체인 경우 bh1750 배열에 추가
        if (!dashboard.sensorGroups['light'].sensors.bh1750) {
            dashboard.sensorGroups['light'].sensors.bh1750 = [];
        }

        // BH1750 센서 데이터 준비
        const sensorInfo = {
            sensor_id: sensorId,
            sensorId: sensorId,
            sensor_type: 'BH1750',
            bus: sensorData.bus,
            mux_channel: sensorData.mux_channel,
            address: sensorData.address || 0x23 // BH1750 기본 주소
        };

        dashboard.sensorGroups['light'].sensors.bh1750.push(sensorInfo);
        dashboard.sensorGroups['light'].totalSensors = dashboard.sensorGroups['light'].sensors.bh1750.length;

        // BH1750 센서 그룹에 추가됨

        // 센서 개수 업데이트
        this.updateSensorCount();
        
        // BH1750 센서 추가 완료
    }

    // 센서 개수 업데이트
    updateSensorCount() {
        const summaryElement = document.querySelector('#light-group-summary');
        if (summaryElement) {
            const sensorCount = this.dashboard.sensorGroups['light']?.sensors?.bh1750?.length || 0;
            summaryElement.textContent = `BH1750×${sensorCount}`;
        }
    }
    
    // 감지된 BH1750 센서에 대해 폴링 시작
    async startPollingForDiscoveredSensors() {
        try {
            console.log('🔍 BH1750 센서 검색 시작');
            
            // 센서 그룹에서 BH1750 센서 찾기
            const response = await fetch('/api/sensors/groups');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const groupsData = await response.json();
            // 센서 그룹 데이터 수신
            
            // light 그룹에서 BH1750 센서 찾기
            const lightGroup = groupsData.groups && groupsData.groups['light'];
            if (lightGroup && lightGroup.sensors && lightGroup.sensors.length > 0) {
                // BH1750 센서만 필터링
                const bh1750Sensors = lightGroup.sensors.filter(sensor => 
                    sensor.sensor_type === 'BH1750'
                );
                console.log(`✅ BH1750 센서 ${bh1750Sensors.length}개 발견`);
                
                if (bh1750Sensors.length > 0) {
                    console.log(`🚀 BH1750 센서 ${bh1750Sensors.length}개 폴링 시작`);
                    
                    // 모든 BH1750 센서에 대해 폴링 시작
                    bh1750Sensors.forEach((sensor, index) => {
                        const sensorInfo = {
                            bus: sensor.bus,
                            mux_channel: sensor.mux_channel
                        };
                        
                        const sensorId = `bh1750_${sensor.bus}_${sensor.mux_channel}`;
                        // BH1750 센서 폴링 시작
                        
                        // 각 센서마다 고유 인덱스로 폴링 시작
                        this.startDataPolling(sensorId, sensorInfo, index);
                    });
                    
                    // BH1750 상태 위젯 설정 (전체 센서 개수)
                    this.initializeStatusWidgets(bh1750Sensors.length);
                    
                    // 차트 초기화
                    setTimeout(() => {
                        if (this.chartHandler) {
                            this.chartHandler.initializeCharts(bh1750Sensors);
                        }
                    }, 2000); // 2초 후 차트 초기화
                } else {
                    console.warn(`⚠️ BH1750 센서를 찾을 수 없음`);
                }
                
            } else {
                console.warn('⚠️ light 그룹에서 BH1750 센서를 찾을 수 없음');
            }
            
        } catch (error) {
            console.error('❌ BH1750 센서 검색 실패:', error);
        }
    }

    // 상태 위젯 초기화
    initializeStatusWidgets(sensorCount) {
        // BH1750 상태 위젯 초기화
        
        // 헤더 상태 업데이트 (light-group-status)
        const headerStatusElement = document.getElementById('light-group-status');
        if (headerStatusElement) {
            headerStatusElement.textContent = `${sensorCount}개 연결됨`;
            headerStatusElement.className = 'sensor-group-status online';
        }
        
        // 위젯 영역 상태 업데이트 (light-status)
        const statusElement = document.getElementById('light-status');
        if (statusElement) {
            statusElement.textContent = `${sensorCount}/${sensorCount} 센서`;
        }
        
        // 초기 테스트 데이터 설정 (API 폴링 비활성화 중)
        this.setInitialTestData();
        
        console.log(`✅ BH1750 상태 설정: ${sensorCount}개 연결됨`);
    }
    
    // 초기 테스트 데이터 설정
    setInitialTestData() {
        // 조도 위젯 초기값 설정
        const lightValueElement = document.getElementById('light-average');
        if (lightValueElement) {
            lightValueElement.textContent = `-- lux`;
        }
        
        // 조도 범위 위젯 초기값 설정
        const lightRangeElement = document.getElementById('light-range');
        if (lightRangeElement) {
            lightRangeElement.textContent = `-- ~ -- lux`;
        }
        
        console.log('✅ BH1750 초기 테스트 데이터 설정 완료');
    }

    // 데이터 폴링 시작
    startDataPolling(sensorId, sensor, sensorIndex) {
        // BH1750 데이터 폴링 시작
        
        // 즉시 한 번 실행
        this.fetchSensorData(sensor, sensorId, sensorIndex);
        
        // 주기적 업데이트 설정
        const intervalId = setInterval(() => {
            this.fetchSensorData(sensor, sensorId, sensorIndex);
        }, this.dashboard.config.updateInterval);
        
        // 인터벌 ID 저장
        this.pollingIntervals.push(intervalId);
        
        // BH1750 폴링 설정 완료
    }

    // 센서 데이터 가져오기
    async fetchSensorData(sensor, sensorId, sensorIndex) {
        const apiUrl = `/api/sensors/bh1750/${sensor.bus}/${sensor.mux_channel}`;
        
        try {
            const response = await fetch(apiUrl);
            const result = await response.json();
            
            if (result.success && result.data) {
                const light = result.data.light;
                const timestamp = Date.now() / 1000;
                
                // BH1750 데이터 수신
                
                // 차트 핸들러를 통한 직접 차트 업데이트 (에러 처리 추가)
                if (this.chartHandler && this.chartHandler.isReady()) {
                    try {
                        this.chartHandler.updateChartsWithRealtimeData(sensorId, {
                            light: light
                        }, timestamp);
                    } catch (chartError) {
                        console.warn(`⚠️ BH1750 차트 업데이트 에러: ${chartError.message}`);
                        // 에러 발생 시 버퍼링으로 전환
                        this.chartHandler.bufferData(sensorId, {
                            light: light
                        }, timestamp);
                    }
                } else {
                    // BH1750ChartHandler 준비되지 않음, 데이터 버퍼링
                    // 차트 핸들러가 준비되지 않은 경우 데이터를 버퍼에 저장
                    if (this.chartHandler) {
                        this.chartHandler.bufferData(sensorId, {
                            light: light
                        }, timestamp);
                    }
                }
                
                // 위젯 업데이트 (모든 센서 데이터 수집 후 평균 계산)
                this.updateWidgets(light, sensorIndex);
                
            } else {
                console.warn(`⚠️ BH1750 API 오류 [${sensorIndex}]:`, result.message || result.error);
            }
        } catch (error) {
            console.error(`❌ BH1750 데이터 수집 실패 [${sensorIndex}]:`, error);
        }
    }
    
    // 위젯 업데이트 (평균값 계산)
    updateWidgets(light, sensorIndex) {
        // 최신 데이터 배열 업데이트
        this.latestData[sensorIndex] = { light };
        
        // 유효한 데이터만 필터링
        const validData = this.latestData.filter(data => data !== undefined);
        
        if (validData.length === 0) {
            return;
        }
        
        // 평균값 계산
        const avgLight = validData.reduce((sum, data) => sum + data.light, 0) / validData.length;
        
        // 최소/최대값 계산
        const lightValues = validData.map(data => data.light);
        const minLight = Math.min(...lightValues);
        const maxLight = Math.max(...lightValues);
        
        // 조도 위젯 업데이트
        const lightValueElement = document.getElementById('light-average');
        if (lightValueElement) {
            lightValueElement.textContent = `${Math.round(avgLight)} lux`;
        }
        
        // 조도 범위 위젯 업데이트
        const lightRangeElement = document.getElementById('light-range');
        if (lightRangeElement) {
            lightRangeElement.textContent = `${Math.round(minLight)} ~ ${Math.round(maxLight)} lux`;
        }
        
        // BH1750 위젯 업데이트 완료
    }

    // WebSocket 데이터 처리에서 BH1750 감지
    processSensorFromWebSocket(sensor) {
        // BH1750 조도 센서 처리
        if (sensor.sensor_type === 'BH1750') {
            console.log('📊 BH1750 조도 센서 발견:', sensor);
            const sensorId = `bh1750_${sensor.bus}_${sensor.mux_channel}`;
            this.addSensorToGroup(sensor, sensorId);
            
            // 센서 발견 시 위젯 초기화
            this.initializeStatusWidgets(1);
        }
    }

    // 실시간 데이터 처리 (WebSocket에서 호출)
    updateData(sensorData) {
        if (sensorData.sensor_type === 'BH1750' && sensorData.values) {
            const values = sensorData.values;
            
            // 연결 상태를 활성중으로 업데이트
            this.setStatusConnected(sensorData);
            
            // 조도 값 처리
            if (values.light !== undefined) {
                const sensorId = `bh1750_${sensorData.bus}_${sensorData.mux_channel}`;
                const sensorIndex = this.findSensorIndex(sensorId);
                
                if (sensorIndex !== -1) {
                    // 위젯 업데이트
                    this.updateWidgets(values.light, sensorIndex);
                    
                    // 차트 업데이트
                    if (this.chartHandler) {
                        this.chartHandler.updateChartsWithRealtimeData(sensorId, values, Date.now() / 1000);
                    }
                }
            }
            
            // BH1750 데이터 처리 완료
        }
    }
    
    // 센서 인덱스 찾기
    findSensorIndex(sensorId) {
        const parts = sensorId.split('_');
        if (parts.length < 3) return -1;
        
        const bus = parseInt(parts[1]);
        const channel = parseInt(parts[2]);
        
        const sensors = this.dashboard.sensorGroups['light']?.sensors?.bh1750 || [];
        return sensors.findIndex(sensor => 
            sensor.bus === bus && sensor.mux_channel === channel
        );
    }
    
    // BH1750 연결 활성 상태 설정 (데이터 수신 시)
    setStatusConnected(sensorData) {
        const statusElement = document.getElementById('light-group-status');
        if (statusElement) {
            const sensorCount = this.dashboard.sensorGroups['light']?.sensors?.bh1750?.length || 1;
            statusElement.textContent = `${sensorCount}개 연결됨`;
            statusElement.className = 'sensor-group-status online';
            console.log('✅ BH1750 상태를 연결 활성중으로 설정 (데이터 수신)');
        }
    }

    // 폴링 중지
    stopPolling() {
        this.pollingIntervals.forEach(intervalId => {
            clearInterval(intervalId);
        });
        this.pollingIntervals = [];
        // BH1750 폴링 중지됨
    }

    // 센서 목록 반환
    getSensors() {
        return this.dashboard.sensorGroups['light']?.sensors?.bh1750 || [];
    }
}

// 전역으로 내보내기
window.BH1750SensorManager = BH1750SensorManager;