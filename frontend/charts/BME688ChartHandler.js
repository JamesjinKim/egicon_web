/**
 * BME688 차트 전용 핸들러
 * ==============================
 * BME688 기압/가스저항 센서의 차트 생성, 업데이트, 관리를 담당
 */

class BME688ChartHandler {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.isInitialized = false;
        this.pendingData = []; // 초기화 전에 받은 데이터 버퍼
        this.sensors = [];
        this.isUpdating = false; // 차트 업데이트 중 플래그
        this.errorCount = 0; // 연속 에러 카운트
        this.maxErrors = 5; // 최대 연속 에러 허용 수
        
        console.log('📊 BME688ChartHandler 초기화 완료');
    }
    
    // BME688 전체 센서 차트 초기화
    initializeCharts(sensors) {
        console.log(`🚨 BME688 전체 센서 차트 초기화 시작!`);
        console.log(`📊 BME688 센서 ${sensors.length}개 전체 처리`);
        
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
        
        // 모든 센서에 대한 라벨 생성
        const pressureLabels = sensors.map(sensor => 
            `BME688-${sensor.bus}.${sensor.mux_channel} 기압`
        );
        const gasLabels = sensors.map(sensor => 
            `BME688-${sensor.bus}.${sensor.mux_channel} 가스저항`
        );
        
        console.log(`🔨 ${sensors.length}개 센서 멀티 차트 생성`);
        console.log(`📊 기압 라벨:`, pressureLabels);
        console.log(`📊 가스저항 라벨:`, gasLabels);
        
        // 멀티 센서 차트 생성
        this.createMultiSensorChart('pressure-multi-chart', 'pressure', pressureLabels);
        this.createMultiSensorChart('gas-resistance-multi-chart', 'gas_resistance', gasLabels);
        
        console.log(`✅ ${sensors.length}개 센서 차트 생성 완료`);
        
        // 최종 확인
        setTimeout(() => {
            this.verifyCharts();
        }, 100);

        this.isInitialized = true;
        this.sensors = sensors; // 센서 정보 저장
        
        // 대기 중인 데이터 처리
        setTimeout(() => {
            this.processPendingData();
        }, 200); // 차트 완전 초기화 후 처리
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

    // 멀티 센서 차트 생성 (여러 데이터셋)
    createMultiSensorChart(canvasId, sensorType, labels) {
        console.log(`🔨 멀티 센서 차트 생성: ${canvasId}, 라벨 수: ${labels.length}`);
        console.log(`📊 라벨 상세:`, labels);
        
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
        
        // 컬러 팔레트
        const colorPalette = [
            '#ff6384', '#36a2eb', '#4bc0c0', '#ff9f40', '#9966ff',
            '#ffcd56', '#c9cbcf', '#ff6384', '#36a2eb', '#4bc0c0'
        ];
        
        // 각 센서별 데이터셋 생성
        const datasets = labels.map((label, index) => ({
            label: label,
            data: [],
            borderColor: colorPalette[index % colorPalette.length],
            backgroundColor: colorPalette[index % colorPalette.length] + '20',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 5,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: colorPalette[index % colorPalette.length],
            pointBorderWidth: 2
        }));
        
        console.log(`📊 실제 생성된 데이터셋:`, datasets.map((d, i) => `${i}: ${d.label}`));
        
        this.dashboard.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: datasets
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
                        type: 'linear',
                        display: true,
                        title: {
                            display: true,
                            text: '데이터 포인트'
                        },
                        min: 0,
                        max: 30,
                        grid: { 
                            color: 'rgba(0, 0, 0, 0.05)' 
                        },
                        ticks: {
                            maxTicksLimit: 10,
                            stepSize: 5
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: sensorConfig.unit || sensorType
                        },
                        min: sensorConfig.min,
                        max: sensorConfig.max,
                        grid: { 
                            color: 'rgba(0, 0, 0, 0.05)' 
                        }
                    }
                }
            }
        });
        
        console.log(`✅ 멀티 센서 차트 생성 완료: ${canvasId} (${datasets.length}개 데이터셋)`)
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

    // 실시간 데이터를 차트에 업데이트
    updateChartsWithRealtimeData(sensorId, data, timestamp) {
        console.log(`🔄 BME688 차트 데이터 업데이트: ${sensorId}`, data);
        
        // sensorId에서 bus와 channel 추출하여 인덱스 찾기
        const sensorIndex = this.findSensorIndex(sensorId);
        
        if (sensorIndex === -1) {
            console.warn(`⚠️ 센서 ID ${sensorId}에 해당하는 인덱스를 찾을 수 없음`);
            return;
        }
        
        console.log(`📊 BME688 멀티 센서 데이터 차트 전달: ${sensorId} → 인덱스 ${sensorIndex}`, data);
        
        // 차트 직접 업데이트
        this.updateChartDataDirectly(sensorId, data, timestamp, sensorIndex);
    }
    
    // 센서 ID로부터 차트 인덱스 찾기
    findSensorIndex(sensorId) {
        // sensorId 형식: "bme688_1_3_77" (bus_channel_address)
        const parts = sensorId.split('_');
        if (parts.length < 3) {
            console.warn(`⚠️ 잘못된 센서 ID 형식: ${sensorId}`);
            return -1;
        }
        
        const bus = parseInt(parts[1]);
        const channel = parseInt(parts[2]);
        
        // 초기화된 센서 목록에서 해당 센서의 인덱스 찾기
        const index = this.sensors.findIndex(sensor => 
            sensor.bus === bus && sensor.mux_channel === channel
        );
        
        console.log(`🔍 센서 인덱스 검색: ${sensorId} (Bus${bus}, Ch${channel}) → 인덱스 ${index}`);
        return index;
    }
    
    // 차트에 직접 데이터 업데이트 (BME688 전용)
    updateChartDataDirectly(sensorId, data, timestamp, sensorIndex) {
        console.log(`📊 BME688 차트 직접 업데이트: ${sensorId} [${sensorIndex}]`, data);
        
        // 연속 에러가 너무 많으면 업데이트 중단
        if (this.errorCount >= this.maxErrors) {
            console.warn(`⚠️ BME688 차트 에러 한계 도달 (${this.errorCount}/${this.maxErrors}), 업데이트 중단`);
            return;
        }
        
        // 이미 업데이트 중이면 건너뜀 (동시 업데이트 방지)
        if (this.isUpdating) {
            console.log(`⏸️ BME688 차트 업데이트 중, 건너뜀`);
            return;
        }
        
        this.isUpdating = true;
        
        // 기압 차트 업데이트
        if (data.pressure !== undefined) {
            const pressureChart = this.dashboard.charts['pressure-multi-chart'];
            if (pressureChart && pressureChart.data && pressureChart.data.datasets) {
                if (pressureChart.data.datasets[sensorIndex]) {
                    // 현재 데이터 길이 확인
                    const currentDataLength = pressureChart.data.datasets[sensorIndex].data.length;
                    
                    // X축 위치 계산 (30개 범위 내에서 슬라이딩)
                    let xPosition = currentDataLength;
                    if (currentDataLength >= 30) {
                        // 30개 이후부터는 슬라이딩 윈도우 적용
                        xPosition = 29; // 마지막 위치에 고정
                        // 기존 데이터를 왼쪽으로 이동
                        pressureChart.data.datasets[sensorIndex].data.forEach((point, index) => {
                            if (point && typeof point === 'object') {
                                point.x = index;
                            }
                        });
                    }
                    
                    // 첫 번째 센서만 X축 레이블 관리
                    if (sensorIndex === 0) {
                        if (currentDataLength < 30) {
                            pressureChart.data.labels.push(currentDataLength);
                        }
                    }
                    
                    // 새 데이터 추가
                    pressureChart.data.datasets[sensorIndex].data.push({
                        x: xPosition,
                        y: data.pressure
                    });
                    
                    // 30개 이상이면 첫 번째 데이터 제거
                    if (pressureChart.data.datasets[sensorIndex].data.length > 30) {
                        pressureChart.data.datasets[sensorIndex].data.shift();
                    }
                    
                    try {
                        pressureChart.update('none');
                        console.log(`✅ 기압 차트 업데이트 [${sensorIndex}]: ${data.pressure}hPa`);
                        this.errorCount = 0; // 성공 시 에러 카운트 리셋
                    } catch (updateError) {
                        this.errorCount++;
                        console.warn(`⚠️ 기압 차트 업데이트 실패 (${this.errorCount}/${this.maxErrors}): ${updateError.message}`);
                        // 차트 재생성 시도
                        if (this.errorCount < this.maxErrors) {
                            setTimeout(() => {
                                this.recreatePressureChart();
                            }, 100);
                        }
                    }
                } else {
                    console.warn(`⚠️ 기압 차트 데이터셋[${sensorIndex}] 없음 (총 ${pressureChart.data.datasets.length}개 데이터셋)`);
                }
            } else {
                console.warn(`⚠️ 기압 차트 'pressure-multi-chart' 없음`);
            }
        }
        
        // 가스저항 차트 업데이트
        if (data.gas_resistance !== undefined) {
            const gasChart = this.dashboard.charts['gas-resistance-multi-chart'];
            if (gasChart && gasChart.data && gasChart.data.datasets) {
                if (gasChart.data.datasets[sensorIndex]) {
                    // 현재 데이터 길이 확인
                    const currentDataLength = gasChart.data.datasets[sensorIndex].data.length;
                    
                    // X축 위치 계산 (30개 범위 내에서 슬라이딩)
                    let xPosition = currentDataLength;
                    if (currentDataLength >= 30) {
                        // 30개 이후부터는 슬라이딩 윈도우 적용
                        xPosition = 29; // 마지막 위치에 고정
                        // 기존 데이터를 왼쪽으로 이동
                        gasChart.data.datasets[sensorIndex].data.forEach((point, index) => {
                            if (point && typeof point === 'object') {
                                point.x = index;
                            }
                        });
                    }
                    
                    // 첫 번째 센서만 X축 레이블 관리
                    if (sensorIndex === 0) {
                        if (currentDataLength < 30) {
                            gasChart.data.labels.push(currentDataLength);
                        }
                    }
                    
                    // 새 데이터 추가
                    gasChart.data.datasets[sensorIndex].data.push({
                        x: xPosition,
                        y: data.gas_resistance
                    });
                    
                    // 30개 이상이면 첫 번째 데이터 제거
                    if (gasChart.data.datasets[sensorIndex].data.length > 30) {
                        gasChart.data.datasets[sensorIndex].data.shift();
                    }
                    
                    try {
                        gasChart.update('none');
                        console.log(`✅ 가스저항 차트 업데이트 [${sensorIndex}]: ${data.gas_resistance}Ω`);
                        this.errorCount = 0; // 성공 시 에러 카운트 리셋
                    } catch (updateError) {
                        this.errorCount++;
                        console.warn(`⚠️ 가스저항 차트 업데이트 실패 (${this.errorCount}/${this.maxErrors}): ${updateError.message}`);
                        // 차트 재생성 시도
                        if (this.errorCount < this.maxErrors) {
                            setTimeout(() => {
                                this.recreateGasChart();
                            }, 100);
                        }
                    }
                } else {
                    console.warn(`⚠️ 가스저항 차트 데이터셋[${sensorIndex}] 없음 (총 ${gasChart.data.datasets.length}개 데이터셋)`);
                }
            } else {
                console.warn(`⚠️ 가스저항 차트 'gas-resistance-multi-chart' 없음`);
            }
        }
        
        // 업데이트 완료 플래그 해제
        this.isUpdating = false;
    }

    // 대기 중인 데이터 버퍼에 추가
    bufferData(sensorId, data, timestamp) {
        this.pendingData.push({ sensorId, data, timestamp });
        console.log(`📦 BME688 데이터 버퍼에 추가: ${sensorId} (총 ${this.pendingData.length}개)`);
    }
    
    // 대기 중인 데이터 처리
    processPendingData() {
        if (this.pendingData.length === 0) {
            console.log(`✅ BME688 대기 데이터 없음`);
            return;
        }
        
        console.log(`🔄 BME688 대기 데이터 ${this.pendingData.length}개 처리 시작`);
        
        const dataToProcess = [...this.pendingData];
        this.pendingData = []; // 버퍼 초기화
        
        dataToProcess.forEach(({ sensorId, data, timestamp }) => {
            this.updateChartsWithRealtimeData(sensorId, data, timestamp);
        });
        
        console.log(`✅ BME688 대기 데이터 처리 완료`);
    }

    // 초기화 상태 확인
    isReady() {
        return this.isInitialized;
    }
    
    // 기압 차트 재생성 (오류 복구용)
    recreatePressureChart() {
        console.log(`🔄 기압 차트 재생성 시도`);
        try {
            // 기존 차트 완전 제거
            const existingChart = this.dashboard.charts['pressure-multi-chart'];
            if (existingChart) {
                existingChart.destroy();
                delete this.dashboard.charts['pressure-multi-chart'];
            }
            
            // DOM 요소 확인 후 재생성
            const canvas = document.getElementById('pressure-multi-chart');
            if (canvas && canvas.ownerDocument) {
                this.createSingleSensorChart('pressure-multi-chart', 'pressure', 'BME688-1.3 기압');
                console.log(`✅ 기압 차트 재생성 완료`);
            } else {
                console.warn(`⚠️ 기압 차트 DOM 요소 없음, 재생성 건너뜀`);
            }
        } catch (error) {
            console.error(`❌ 기압 차트 재생성 실패: ${error.message}`);
        }
    }
    
    // 가스저항 차트 재생성 (오류 복구용)
    recreateGasChart() {
        console.log(`🔄 가스저항 차트 재생성 시도`);
        try {
            // 기존 차트 완전 제거
            const existingChart = this.dashboard.charts['gas-resistance-multi-chart'];
            if (existingChart) {
                existingChart.destroy();
                delete this.dashboard.charts['gas-resistance-multi-chart'];
            }
            
            // DOM 요소 확인 후 재생성
            const canvas = document.getElementById('gas-resistance-multi-chart');
            if (canvas && canvas.ownerDocument) {
                this.createSingleSensorChart('gas-resistance-multi-chart', 'gas_resistance', 'BME688-1.3 가스저항');
                console.log(`✅ 가스저항 차트 재생성 완료`);
            } else {
                console.warn(`⚠️ 가스저항 차트 DOM 요소 없음, 재생성 건너뜀`);
            }
        } catch (error) {
            console.error(`❌ 가스저항 차트 재생성 실패: ${error.message}`);
        }
    }
}

// 전역으로 내보내기
window.BME688ChartHandler = BME688ChartHandler;