/**
 * SDP810 센서 관리자
 * ===================
 * SDP810 차압센서의 발견, 폴링, 데이터 처리를 담당
 * CRC 검증 실패 시 데이터 skip 처리
 */

class SDP810SensorManager {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.sensors = [];
        this.pollingIntervals = [];
        this.chartHandler = null; // SDP810ChartHandler 인스턴스
        this.latestData = []; // 각 센서의 최신 데이터 저장
        this.skipCount = 0; // CRC 실패로 skip한 데이터 개수
        
        // SDP810 센서 배열 초기화 (새로고침 시 중복 방지)
        if (this.dashboard.sensorGroups && this.dashboard.sensorGroups['pressure']) {
            this.dashboard.sensorGroups['pressure'].sensors.sdp810 = [];
            console.log(`🔄 SDP810 센서 배열 초기화됨 (새로고침 대응)`);
        }
        
        // SDP810SensorManager 초기화 완료
    }
    
    // 차트 핸들러 설정
    setChartHandler(chartHandler) {
        this.chartHandler = chartHandler;
        // SDP810 차트 핸들러 연결됨
    }
    
    // SDP810 센서 그룹에 센서 추가
    addSensorToGroup(sensorData, sensorId) {
        console.log(`🔍 addSensorToGroup 호출됨: ${sensorId}`, sensorData);
        
        const dashboard = this.dashboard;
        
        if (!dashboard.sensorGroups['pressure']) {
            console.warn('⚠️ pressure 그룹이 존재하지 않음');
            return;
        }

        // sensors가 객체인 경우 sdp810 배열에 추가
        if (!dashboard.sensorGroups['pressure'].sensors.sdp810) {
            dashboard.sensorGroups['pressure'].sensors.sdp810 = [];
        }
        
        // 중복 센서 체크 (sensorId와 bus/channel 조합 모두 확인)
        const existingSensorById = dashboard.sensorGroups['pressure'].sensors.sdp810.find(sensor => 
            sensor.sensorId === sensorId || sensor.sensor_id === sensorId
        );
        const existingSensorByLocation = dashboard.sensorGroups['pressure'].sensors.sdp810.find(sensor => 
            sensor.bus === sensorData.bus && sensor.mux_channel === sensorData.mux_channel
        );
        
        if (existingSensorById || existingSensorByLocation) {
            console.log(`⚠️ SDP810 센서 중복 감지, 추가하지 않음:`);
            console.log(`  - 센서 ID 중복: ${!!existingSensorById}, ${sensorId}`);
            console.log(`  - 위치 중복: ${!!existingSensorByLocation}, Bus ${sensorData.bus}, Channel ${sensorData.mux_channel}`);
            return; // 중복 센서는 추가하지 않음
        }

        // SDP810 센서 데이터 준비
        const sensorInfo = {
            sensor_id: sensorId,
            sensorId: sensorId,
            sensor_type: 'SDP810',
            bus: sensorData.bus,
            mux_channel: sensorData.mux_channel,
            address: sensorData.address || 0x25 // SDP810 기본 주소
        };

        dashboard.sensorGroups['pressure'].sensors.sdp810.push(sensorInfo);
        dashboard.sensorGroups['pressure'].totalSensors = dashboard.sensorGroups['pressure'].sensors.sdp810.length;
        
        console.log(`✅ SDP810 센서 추가: Bus ${sensorData.bus}, Channel ${sensorData.mux_channel} (총 ${dashboard.sensorGroups['pressure'].sensors.sdp810.length}개)`);

        // 센서 개수 업데이트는 지연 실행하여 최종 값으로 표시
        setTimeout(() => {
            this.updateSensorCount();
            console.log(`🔄 SDP810 센서 개수 최종 업데이트: ${dashboard.sensorGroups['pressure'].sensors.sdp810.length}개`);
        }, 2000); // 2초 후 최종 업데이트
    }

    // 센서 개수 업데이트
    updateSensorCount() {
        const summaryElement = document.querySelector('#pressure-group-summary');
        if (summaryElement) {
            const sensorCount = this.dashboard.sensorGroups['pressure']?.sensors?.sdp810?.length || 0;
            summaryElement.textContent = `SDP810×${sensorCount}`;
        }
    }
    
    // 감지된 SDP810 센서에 대해 폴링 시작
    async startPollingForDiscoveredSensors() {
        try {
            console.log('🔍 SDP810 센서 검색 시작');
            
            // 센서 그룹에서 SDP810 센서 찾기
            const response = await fetch('/api/sensors/groups');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const groupsData = await response.json();
            
            // pressure 그룹에서 SDP810 센서 찾기 (API에서 발견되지 않으면 하드코딩된 센서 사용)
            const pressureGroup = groupsData.groups && groupsData.groups['pressure'];
            let sdp810Sensors = [];
            
            if (pressureGroup && pressureGroup.sensors && pressureGroup.sensors.length > 0) {
                // SDP810 센서만 필터링
                sdp810Sensors = pressureGroup.sensors.filter(sensor => 
                    sensor.sensor_type === 'SDP810'
                );
                console.log(`✅ API에서 SDP810 센서 ${sdp810Sensors.length}개 발견`);
            }
            
            // API에서 SDP810이 발견되지 않으면 하드코딩된 센서 정보 사용 (Bus 1, Channel 4)
            if (sdp810Sensors.length === 0) {
                console.log(`⚠️ API에서 SDP810 센서를 찾을 수 없음, 하드코딩된 센서 정보 사용`);
                sdp810Sensors = [{
                    bus: 1,
                    mux_channel: 4,
                    address: '0x25',
                    sensor_name: 'SDP810',
                    sensor_type: 'SDP810',
                    status: 'connected'
                }];
                console.log(`🔧 하드코딩된 SDP810 센서 1개 추가됨: Bus 1, Channel 4`);
            }
            
            if (sdp810Sensors.length > 0) {
                console.log(`🚀 SDP810 센서 ${sdp810Sensors.length}개 폴링 시작`);
                    
                    // 모든 SDP810 센서에 대해 폴링 시작
                    sdp810Sensors.forEach((sensor, index) => {
                        const sensorInfo = {
                            bus: sensor.bus,
                            mux_channel: sensor.mux_channel
                        };
                        
                        const sensorId = `sdp810_${sensor.bus}_${sensor.mux_channel}`;
                        
                        // 각 센서마다 고유 인덱스로 폴링 시작
                        this.startDataPolling(sensorId, sensorInfo, index);
                    });
                    
                    // SDP810 상태 위젯 설정 (전체 센서 개수)
                    this.initializeStatusWidgets(sdp810Sensors.length);
                    
                    // 센서 발견 후 연결 상태로 업데이트
                    setTimeout(() => {
                        this.updateStatusToConnected(sdp810Sensors.length);
                    }, 1000);
                    
                    // 차트 초기화
                    setTimeout(() => {
                        if (this.chartHandler) {
                            this.chartHandler.initializeCharts(sdp810Sensors);
                        }
                    }, 2000); // 2초 후 차트 초기화
                } else {
                    console.warn(`⚠️ SDP810 센서를 찾을 수 없음`);
                    // 센서가 없어도 기본 상태 설정
                    this.initializeStatusWidgets(0);
                }
                
            } else {
                console.warn('⚠️ pressure 그룹에서 SDP810 센서를 찾을 수 없음');
                // pressure 그룹이 없어도 기본 상태 설정
                this.initializeStatusWidgets(0);
            }
            
        } catch (error) {
            console.error('❌ SDP810 센서 검색 실패:', error);
            // API 오류 시에도 기본 상태 설정
            this.initializeStatusWidgets(0);
        }
    }

    // 상태 위젯 초기화
    initializeStatusWidgets(sensorCount) {
        console.log(`🔧 SDP810 상태 위젯 초기화: ${sensorCount}개 센서`);
        
        // 헤더 상태 업데이트 (pressure-group-status)
        const headerStatusElement = document.getElementById('pressure-group-status');
        if (headerStatusElement) {
            if (sensorCount > 0) {
                headerStatusElement.textContent = `${sensorCount}개 연결됨`;
                headerStatusElement.className = 'sensor-group-status online';
            } else {
                headerStatusElement.textContent = '센서 검색 중...';
                headerStatusElement.className = 'sensor-group-status offline';
            }
            console.log(`✅ pressure-group-status 업데이트: ${headerStatusElement.textContent}`);
        } else {
            console.error('❌ pressure-group-status 요소를 찾을 수 없음');
        }
        
        // 헤더 요약 업데이트 (pressure-group-summary)
        const summaryElement = document.getElementById('pressure-group-summary');
        if (summaryElement) {
            if (sensorCount > 0) {
                summaryElement.textContent = `SDP810×${sensorCount}`;
            } else {
                summaryElement.textContent = 'SDP810 센서 검색 중';
            }
            console.log(`✅ pressure-group-summary 업데이트: ${summaryElement.textContent}`);
        } else {
            console.error('❌ pressure-group-summary 요소를 찾을 수 없음');
        }
        
        // 위젯 영역 상태 업데이트 (pressure-status)
        const statusElement = document.getElementById('pressure-status');
        if (statusElement) {
            if (sensorCount > 0) {
                statusElement.textContent = `${sensorCount}/${sensorCount} 센서`;
            } else {
                statusElement.textContent = '0/0 센서';
            }
            console.log(`✅ pressure-status 업데이트: ${statusElement.textContent}`);
        } else {
            console.error('❌ pressure-status 요소를 찾을 수 없음');
        }
        
        // 초기 테스트 데이터 설정
        this.setInitialTestData();
        
        console.log(`✅ SDP810 상태 설정: ${sensorCount}개 연결됨`);
    }
    
    // 센서 연결 상태로 업데이트
    updateStatusToConnected(sensorCount) {
        console.log(`🔗 SDP810 센서 연결 상태 업데이트: ${sensorCount}개`);
        
        // 헤더 상태를 연결됨으로 업데이트
        const headerStatusElement = document.getElementById('pressure-group-status');
        if (headerStatusElement) {
            headerStatusElement.textContent = `${sensorCount}개 연결됨`;
            headerStatusElement.className = 'sensor-group-status online';
            console.log(`✅ 헤더 상태 업데이트: ${headerStatusElement.textContent}`);
        }
        
        // 헤더 요약을 구체적으로 업데이트
        const summaryElement = document.getElementById('pressure-group-summary');
        if (summaryElement) {
            summaryElement.textContent = `SDP810 차압센서×${sensorCount}`;
            console.log(`✅ 헤더 요약 업데이트: ${summaryElement.textContent}`);
        }
    }
    
    // 초기 테스트 데이터 설정
    setInitialTestData() {
        console.log('🔍 SDP810 위젯 요소 디버깅 시작');
        
        // 차압 센서 그룹 전체 확인
        const pressureGroup = document.querySelector('[data-group="pressure"]');
        console.log('🔍 pressure 그룹 요소:', pressureGroup);
        if (pressureGroup) {
            // 그룹이 숨겨져 있다면 표시
            pressureGroup.style.display = 'block';
            console.log('✅ pressure 그룹 표시 강제 설정');
        }
        
        // 차압 위젯 초기값 설정
        const pressureValueElement = document.getElementById('differential-pressure-average');
        console.log('🔍 differential-pressure-average 요소:', pressureValueElement);
        if (pressureValueElement) {
            pressureValueElement.textContent = `연결됨 Pa`;
            console.log('✅ differential-pressure-average 업데이트:', pressureValueElement.textContent);
        } else {
            console.error('❌ differential-pressure-average 요소를 찾을 수 없음');
        }
        
        // 차압 범위 위젯 초기값 설정
        const pressureRangeElement = document.getElementById('differential-pressure-range');
        console.log('🔍 differential-pressure-range 요소:', pressureRangeElement);
        if (pressureRangeElement) {
            pressureRangeElement.textContent = `센서 대기 중`;
            console.log('✅ differential-pressure-range 업데이트:', pressureRangeElement.textContent);
        } else {
            console.error('❌ differential-pressure-range 요소를 찾을 수 없음');
        }
        
        // 최종 센서 개수 확인 및 업데이트 (3초 후)
        setTimeout(() => {
            const finalCount = this.dashboard.sensorGroups['pressure']?.sensors?.sdp810?.length || 0;
            console.log(`🎯 SDP810 최종 센서 개수 확인: ${finalCount}개`);
            this.updateSensorCount();
        }, 3000);
        
        console.log('✅ SDP810 초기 테스트 데이터 설정 완료');
    }

    // 데이터 폴링 시작
    startDataPolling(sensorId, sensor, sensorIndex) {
        // SDP810 데이터 폴링 시작
        
        // 즉시 한 번 실행
        this.fetchSensorData(sensor, sensorId, sensorIndex);
        
        // 주기적 업데이트 설정 (2초 간격)
        const intervalId = setInterval(() => {
            this.fetchSensorData(sensor, sensorId, sensorIndex);
        }, 2000); // 2초 간격
        
        // 인터벌 ID 저장
        this.pollingIntervals.push(intervalId);
        
        // SDP810 폴링 설정 완료
    }

    // 센서 데이터 가져오기 (실제 API 호출 + CRC 검증)
    async fetchSensorData(sensor, sensorId, sensorIndex) {
        const apiUrl = `/api/sensors/sdp810/${sensor.bus}/${sensor.mux_channel}`;
        
        try {
            console.log(`🔗 SDP810 API 호출 [${sensorIndex}]: ${apiUrl}`);
            
            const response = await fetch(apiUrl);
            const result = await response.json();
            
            if (result.success && result.data) {
                // ✅ API 성공 + CRC 검증 성공
                const pressure = result.data.pressure;
                const timestamp = result.data.timestamp;
                const crcValid = result.data.crc_valid;
                
                console.log(`✅ SDP810 실제 데이터 [${sensorIndex}]: ${pressure.toFixed(4)} Pa (CRC: ${crcValid ? '✅' : '❌'})`);
                
                // CRC 검증이 성공한 경우만 처리
                if (crcValid) {
                    // 차트 핸들러를 통한 직접 차트 업데이트
                    if (this.chartHandler && this.chartHandler.isReady()) {
                        try {
                            this.chartHandler.updateChartsWithRealtimeData(sensorId, {
                                pressure: pressure
                            }, Date.now() / 1000);
                            console.log(`📊 SDP810 차트 업데이트 성공 [${sensorIndex}]`);
                        } catch (chartError) {
                            console.warn(`⚠️ SDP810 차트 업데이트 에러 [${sensorIndex}]: ${chartError.message}`);
                        }
                    } else {
                        console.log(`📦 SDP810 차트 핸들러 준비 중, 데이터 버퍼링 [${sensorIndex}]`);
                        if (this.chartHandler) {
                            this.chartHandler.bufferData(sensorId, {
                                pressure: pressure
                            }, Date.now() / 1000);
                        }
                    }
                    
                    // 위젯 업데이트 (CRC 성공 데이터만)
                    this.updateWidgets(pressure, sensorIndex);
                } else {
                    // CRC 실패 시 데이터 skip
                    this.skipCount++;
                    console.warn(`⚠️ SDP810 CRC 실패로 데이터 skip [${sensorIndex}] (총 ${this.skipCount}회 skip)`);
                }
                
            } else if (result.crc_error) {
                // ❌ CRC 검증 실패로 인한 API 에러
                this.skipCount++;
                console.warn(`⚠️ SDP810 CRC 검증 실패로 skip [${sensorIndex}] (총 ${this.skipCount}회 skip): ${result.error}`);
            } else {
                // ❌ 기타 API 오류
                console.warn(`⚠️ SDP810 API 응답 오류 [${sensorIndex}]:`, result.error || result.message);
            }
        } catch (error) {
            console.error(`❌ SDP810 API 호출 실패 [${sensorIndex}]: ${error.message}`);
        }
    }
    
    // 위젯 업데이트 (평균값 계산)
    updateWidgets(pressure, sensorIndex) {
        // 최신 데이터 배열 업데이트
        this.latestData[sensorIndex] = { pressure };
        
        // 유효한 데이터만 필터링
        const validData = this.latestData.filter(data => data !== undefined);
        
        if (validData.length === 0) {
            return;
        }
        
        // 평균값 계산
        const avgPressure = validData.reduce((sum, data) => sum + data.pressure, 0) / validData.length;
        
        // 최소/최대값 계산
        const pressureValues = validData.map(data => data.pressure);
        const minPressure = Math.min(...pressureValues);
        const maxPressure = Math.max(...pressureValues);
        
        // 차압 위젯 업데이트
        const pressureValueElement = document.getElementById('differential-pressure-average');
        if (pressureValueElement) {
            pressureValueElement.textContent = `${avgPressure.toFixed(3)} Pa`;
        }
        
        // 차압 범위 위젯 업데이트
        const pressureRangeElement = document.getElementById('differential-pressure-range');
        if (pressureRangeElement) {
            pressureRangeElement.textContent = `${minPressure.toFixed(3)} ~ ${maxPressure.toFixed(3)} Pa`;
        }
        
        // SDP810 위젯 업데이트 완료
    }

    // WebSocket 데이터 처리에서 SDP810 감지
    processSensorFromWebSocket(sensor) {
        // SDP810 차압 센서 처리
        if (sensor.sensor_type === 'SDP810') {
            console.log('📊 SDP810 차압 센서 발견:', sensor);
            const sensorId = `sdp810_${sensor.bus}_${sensor.mux_channel}`;
            this.addSensorToGroup(sensor, sensorId);
            
            // 센서 발견 시 위젯 초기화 (지연 실행)
            console.log('⏱️ SDP810 위젯 초기화 지연 실행 (DOM 준비 대기)');
            setTimeout(() => {
                this.initializeStatusWidgets(1);
                
                // 차트 초기화 직접 호출
                console.log('📊 SDP810 차트 초기화 직접 호출');
                
                if (this.chartHandler) {
                    // 가상의 센서 정보로 차트 초기화
                    const testSensors = [{
                        bus: sensor.bus,
                        mux_channel: sensor.mux_channel,
                        sensor_type: 'SDP810'
                    }];
                    
                    try {
                        this.chartHandler.initializeCharts(testSensors);
                        console.log('✅ SDP810 차트 초기화 호출 완료');
                    } catch (initError) {
                        console.error('❌ SDP810 차트 초기화 실패:', initError);
                    }
                } else {
                    console.error('❌ SDP810 차트 핸들러가 없음');
                }
                
                // 2초 간격 실제 API 폴링 시작
                setTimeout(() => {
                    console.log('🔗 SDP810 실제 API 폴링 시작');
                    this.startRealSensorPolling(sensor);
                }, 2000);
            }, 1000); // 1초 지연으로 DOM 완전 로딩 대기
        }
    }

    // 실제 센서 API 폴링 (2초 간격)
    startRealSensorPolling(sensor) {
        console.log('🔗 SDP810 실제 센서 API 폴링 시작: 2초 간격');
        
        const sensorId = `sdp810_${sensor.bus}_${sensor.mux_channel}`;
        const apiUrl = `/api/sensors/sdp810/${sensor.bus}/${sensor.mux_channel}`;
        
        // 실제 센서 데이터 가져오기 함수
        const fetchRealSensorData = async () => {
            try {
                console.log(`🔗 SDP810 API 호출: ${apiUrl}`);
                
                const response = await fetch(apiUrl);
                const result = await response.json();
                
                if (result.success && result.data && result.data.crc_valid) {
                    // CRC 검증 성공한 데이터만 처리
                    const pressureValue = result.data.pressure;
                    const timestamp = result.data.timestamp;
                    
                    console.log(`✅ SDP810 실제 센서 데이터 (CRC 성공): ${pressureValue.toFixed(4)} Pa (${timestamp})`);
                    
                    // 위젯 업데이트
                    this.updateWidgets(pressureValue, 0);
                    
                    // 차트 업데이트
                    if (this.chartHandler && this.chartHandler.isReady()) {
                        console.log('📊 SDP810 실제 데이터로 차트 업데이트');
                        this.chartHandler.updateChartsWithRealtimeData(sensorId, {
                            pressure: pressureValue
                        }, Date.now() / 1000);
                    }
                    
                } else {
                    // CRC 실패 또는 기타 오류 시 skip
                    this.skipCount++;
                    console.warn(`⚠️ SDP810 CRC 실패로 데이터 skip (총 ${this.skipCount}회): ${result.error || 'CRC 검증 실패'}`);
                }
                
            } catch (error) {
                console.error(`❌ SDP810 API 호출 실패: ${error.message}`);
            }
        };
        
        // 첫 번째 데이터 즉시 가져오기
        fetchRealSensorData();
        
        // 2초 간격으로 지속적인 실제 데이터 폴링
        const pollingInterval = setInterval(fetchRealSensorData, 2000);
        
        // 인터벌 저장 (나중에 정리용)
        this.pollingIntervals.push(pollingInterval);
        
        console.log('✅ SDP810 실제 센서 API 폴링 설정 완료 (2초 간격, CRC 검증 포함)');
    }

    // 실시간 데이터 처리 (WebSocket에서 호출)
    updateData(sensorData) {
        if (sensorData.sensor_type === 'SDP810' && sensorData.values) {
            const values = sensorData.values;
            
            // 연결 상태를 활성중으로 업데이트
            this.setStatusConnected(sensorData);
            
            // 차압 값 처리
            if (values.pressure !== undefined) {
                const sensorId = `sdp810_${sensorData.bus}_${sensorData.mux_channel}`;
                const sensorIndex = this.findSensorIndex(sensorId);
                
                if (sensorIndex !== -1) {
                    // 위젯 업데이트
                    this.updateWidgets(values.pressure, sensorIndex);
                    
                    // 차트 업데이트
                    if (this.chartHandler) {
                        this.chartHandler.updateChartsWithRealtimeData(sensorId, values, Date.now() / 1000);
                    }
                }
            }
        }
    }
    
    // 센서 인덱스 찾기
    findSensorIndex(sensorId) {
        const parts = sensorId.split('_');
        if (parts.length < 3) return -1;
        
        const bus = parseInt(parts[1]);
        const channel = parseInt(parts[2]);
        
        const sensors = this.dashboard.sensorGroups['pressure']?.sensors?.sdp810 || [];
        return sensors.findIndex(sensor => 
            sensor.bus === bus && sensor.mux_channel === channel
        );
    }
    
    // SDP810 연결 활성 상태 설정 (데이터 수신 시)
    setStatusConnected(sensorData) {
        const statusElement = document.getElementById('pressure-group-status');
        if (statusElement) {
            const sensorCount = this.dashboard.sensorGroups['pressure']?.sensors?.sdp810?.length || 1;
            statusElement.textContent = `${sensorCount}개 연결됨`;
            statusElement.className = 'sensor-group-status online';
            console.log('✅ SDP810 상태를 연결 활성중으로 설정 (데이터 수신)');
        }
    }

    // 폴링 중지
    stopPolling() {
        this.pollingIntervals.forEach(intervalId => {
            clearInterval(intervalId);
        });
        this.pollingIntervals = [];
        console.log(`🛑 SDP810 폴링 중지됨 (총 ${this.skipCount}회 CRC 실패로 skip)`);
    }

    // 센서 목록 반환
    getSensors() {
        return this.dashboard.sensorGroups['pressure']?.sensors?.sdp810 || [];
    }
}

// 전역으로 내보내기
window.SDP810SensorManager = SDP810SensorManager;