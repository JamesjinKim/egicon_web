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
        
        // BH1750 센서 배열 초기화 (새로고침 시 중복 방지)
        if (this.dashboard.sensorGroups && this.dashboard.sensorGroups['light']) {
            this.dashboard.sensorGroups['light'].sensors.bh1750 = [];
            console.log(`🔄 BH1750 센서 배열 초기화됨 (새로고침 대응)`);
        }
        
        // BH1750SensorManager 초기화 완료
    }
    
    // 차트 핸들러 설정
    setChartHandler(chartHandler) {
        this.chartHandler = chartHandler;
        // BH1750 차트 핸들러 연결됨
    }
    
    // BH1750 센서 그룹에 센서 추가
    addSensorToGroup(sensorData, sensorId) {
        console.log(`🔍 addSensorToGroup 호출됨: ${sensorId}`, sensorData);
        console.log(`🔍 호출 스택:`, new Error().stack);
        
        const dashboard = this.dashboard;
        
        if (!dashboard.sensorGroups['light']) {
            console.warn('⚠️ light 그룹이 존재하지 않음');
            return;
        }

        // sensors가 객체인 경우 bh1750 배열에 추가
        if (!dashboard.sensorGroups['light'].sensors.bh1750) {
            dashboard.sensorGroups['light'].sensors.bh1750 = [];
        }
        
        // 현재 센서 목록 상태 로깅 및 정리
        console.log(`📊 센서 추가 전 현재 bh1750 센서 목록 (${dashboard.sensorGroups['light'].sensors.bh1750.length}개):`);
        dashboard.sensorGroups['light'].sensors.bh1750.forEach((sensor, index) => {
            console.log(`  ${index}: `, {
                id: sensor.sensorId || sensor.sensor_id,
                bus: sensor.bus,
                channel: sensor.mux_channel,
                type: typeof sensor,
                fullData: sensor
            });
        });
        
        // 잘못된 형태(문자열 등)의 센서 데이터 제거
        const validSensors = dashboard.sensorGroups['light'].sensors.bh1750.filter(sensor => 
            typeof sensor === 'object' && sensor !== null && typeof sensor !== 'string'
        );
        
        if (validSensors.length !== dashboard.sensorGroups['light'].sensors.bh1750.length) {
            console.log(`🧹 잘못된 센서 데이터 정리: ${dashboard.sensorGroups['light'].sensors.bh1750.length}개 → ${validSensors.length}개`);
            dashboard.sensorGroups['light'].sensors.bh1750 = validSensors;
        }

        // 중복 센서 체크 (sensorId와 bus/channel 조합 모두 확인)
        const existingSensorById = dashboard.sensorGroups['light'].sensors.bh1750.find(sensor => 
            sensor.sensorId === sensorId || sensor.sensor_id === sensorId
        );
        const existingSensorByLocation = dashboard.sensorGroups['light'].sensors.bh1750.find(sensor => 
            sensor.bus === sensorData.bus && sensor.mux_channel === sensorData.mux_channel
        );
        
        if (existingSensorById || existingSensorByLocation) {
            console.log(`⚠️ BH1750 센서 중복 감지, 추가하지 않음:`);
            console.log(`  - 센서 ID 중복: ${!!existingSensorById}, ${sensorId}`);
            console.log(`  - 위치 중복: ${!!existingSensorByLocation}, Bus ${sensorData.bus}, Channel ${sensorData.mux_channel}`);
            console.log(`  - 현재 센서 목록:`, dashboard.sensorGroups['light'].sensors.bh1750.map(s => ({id: s.sensorId, bus: s.bus, channel: s.mux_channel})));
            return; // 중복 센서는 추가하지 않음
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
        
        console.log(`✅ BH1750 센서 추가: Bus ${sensorData.bus}, Channel ${sensorData.mux_channel} (총 ${dashboard.sensorGroups['light'].sensors.bh1750.length}개)`);

        // BH1750 센서 그룹에 추가됨

        // 센서 개수 업데이트는 지연 실행하여 최종 값으로 표시
        setTimeout(() => {
            this.updateSensorCount();
            console.log(`🔄 BH1750 센서 개수 최종 업데이트: ${dashboard.sensorGroups['light'].sensors.bh1750.length}개`);
        }, 2000); // 2초 후 최종 업데이트
        
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
        console.log('🔍 BH1750 위젯 요소 디버깅 시작');
        
        // 조도 센서 그룹 전체 확인
        const lightGroup = document.querySelector('[data-group="light"]');
        console.log('🔍 light 그룹 요소:', lightGroup);
        if (lightGroup) {
            // 그룹이 숨겨져 있다면 표시
            lightGroup.style.display = 'block';
            console.log('✅ light 그룹 표시 강제 설정');
        }
        
        // 조도 위젯 초기값 설정
        const lightValueElement = document.getElementById('light-average');
        console.log('🔍 light-average 요소:', lightValueElement);
        if (lightValueElement) {
            lightValueElement.textContent = `연결됨 lux`;
            console.log('✅ light-average 업데이트:', lightValueElement.textContent);
        } else {
            console.error('❌ light-average 요소를 찾을 수 없음');
            // light-average 요소가 없다면 동적으로 생성
            this.createMissingLightElements();
        }
        
        // 조도 범위 위젯 초기값 설정
        const lightRangeElement = document.getElementById('light-range');
        console.log('🔍 light-range 요소:', lightRangeElement);
        if (lightRangeElement) {
            lightRangeElement.textContent = `센서 대기 중`;
            console.log('✅ light-range 업데이트:', lightRangeElement.textContent);
        } else {
            console.error('❌ light-range 요소를 찾을 수 없음');
        }
        
        // 모든 light 관련 요소 스캔
        const allLightElements = document.querySelectorAll('[id*="light"]');
        console.log('🔍 모든 light 관련 요소들:', allLightElements);
        allLightElements.forEach((element, index) => {
            console.log(`  ${index}: ID=${element.id}, 내용="${element.textContent}", 표시상태=${getComputedStyle(element).display}`);
        });
        
        // 최종 센서 개수 확인 및 업데이트 (3초 후)
        setTimeout(() => {
            const finalCount = this.dashboard.sensorGroups['light']?.sensors?.bh1750?.length || 0;
            console.log(`🎯 BH1750 최종 센서 개수 확인: ${finalCount}개`);
            this.updateSensorCount();
        }, 3000);
        
        console.log('✅ BH1750 초기 테스트 데이터 설정 완료');
    }
    
    // 누락된 light 요소들 생성
    createMissingLightElements() {
        console.log('🔧 누락된 light 요소들 동적 생성 시도');
        
        const lightGroup = document.querySelector('[data-group="light"]');
        if (!lightGroup) {
            console.error('❌ light 그룹 자체를 찾을 수 없음');
            return;
        }
        
        // summary-widgets-container 찾기
        const summaryContainer = lightGroup.querySelector('.summary-widgets-container');
        if (summaryContainer) {
            console.log('✅ summary-widgets-container 발견');
            
            // light-average 요소가 없으면 생성
            if (!document.getElementById('light-average')) {
                const lightWidget = summaryContainer.querySelector('.summary-widget.light');
                if (lightWidget) {
                    const summaryValue = lightWidget.querySelector('.summary-value');
                    if (summaryValue && !summaryValue.id) {
                        summaryValue.id = 'light-average';
                        summaryValue.textContent = '동적생성 lux';
                        console.log('✅ light-average 요소 동적 생성 완료');
                    }
                }
            }
        }
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
            
            // 센서 발견 시 위젯 초기화 (지연 실행)
            console.log('⏱️ BH1750 위젯 초기화 지연 실행 (DOM 준비 대기)');
            setTimeout(() => {
                this.initializeStatusWidgets(1);
                
                // 차트 초기화 직접 호출 (API 폴링 없이 테스트)
                console.log('📊 BH1750 차트 초기화 직접 호출');
                console.log('📊 차트 핸들러 상태:', {
                    exists: !!this.chartHandler,
                    isReady: this.chartHandler ? this.chartHandler.isReady() : false
                });
                
                if (this.chartHandler) {
                    // 가상의 센서 정보로 차트 초기화
                    const testSensors = [{
                        bus: sensor.bus,
                        mux_channel: sensor.mux_channel,
                        sensor_type: 'BH1750'
                    }];
                    console.log('📊 테스트 센서 정보:', testSensors);
                    
                    // DOM 요소 확인
                    const chartCanvas = document.getElementById('light-multi-chart');
                    console.log('📊 차트 캔버스 요소 확인:', {
                        exists: !!chartCanvas,
                        id: chartCanvas ? chartCanvas.id : 'null',
                        display: chartCanvas ? getComputedStyle(chartCanvas).display : 'null'
                    });
                    
                    try {
                        this.chartHandler.initializeCharts(testSensors);
                        console.log('✅ BH1750 차트 초기화 호출 완료');
                    } catch (initError) {
                        console.error('❌ BH1750 차트 초기화 실패:', initError);
                    }
                } else {
                    console.error('❌ BH1750 차트 핸들러가 없음');
                }
                
                // 추가로 5초 후 테스트 데이터 시뮬레이션
                setTimeout(() => {
                    console.log('🧪 BH1750 테스트 데이터 시뮬레이션');
                    this.updateWidgets(350.5, 0); // 350.5 lux 테스트 데이터
                    
                    // 차트에도 테스트 데이터 추가
                    if (this.chartHandler && this.chartHandler.isReady()) {
                        const sensorId = `bh1750_${sensor.bus}_${sensor.mux_channel}`;
                        console.log('📊 BH1750 차트 테스트 데이터 추가:', sensorId);
                        this.chartHandler.updateChartsWithRealtimeData(sensorId, {
                            light: 350.5
                        }, Date.now() / 1000);
                    }
                }, 5000);
            }, 1000); // 1초 지연으로 DOM 완전 로딩 대기
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