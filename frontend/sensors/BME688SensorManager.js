/**
 * BME688 센서 관리자
 * ===================
 * BME688 센서의 발견, 폴링, 데이터 처리를 담당
 */

class BME688SensorManager {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.sensors = [];
        this.pollingIntervals = [];
        this.chartHandler = null; // BME688ChartHandler 인스턴스
        this.latestData = []; // 각 센서의 최신 데이터 저장
        
        console.log('🔧 BME688SensorManager 초기화 완료');
    }
    
    // 차트 핸들러 설정
    setChartHandler(chartHandler) {
        this.chartHandler = chartHandler;
        console.log('📊 BME688 차트 핸들러 연결됨');
    }
    
    // BME688 센서 그룹에 센서 추가
    addSensorToGroup(sensorData, sensorId) {
        console.log(`📊 BME688 기압/가스저항 센서 발견: ${JSON.stringify(sensorData)} → ${sensorId}`);
        
        const dashboard = this.dashboard;
        
        if (!dashboard.sensorGroups['pressure-gas']) {
            console.warn('⚠️ pressure-gas 그룹이 존재하지 않음');
            return;
        }

        // sensors가 배열이 아닌 경우 강제로 배열로 변환
        if (!Array.isArray(dashboard.sensorGroups['pressure-gas'].sensors)) {
            console.log('🔧 pressure-gas.sensors 배열로 강제 초기화 (기존 타입: ' + typeof dashboard.sensorGroups['pressure-gas'].sensors + ')');
            dashboard.sensorGroups['pressure-gas'].sensors = [];
        }

        // BME688 센서 데이터 준비
        const sensorInfo = {
            sensor_id: sensorId,
            sensorId: sensorId,
            sensor_type: 'BME688',
            bus: sensorData.bus,
            mux_channel: sensorData.mux_channel,
            address: sensorData.address
        };

        dashboard.sensorGroups['pressure-gas'].sensors.push(sensorInfo);
        dashboard.sensorGroups['pressure-gas'].totalSensors = dashboard.sensorGroups['pressure-gas'].sensors.length;

        console.log(`✅ BME688 센서 그룹에 추가됨: ${sensorId}`, sensorInfo);

        // 센서 개수 업데이트
        this.updateSensorCount();
        
        console.log(`✅ BME688 센서 추가 완료: ${sensorId} (총 ${dashboard.sensorGroups['pressure-gas']?.sensors?.length || 0}개)`);
    }

    // 센서 개수 업데이트
    updateSensorCount() {
        const summaryElement = document.querySelector('#pressure-gas-summary');
        if (summaryElement) {
            const sensorCount = this.dashboard.sensorGroups['pressure-gas']?.sensors?.length || 0;
            summaryElement.textContent = `BME688×${sensorCount}`;
        }
    }
    
    // 감지된 BME688 센서에 대해 폴링 시작 (단일 센서 우선)
    async startPollingForDiscoveredSensors() {
        try {
            console.log('🔍 BME688 센서 검색 및 폴링 시작...');
            
            // 센서 그룹에서 BME688 센서 찾기
            const response = await fetch('/api/sensors/groups');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const groupsData = await response.json();
            console.log('📡 센서 그룹 데이터:', groupsData);
            
            // pressure-gas 그룹에서 BME688 센서 찾기
            const pressureGasGroup = groupsData.groups && groupsData.groups['pressure-gas'];
            if (pressureGasGroup && pressureGasGroup.sensors && pressureGasGroup.sensors.length > 0) {
                // BME688 센서만 필터링
                const bme688Sensors = pressureGasGroup.sensors.filter(sensor => 
                    sensor.sensor_type === 'BME688'
                );
                console.log(`✅ BME688 센서 ${bme688Sensors.length}개 발견`, bme688Sensors);
                
                // BME688 센서 5개 전체 처리 (Bus 1의 채널 2,3,5,6,7)
                const targetChannels = [2, 3, 5, 6, 7]; // Bus 1의 목표 채널들
                const validSensors = bme688Sensors.filter(sensor => 
                    sensor.bus === 1 && targetChannels.includes(sensor.mux_channel)
                );
                
                console.log(`🎆 BME688 센서 ${validSensors.length}개 전체 처리 시작:`, 
                    validSensors.map(s => `Bus${s.bus}:Ch${s.mux_channel}`));
                
                if (validSensors.length > 0) {
                    // 모든 유효한 센서에 대해 폴링 시작
                    validSensors.forEach((sensor, index) => {
                        const sensorInfo = {
                            bus: sensor.bus,
                            mux_channel: sensor.mux_channel
                        };
                        
                        const sensorId = `bme688_${sensor.bus}_${sensor.mux_channel}_77`;
                        console.log(`🚀 BME688 센서 폴링 시작 [${index}]: ${sensorId}`, sensorInfo);
                        
                        // 각 센서마다 고유 인덱스로 폴링 시작
                        this.startDataPolling(sensorId, sensorInfo, index);
                    });
                    
                    // BME688 상태 위젯 설정 (전체 센서 개수)
                    this.initializeStatusWidgets(validSensors.length);
                    
                    // 5개 센서 차트 초기화
                    console.log(`⏰ BME688 전체 센서 차트 초기화 2초 후 예약됨...`);
                    setTimeout(() => {
                        console.log(`🚀 BME688 전체 센서 차트 초기화 시작 (${validSensors.length}개)`);
                        if (this.chartHandler) {
                            this.chartHandler.initializeCharts(validSensors);
                        }
                    }, 2000); // 2초 후 차트 초기화
                } else {
                    console.warn(`⚠️ Bus 1의 BME688 센서를 찾을 수 없음`);
                    // 폴백: 모든 BME688 센서 사용
                    if (bme688Sensors.length > 0) {
                        console.log(`🔄 폴백: 모든 BME688 센서 사용 (${bme688Sensors.length}개)`);
                        bme688Sensors.forEach((sensor, index) => {
                            const sensorInfo = {
                                bus: sensor.bus,
                                mux_channel: sensor.mux_channel
                            };
                            const sensorId = `bme688_${sensor.bus}_${sensor.mux_channel}_77`;
                            this.startDataPolling(sensorId, sensorInfo, index);
                        });
                        
                        this.initializeStatusWidgets(bme688Sensors.length);
                        
                        setTimeout(() => {
                            if (this.chartHandler) {
                                this.chartHandler.initializeCharts(bme688Sensors);
                            }
                        }, 2000);
                    }
                }
                
            } else {
                console.warn('⚠️ pressure-gas 그룹에서 BME688 센서를 찾을 수 없음');
            }
            
        } catch (error) {
            console.error('❌ BME688 센서 검색 실패:', error);
        }
    }

    // 상태 위젯 초기화
    initializeStatusWidgets(sensorCount) {
        console.log(`🔧 BME688 상태 위젯 초기화: ${sensorCount}/${sensorCount} 센서`);
        
        // 헤더 상태 업데이트 (pressure-gas-status)
        const headerStatusElement = document.getElementById('pressure-gas-status');
        if (headerStatusElement) {
            headerStatusElement.textContent = `${sensorCount}개 연결됨`;
            headerStatusElement.className = 'sensor-group-status online';
        }
        
        // 위젯 영역 상태 업데이트 (pressure-gas-status-widget)
        const statusElement = document.getElementById('pressure-gas-status-widget');
        if (statusElement) {
            statusElement.textContent = `${sensorCount}/${sensorCount} 센서`;
        }
        
        console.log(`✅ BME688 상태 위젯 설정 완료: ${sensorCount}개 연결됨`);
    }

    // 데이터 폴링 시작
    startDataPolling(sensorId, sensor, sensorIndex) {
        console.log(`🔄 BME688 데이터 폴링 시작: ${sensorId} (인덱스: ${sensorIndex})`, sensor);
        console.log(`⏰ 폴링 간격: ${this.dashboard.config.updateInterval}ms`);
        
        // 즉시 한 번 실행
        this.fetchSensorData(sensor, sensorId, sensorIndex);
        
        // 주기적 업데이트 설정
        const intervalId = setInterval(() => {
            this.fetchSensorData(sensor, sensorId, sensorIndex);
        }, this.dashboard.config.updateInterval);
        
        // 인터벌 ID 저장
        this.pollingIntervals.push(intervalId);
        
        console.log(`✅ BME688 폴링 설정 완료: ${sensorId} - interval ID ${intervalId}`);
    }

    // 센서 데이터 가져오기
    async fetchSensorData(sensor, sensorId, sensorIndex) {
        const apiUrl = `/api/sensors/bme688/${sensor.bus}/${sensor.mux_channel}`;
        
        try {
            const response = await fetch(apiUrl);
            const result = await response.json();
            
            if (result.success && result.data) {
                const pressure = result.data.pressure;
                const gasResistance = result.data.gas_resistance;
                const timestamp = Date.now() / 1000;
                
                console.log(`📊 BME688 데이터 [${sensorIndex}]: 기압=${pressure}hPa, 가스저항=${gasResistance}Ω`);
                
                // 차트 핸들러를 통한 직접 차트 업데이트 (에러 처리 추가)
                if (this.chartHandler && this.chartHandler.isReady()) {
                    try {
                        this.chartHandler.updateChartsWithRealtimeData(sensorId, {
                            pressure: pressure,
                            gas_resistance: gasResistance
                        }, timestamp);
                    } catch (chartError) {
                        console.warn(`⚠️ BME688 차트 업데이트 에러: ${chartError.message}`);
                        console.log(`📦 에러 발생으로 데이터 버퍼링으로 전환`);
                        // 에러 발생 시 버퍼링으로 전환
                        this.chartHandler.bufferData(sensorId, {
                            pressure: pressure,
                            gas_resistance: gasResistance
                        }, timestamp);
                    }
                } else {
                    console.log(`📦 BME688ChartHandler 준비되지 않음, 데이터 버퍼링`);
                    // 차트 핸들러가 준비되지 않은 경우 데이터를 버퍼에 저장
                    if (this.chartHandler) {
                        this.chartHandler.bufferData(sensorId, {
                            pressure: pressure,
                            gas_resistance: gasResistance
                        }, timestamp);
                    }
                }
                
                // 위젯 업데이트 (모든 센서 데이터 수집 후 평균 계산)
                this.updateWidgets(pressure, gasResistance, sensorIndex);
                
            } else {
                console.warn(`⚠️ BME688 API 오류 [${sensorIndex}]:`, result.message || result.error);
            }
        } catch (error) {
            console.error(`❌ BME688 데이터 수집 실패 [${sensorIndex}]:`, error);
        }
    }
    
    // 위젯 업데이트 (평균값 계산)
    updateWidgets(pressure, gasResistance, sensorIndex) {
        // 최신 데이터 배열 업데이트
        this.latestData[sensorIndex] = { pressure, gasResistance };
        
        // 유효한 데이터만 필터링
        const validData = this.latestData.filter(data => data !== undefined);
        
        if (validData.length === 0) {
            return;
        }
        
        // 평균값 계산
        const avgPressure = validData.reduce((sum, data) => sum + data.pressure, 0) / validData.length;
        const avgGasResistance = validData.reduce((sum, data) => sum + data.gasResistance, 0) / validData.length;
        
        // 기압 위젯 업데이트
        const pressureValueElement = document.getElementById('pressure-average');
        if (pressureValueElement) {
            pressureValueElement.textContent = `${avgPressure.toFixed(2)} hPa`;
        }
        
        // 가스저항 위젯 업데이트
        const gasValueElement = document.getElementById('gas-resistance-average');
        if (gasValueElement) {
            gasValueElement.textContent = `${Math.round(avgGasResistance)} Ω`;
        }
        
        console.log(`✅ BME688 위젯 업데이트 완료 [${validData.length}개 센서] - 평균 기압: ${avgPressure.toFixed(2)}hPa, 평균 가스저항: ${Math.round(avgGasResistance)}Ω`);
    }

    // 폴링 중지
    stopPolling() {
        this.pollingIntervals.forEach(intervalId => {
            clearInterval(intervalId);
        });
        this.pollingIntervals = [];
        console.log('🛑 BME688 폴링 중지됨');
    }

    // 센서 목록 반환
    getSensors() {
        return this.dashboard.sensorGroups['pressure-gas']?.sensors || [];
    }
}

// 전역으로 내보내기
window.BME688SensorManager = BME688SensorManager;