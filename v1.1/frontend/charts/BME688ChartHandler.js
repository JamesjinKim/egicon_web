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
        
        // BME688ChartHandler 초기화 완료
    }
    
    // BME688 전체 센서 차트 초기화
    initializeCharts(sensors) {
        console.log(`📊 BME688 차트 초기화: ${sensors.length}개 센서`);
        
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
        
        // 멀티 센서 차트 생성
        
        // 멀티 센서 차트 생성
        this.createMultiSensorChart('pressure-multi-chart', 'pressure', pressureLabels);
        this.createMultiSensorChart('gas-resistance-multi-chart', 'gas_resistance', gasLabels);
        
        console.log(`✅ BME688 차트 생성 완료: ${sensors.length}개`);
        
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
        // 단일 센서 차트 생성
        
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
            showLine: true,  // 명시적으로 선 표시 활성화
            spanGaps: true,  // 데이터 간격이 있어도 선 연결
            pointRadius: 2,
            pointHoverRadius: 5,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#ff6384',
            pointBorderWidth: 2,
            stepped: false,  // 부드러운 곡선 유지
            cubicInterpolationMode: 'default'  // 기본 곡선 보간
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
                animation: {
                    duration: 0  // 애니메이션 비활성화로 성능 향상 및 끊김 방지
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    line: {
                        tension: 0.4,
                        borderWidth: 2,
                        spanGaps: true  // 전역 spanGaps 설정
                    },
                    point: {
                        radius: 2,
                        hoverRadius: 5
                    }
                },
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
        
        // 단일 센서 차트 생성 완료
    }

    // 멀티 센서 차트 생성 (여러 데이터셋)
    createMultiSensorChart(canvasId, sensorType, labels) {
        // 멀티 센서 차트 생성
        
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
            showLine: true,  // 명시적으로 선 표시 활성화
            spanGaps: true,  // 데이터 간격이 있어도 선 연결
            pointRadius: 2,
            pointHoverRadius: 5,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: colorPalette[index % colorPalette.length],
            pointBorderWidth: 2,
            stepped: false,  // 부드러운 곡선 유지
            cubicInterpolationMode: 'default'  // 기본 곡선 보간
        }));
        
        // 실제 생성된 데이터셋
        
        this.dashboard.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 0  // 애니메이션 비활성화로 성능 향상 및 끊김 방지
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    line: {
                        tension: 0.4,
                        borderWidth: 2,
                        spanGaps: true  // 전역 spanGaps 설정
                    },
                    point: {
                        radius: 2,
                        hoverRadius: 5
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        display: true,
                        title: {
                            display: true,
                            text: '시간'
                        },
                        time: {
                            unit: 'second',
                            displayFormats: {
                                second: 'HH:mm:ss'
                            }
                        },
                        min: function(context) {
                            // 최신 60초 범위 표시
                            return new Date(Date.now() - 60000);
                        },
                        max: function(context) {
                            // 현재 시간까지 표시
                            return new Date();
                        },
                        grid: { 
                            color: 'rgba(0, 0, 0, 0.05)' 
                        },
                        ticks: {
                            maxTicksLimit: 8,
                            source: 'auto'
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
        
        // 멀티 센서 차트 생성 완료
    }

    // BME688 차트 최종 확인
    verifyCharts() {
        const pressureChart = this.dashboard.charts['pressure-multi-chart'];
        const gasChart = this.dashboard.charts['gas-resistance-multi-chart'];
        
        if (!pressureChart || !gasChart) {
            console.error('❌ BME688 차트 생성 실패');
            return;
        }
        
        console.log(`✅ BME688 차트 초기화 완료`);
    }

    // 실시간 데이터를 차트에 업데이트
    updateChartsWithRealtimeData(sensorId, data, timestamp) {
        // sensorId에서 bus와 channel 추출하여 인덱스 찾기
        const sensorIndex = this.findSensorIndex(sensorId);
        
        if (sensorIndex === -1) {
            console.warn(`⚠️ BME688 센서 인덱스 찾기 실패: ${sensorId}`);
            return;
        }
        
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
        
        // 센서 인덱스 검색 완료
        return index;
    }
    
    // 차트에 직접 데이터 업데이트 (BME688 전용)
    updateChartDataDirectly(sensorId, data, timestamp, sensorIndex) {
        // 연속 에러가 너무 많으면 업데이트 중단
        if (this.errorCount >= this.maxErrors) {
            return;
        }
        
        // 이미 업데이트 중이면 건너뜀 (동시 업데이트 방지)
        if (this.isUpdating) {
            return;
        }
        
        this.isUpdating = true;
        
        try {
        
        // 현재 시간을 X축 값으로 사용 (timestamp가 없으면 현재 시간 사용)
        const currentTime = timestamp ? new Date(timestamp * 1000) : new Date();
        
        // 기압 차트 업데이트
        if (data.pressure !== undefined) {
            const pressureChart = this.dashboard.charts['pressure-multi-chart'];
            if (pressureChart && pressureChart.data && pressureChart.data.datasets) {
                if (pressureChart.data.datasets[sensorIndex]) {
                    // 현재 데이터 길이 확인
                    const currentDataLength = pressureChart.data.datasets[sensorIndex].data.length;
                    console.log(`📊 BME688 기압 현재 데이터 개수: ${currentDataLength}개`);
                    
                    // 60초 이전 데이터 제거 (시간 기반 슬라이딩 윈도우)
                    const cutoffTime = new Date(currentTime.getTime() - 60000); // 60초 전
                    pressureChart.data.datasets[sensorIndex].data = pressureChart.data.datasets[sensorIndex].data.filter(point => {
                        return new Date(point.x).getTime() > cutoffTime.getTime();
                    });
                    console.log(`📊 BME688 기압 60초 이전 데이터 정리됨 (현재: ${pressureChart.data.datasets[sensorIndex].data.length}개)`);
                    
                    // 새 데이터 포인트 추가 (시간 기반)
                    const newDataPoint = {
                        x: currentTime,
                        y: data.pressure
                    };
                    console.log(`📊 BME688 기압 새 데이터 포인트 추가:`, newDataPoint);
                    
                    // 데이터 추가
                    pressureChart.data.datasets[sensorIndex].data.push(newDataPoint);
                    
                    // 데이터 포인트가 2개 이상일 때만 선 표시
                    const dataPointCount = pressureChart.data.datasets[sensorIndex].data.length;
                    if (dataPointCount >= 2) {
                        pressureChart.data.datasets[sensorIndex].showLine = true;
                        console.log(`📈 BME688 기압 트렌드 선 활성화: ${dataPointCount}개 데이터 포인트`);
                    }
                    
                    try {
                        pressureChart.update('none');
                        console.log(`✅ BME688 기압 차트 업데이트 성공`);
                        
                        // 트렌드 선 연속성 보장을 위한 추가 검증
                        const currentDataset = pressureChart.data.datasets[sensorIndex];
                        if (currentDataset.data.length >= 2) {
                            // 트렌드 선 설정 강제 적용
                            currentDataset.showLine = true;
                            currentDataset.spanGaps = true;
                            
                            console.log(`📈 BME688 기압 트렌드 선 연속성 확인: ${currentDataset.data.length}개 포인트`);
                        }
                        
                        this.errorCount = 0; // 성공 시 에러 카운트 리셋
                    } catch (updateError) {
                        this.errorCount++;
                        console.warn(`⚠️ BME688 기압 차트 에러 (${this.errorCount}/${this.maxErrors}): ${updateError.message}`);
                        throw updateError; // 상위 catch에서 처리
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
                    console.log(`📊 BME688 가스저항 현재 데이터 개수: ${currentDataLength}개`);
                    
                    // 60초 이전 데이터 제거 (시간 기반 슬라이딩 윈도우)
                    const cutoffTime = new Date(currentTime.getTime() - 60000); // 60초 전
                    gasChart.data.datasets[sensorIndex].data = gasChart.data.datasets[sensorIndex].data.filter(point => {
                        return new Date(point.x).getTime() > cutoffTime.getTime();
                    });
                    console.log(`📊 BME688 가스저항 60초 이전 데이터 정리됨 (현재: ${gasChart.data.datasets[sensorIndex].data.length}개)`);
                    
                    // 새 데이터 포인트 추가 (시간 기반)
                    const newDataPoint = {
                        x: currentTime,
                        y: data.gas_resistance
                    };
                    console.log(`📊 BME688 가스저항 새 데이터 포인트 추가:`, newDataPoint);
                    
                    // 데이터 추가
                    gasChart.data.datasets[sensorIndex].data.push(newDataPoint);
                    
                    // 데이터 포인트가 2개 이상일 때만 선 표시
                    const dataPointCount = gasChart.data.datasets[sensorIndex].data.length;
                    if (dataPointCount >= 2) {
                        gasChart.data.datasets[sensorIndex].showLine = true;
                        console.log(`📈 BME688 가스저항 트렌드 선 활성화: ${dataPointCount}개 데이터 포인트`);
                    }
                    
                    try {
                        gasChart.update('none');
                        console.log(`✅ BME688 가스저항 차트 업데이트 성공`);
                        
                        // 트렌드 선 연속성 보장을 위한 추가 검증
                        const currentDataset = gasChart.data.datasets[sensorIndex];
                        if (currentDataset.data.length >= 2) {
                            // 트렌드 선 설정 강제 적용
                            currentDataset.showLine = true;
                            currentDataset.spanGaps = true;
                            
                            console.log(`📈 BME688 가스저항 트렌드 선 연속성 확인: ${currentDataset.data.length}개 포인트`);
                        }
                        
                        this.errorCount = 0; // 성공 시 에러 카운트 리셋
                    } catch (updateError) {
                        this.errorCount++;
                        console.warn(`⚠️ BME688 가스저항 차트 에러 (${this.errorCount}/${this.maxErrors}): ${updateError.message}`);
                        throw updateError; // 상위 catch에서 처리
                    }
                } else {
                    console.warn(`⚠️ 가스저항 차트 데이터셋[${sensorIndex}] 없음 (총 ${gasChart.data.datasets.length}개 데이터셋)`);
                }
            } else {
                console.warn(`⚠️ 가스저항 차트 'gas-resistance-multi-chart' 없음`);
            }
        }
        
        } catch (chartError) {
            // 모든 Chart.js 에러를 여기서 캐치 (로그 없이 무시)
            this.errorCount++;
            if (this.errorCount < this.maxErrors) {
                // 에러 발생 시 차트 재생성 시도 (조용히)
                setTimeout(() => {
                    this.recreatePressureChart();
                    this.recreateGasChart();
                }, 100);
            }
        } finally {
            // 업데이트 완료 플래그 해제
            this.isUpdating = false;
        }
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