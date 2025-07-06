/**
 * BME688 기압/가스저항 센서 관리 클래스
 * =======================================
 * BME688 센서의 데이터 수집, 차트 생성, 상태 관리를 담당
 */

class BME688Sensor {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.sensors = [];
        this.pollingIntervals = [];
        this.isInitialized = false;
        
        console.log('📊 BME688Sensor 클래스 초기화 완료');
    }

    // BME688 센서 그룹에 센서 추가
    addSensorToGroup(sensorData, sensorId) {
        console.log(`📊 BME688 기압/가스저항 센서 발견: ${sensorData} → ${sensorId}`);
        
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

    // BME688 단계별 차트 초기화
    initializeCharts(sensors) {
        console.log(`🚨 BME688 단계별 차트 초기화 시작!`);
        console.log(`📊 BME688 센서 ${sensors.length}개 단계별 처리`);
        
        if (sensors.length === 0) {
            console.warn(`⚠️ BME688 센서가 없어 차트 생성 중단`);
            return;
        }
        
        // DOM 요소 존재 확인
        const pressureCanvas = document.getElementById('pressure-multi-chart');
        const gasCanvas = document.getElementById('gas-resistance-multi-chart');
        
        if (!pressureCanvas || !gasCanvas) {
            console.error(`❌ 캔버스 요소 누락, 1초 후 재시도`);
            setTimeout(() => {
                this.initializeCharts(sensors);
            }, 1000);
            return;
        }
        
        // 1단계: 첫 번째 센서로 기본 차트 생성
        const firstSensor = sensors[0];
        console.log(`🔨 1단계: 첫 번째 센서로 기본 차트 생성`, firstSensor);
        
        const firstPressureLabel = `BME688-${firstSensor.bus}.${firstSensor.mux_channel} 기압`;
        const firstGasLabel = `BME688-${firstSensor.bus}.${firstSensor.mux_channel} 가스저항`;
        
        // 기본 차트 생성 (1개 데이터셋)
        this.createSingleSensorChart('pressure-multi-chart', 'pressure', firstPressureLabel);
        this.createSingleSensorChart('gas-resistance-multi-chart', 'gas_resistance', firstGasLabel);
        
        console.log(`✅ 1단계 완료: 기본 차트 생성됨`);
        
        // 2단계: 나머지 센서들을 순차적으로 추가
        if (sensors.length > 1) {
            console.log(`🔨 2단계: 나머지 ${sensors.length - 1}개 센서 추가 시작`);
            
            for (let i = 1; i < sensors.length; i++) {
                const sensor = sensors[i];
                const pressureLabel = `BME688-${sensor.bus}.${sensor.mux_channel} 기압`;
                const gasLabel = `BME688-${sensor.bus}.${sensor.mux_channel} 가스저항`;
                
                console.log(`➕ 센서 ${i + 1}/${sensors.length} 추가: ${sensor.bus}.${sensor.mux_channel}`);
                
                this.addDatasetToChart('pressure-multi-chart', pressureLabel, i);
                this.addDatasetToChart('gas-resistance-multi-chart', gasLabel, i);
            }
            
            console.log(`✅ 2단계 완료: 모든 센서 추가됨`);
        }
        
        // 최종 확인
        setTimeout(() => {
            this.verifyCharts();
        }, 100);

        this.isInitialized = true;
    }

    // 단일 센서 차트 생성 (기본 1개 데이터셋)
    createSingleSensorChart(canvasId, sensorType, label) {
        console.log(`🔨 단일 센서 차트 생성: ${canvasId}, 라벨: ${label}`);
        
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`❌ 캔버스 요소 없음: ${canvasId}`);
            return;
        }
        
        // 기존 차트 파괴
        const existingChart = Chart.getChart(canvasId);
        if (existingChart) {
            console.log(`🗑️ 기존 차트 파괴: ${canvasId}`);
            existingChart.destroy();
        }
        
        if (this.dashboard.charts[canvasId]) {
            delete this.dashboard.charts[canvasId];
        }
        
        const sensorConfig = this.dashboard.sensorTypes[sensorType];
        if (!sensorConfig) {
            console.error(`❌ 센서 설정 없음: ${sensorType}`);
            return;
        }
        
        // 첫 번째 데이터셋 생성
        const dataset = {
            label: label,
            data: [],
            borderColor: '#ff6384',
            backgroundColor: '#ff638420',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 5,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#ff6384',
            pointBorderWidth: 2
        };
        
        this.dashboard.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [dataset]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: { color: 'rgba(0, 0, 0, 0.05)' }
                    },
                    y: {
                        display: true,
                        min: sensorConfig.min,
                        max: sensorConfig.max,
                        grid: { color: 'rgba(0, 0, 0, 0.05)' }
                    }
                }
            }
        });
        
        console.log(`✅ 단일 센서 차트 생성 완료: ${canvasId}`);
    }

    // 기존 차트에 데이터셋 추가
    addDatasetToChart(canvasId, label, index) {
        console.log(`➕ 데이터셋 추가: ${canvasId}, 라벨: ${label}, 인덱스: ${index}`);
        
        const chart = this.dashboard.charts[canvasId];
        if (!chart) {
            console.error(`❌ 차트 없음: ${canvasId}`);
            return;
        }
        
        // 색상 팔레트
        const colors = ['#ff6384', '#36a2eb', '#4bc0c0', '#ff9f40', '#9966ff'];
        const color = colors[index % colors.length];
        
        const newDataset = {
            label: label,
            data: [],
            borderColor: color,
            backgroundColor: color + '20',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 5,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: color,
            pointBorderWidth: 2
        };
        
        chart.data.datasets.push(newDataset);
        chart.update('none'); // 애니메이션 없이 업데이트
        
        console.log(`✅ 데이터셋 추가 완료: ${canvasId} (총 ${chart.data.datasets.length}개)`);
    }

    // BME688 차트 최종 확인
    verifyCharts() {
        console.log(`🔍 BME688 차트 최종 확인`);
        
        const pressureChart = this.dashboard.charts['pressure-multi-chart'];
        const gasChart = this.dashboard.charts['gas-resistance-multi-chart'];
        
        console.log(`📊 최종 차트 상태:`, {
            'pressure-multi-chart': !!pressureChart,
            'gas-resistance-multi-chart': !!gasChart
        });
        
        if (pressureChart) {
            console.log(`📊 pressure 차트: ${pressureChart.data.datasets.length}개 데이터셋`);
            console.log(`📊 pressure 라벨:`, pressureChart.data.datasets.map(d => d.label));
        }
        
        if (gasChart) {
            console.log(`📊 gas_resistance 차트: ${gasChart.data.datasets.length}개 데이터셋`);
            console.log(`📊 gas_resistance 라벨:`, gasChart.data.datasets.map(d => d.label));
        }
        
        console.log(`✅ BME688 단계별 차트 초기화 완전 완료!`);
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
                console.log(`📊 BME688 데이터 [${sensorIndex}]: 기압=${result.data.pressure}hPa, 가스저항=${result.data.gas_resistance}Ω`);
                
                // 실시간 데이터 처리
                this.dashboard.handleRealtimeData([{
                    sensorId: sensorId,
                    data: {
                        pressure: result.data.pressure,
                        gas_resistance: result.data.gas_resistance
                    }
                }]);
            } else {
                console.warn(`⚠️ BME688 API 오류 [${sensorIndex}]:`, result.message || result.error);
            }
        } catch (error) {
            console.error(`❌ BME688 데이터 수집 실패 [${sensorIndex}]:`, error);
        }
    }

    // 상태 위젯 초기화
    initializeStatusWidgets(sensorCount) {
        console.log(`🔧 BME688 상태 위젯 초기화: ${sensorCount}/${sensorCount} 센서`);
        
        const statusElement = document.getElementById('pressure-gas-status-widget');
        if (statusElement) {
            statusElement.textContent = `${sensorCount}/${sensorCount} 센서`;
        }
        
        console.log(`✅ BME688 상태 위젯 설정 완료: ${sensorCount}/${sensorCount} 활성`);
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

    // 초기화 상태 확인
    isReady() {
        return this.isInitialized;
    }
}

// 전역으로 내보내기
window.BME688Sensor = BME688Sensor;