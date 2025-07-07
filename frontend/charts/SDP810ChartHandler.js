/**
 * SDP810 차트 전용 핸들러
 * ========================
 * SDP810 차압센서의 차트 생성, 업데이트, 관리를 담당
 * CRC 검증 실패 데이터는 skip 처리
 */

class SDP810ChartHandler {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.isInitialized = false;
        this.pendingData = []; // 초기화 전에 받은 데이터 버퍼
        this.sensors = [];
        this.isUpdating = false; // 차트 업데이트 중 플래그
        this.errorCount = 0; // 연속 에러 카운트
        this.maxErrors = 5; // 최대 연속 에러 허용 수
        
        // SDP810ChartHandler 초기화 완료
    }
    
    // SDP810 전체 센서 차트 초기화
    initializeCharts(sensors) {
        console.log(`📊 SDP810 차트 초기화: ${sensors.length}개 센서`);
        
        if (sensors.length === 0) {
            console.warn(`⚠️ SDP810 센서가 없어 차트 생성 중단`);
            return;
        }
        
        // DOM 요소 존재 확인
        const pressureCanvas = document.getElementById('differential-pressure-chart');
        
        if (!pressureCanvas) {
            console.error(`❌ 캔버스 요소 누락, 1초 후 재시도`);
            setTimeout(() => {
                this.initializeCharts(sensors);
            }, 1000);
            return;
        }
        
        // 단일 센서 1:1 차트 라벨 생성 (첫 번째 센서만 사용)
        const primarySensor = sensors[0];
        const pressureLabel = `SDP810-${primarySensor.bus}.${primarySensor.mux_channel} 차압`;
        
        console.log(`📊 SDP810 단일 센서 차트 라벨:`, pressureLabel);
        
        // 단일 센서 차트 생성
        this.createSingleSensorChart('differential-pressure-chart', 'pressure', pressureLabel);
        
        console.log(`✅ SDP810 차트 생성 완료: ${sensors.length}개`);
        
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

    // 단일 센서 차트 생성 (1:1 방식)
    createSingleSensorChart(canvasId, sensorType, label) {
        console.log(`🔧 SDP810 단일 센서 차트 생성 시작: ${canvasId}`);
        console.log(`📊 센서 타입: ${sensorType}, 라벨: ${label}`);
        
        const ctx = document.getElementById(canvasId);
        console.log(`🔍 캔버스 요소 확인 (${canvasId}):`, ctx);
        
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
        
        // 단일 데이터셋 설정 (파란색 계열 - 차압용)
        const dataset = {
            label: label,
            data: [],
            borderColor: '#2196f3',
            backgroundColor: '#2196f320',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            showLine: true,  // 명시적으로 선 표시 활성화
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#2196f3',
            pointBorderWidth: 2,
            spanGaps: true  // 데이터 간격이 있어도 선 연결
        };
        
        try {
            console.log(`📊 Chart.js 단일 센서 차트 생성 시도 중...`);
            
            // 캔버스 및 컨테이너 강제 설정
            const canvas = ctx;
            const chartContainer = canvas.closest('.chart-container');
            const chartCard = canvas.closest('.chart-card');
            const sensorGroup = canvas.closest('.sensor-group');
            
            // 모든 부모 컨테이너 강제 표시
            if (sensorGroup) {
                sensorGroup.style.display = 'block';
            }
            if (chartCard) {
                chartCard.style.display = 'block';
                chartCard.style.visibility = 'visible';
            }
            if (chartContainer) {
                chartContainer.style.display = 'block';
                chartContainer.style.height = '300px';
                chartContainer.style.minHeight = '300px';
            }
            
            // 캔버스 자체 크기 강제 설정
            canvas.style.display = 'block';
            canvas.style.width = '100%';
            canvas.style.height = '300px';
            canvas.width = chartContainer ? chartContainer.clientWidth : 400;
            canvas.height = 300;
            
            this.dashboard.charts[canvasId] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [dataset]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    elements: {
                        line: {
                            tension: 0.4,
                            borderWidth: 2
                        },
                        point: {
                            radius: 3,
                            hoverRadius: 6
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
                                text: '차압 (Pa)'
                            },
                            min: -300,
                            max: 300,
                            grid: { 
                                color: 'rgba(0, 0, 0, 0.05)' 
                            },
                            ticks: {
                                callback: function(value) {
                                    // 100 Pa 이후는 100 단위로 표시
                                    if (Math.abs(value) >= 100) {
                                        // 100의 배수만 표시
                                        if (value % 100 === 0) {
                                            return value + ' Pa';
                                        } else {
                                            return null; // 100의 배수가 아니면 표시하지 않음
                                        }
                                    } else {
                                        // 100 Pa 미만은 소수점 표시
                                        if (Math.abs(value) < 1) {
                                            return value.toFixed(3) + ' Pa';
                                        } else {
                                            return value.toFixed(1) + ' Pa';
                                        }
                                    }
                                },
                                stepSize: 50,  // 기본 간격은 50Pa로 설정
                                maxTicksLimit: 13  // 최대 눈금 수 제한 (-300 ~ 300 범위)
                            }
                        }
                    }
                }
            });
            
            console.log(`✅ SDP810 단일 센서 Chart.js 차트 객체 생성 성공: ${canvasId}`);
            
            // 차트 강제 렌더링
            this.dashboard.charts[canvasId].resize();
            this.dashboard.charts[canvasId].update('active');
            
            console.log(`🔄 SDP810 단일 센서 차트 강제 렌더링 완료: ${canvasId}`);
            
        } catch (chartError) {
            console.error(`❌ SDP810 단일 센서 차트 생성 실패: ${chartError.message}`, chartError);
        }
    }

    // SDP810 차트 최종 확인
    verifyCharts() {
        const pressureChart = this.dashboard.charts['differential-pressure-chart'];
        
        if (!pressureChart) {
            console.error('❌ SDP810 차트 생성 실패');
            return;
        }
        
        console.log(`✅ SDP810 차트 초기화 완료`);
    }

    // 실시간 데이터를 차트에 업데이트 (CRC 검증된 데이터만)
    updateChartsWithRealtimeData(sensorId, data, timestamp) {
        console.log(`🔄 SDP810 차트 데이터 업데이트 시작: ${sensorId}`, data);
        
        // sensorId에서 bus와 channel 추출하여 인덱스 찾기
        const sensorIndex = this.findSensorIndex(sensorId);
        
        console.log(`🔍 센서 인덱스 검색 결과: ${sensorId} → ${sensorIndex}`);
        console.log(`📊 현재 등록된 센서들:`, this.sensors);
        
        if (sensorIndex === -1) {
            console.warn(`⚠️ SDP810 센서 인덱스 찾기 실패: ${sensorId}`);
            console.warn(`📊 검색 대상 센서들:`, this.sensors.map(s => ({bus: s.bus, mux_channel: s.mux_channel})));
            return;
        }
        
        // 차트 직접 업데이트
        this.updateChartDataDirectly(sensorId, data, timestamp, sensorIndex);
    }
    
    // 센서 ID로부터 차트 인덱스 찾기
    findSensorIndex(sensorId) {
        console.log(`🔍 센서 인덱스 검색 시작: ${sensorId}`);
        
        // sensorId 형식: "sdp810_1_4" (prefix_bus_channel)
        const parts = sensorId.split('_');
        console.log(`🔍 센서 ID 분할 결과:`, parts);
        
        if (parts.length < 3) {
            console.warn(`⚠️ 잘못된 센서 ID 형식: ${sensorId}, 부분 개수: ${parts.length}`);
            return -1;
        }
        
        const bus = parseInt(parts[1]);
        const channel = parseInt(parts[2]);
        console.log(`🔍 추출된 버스/채널: bus=${bus}, channel=${channel}`);
        
        // 초기화된 센서 목록에서 해당 센서의 인덱스 찾기
        const index = this.sensors.findIndex(sensor => 
            sensor.bus === bus && sensor.mux_channel === channel
        );
        
        console.log(`🔍 센서 인덱스 검색 완료: ${sensorId} → ${index}`);
        return index;
    }
    
    // 차트에 직접 데이터 업데이트 (SDP810 전용)
    updateChartDataDirectly(sensorId, data, timestamp, sensorIndex) {
        console.log(`🔄 SDP810 차트 직접 업데이트 시작: sensorIndex=${sensorIndex}`, data);
        
        // 연속 에러가 너무 많으면 업데이트 중단
        if (this.errorCount >= this.maxErrors) {
            console.warn(`⚠️ SDP810 차트 에러 한계 도달 (${this.errorCount}/${this.maxErrors}), 업데이트 중단`);
            return;
        }
        
        // 이미 업데이트 중이면 건너뜀 (동시 업데이트 방지)
        if (this.isUpdating) {
            return;
        }
        
        this.isUpdating = true;
        
        // 차압 차트 업데이트 (단일 센서 1:1 방식)
        if (data.pressure !== undefined) {
            console.log(`📊 차압 데이터 업데이트 시작: ${data.pressure} Pa`);
            const pressureChart = this.dashboard.charts['differential-pressure-chart'];
            console.log(`📊 차압 차트 객체 확인:`, {
                exists: !!pressureChart,
                hasData: !!(pressureChart && pressureChart.data),
                hasDatasets: !!(pressureChart && pressureChart.data && pressureChart.data.datasets),
                datasetCount: pressureChart && pressureChart.data && pressureChart.data.datasets ? pressureChart.data.datasets.length : 0
            });
            
            if (pressureChart && pressureChart.data && pressureChart.data.datasets) {
                // 단일 센서이므로 항상 인덱스 0 사용
                const datasetIndex = 0;
                console.log(`📊 단일 센서 데이터셋[${datasetIndex}] 존재 여부:`, !!pressureChart.data.datasets[datasetIndex]);
                if (pressureChart.data.datasets[datasetIndex]) {
                    // 현재 데이터 길이 확인
                    const currentDataLength = pressureChart.data.datasets[datasetIndex].data.length;
                    console.log(`📊 현재 데이터 개수: ${currentDataLength}개`);
                    
                    // 30개 이상이면 첫 번째 데이터 제거 (슬라이딩 윈도우)
                    if (currentDataLength >= 30) {
                        pressureChart.data.datasets[datasetIndex].data.shift();
                        pressureChart.data.labels.shift();
                        console.log(`📊 30개 초과로 첫 번째 데이터 제거됨`);
                    }
                    
                    // 연속적인 X축 값 생성 (시간 기반)
                    const nextXValue = currentDataLength >= 30 ? 29 : currentDataLength;
                    
                    // 새 데이터 포인트 추가
                    const newDataPoint = {
                        x: nextXValue,
                        y: data.pressure
                    };
                    console.log(`📊 새 데이터 포인트 추가:`, newDataPoint);
                    
                    // 데이터와 레이블 동시 추가
                    pressureChart.data.datasets[datasetIndex].data.push(newDataPoint);
                    pressureChart.data.labels.push(nextXValue);
                    
                    // 데이터 포인트가 2개 이상일 때만 선 표시
                    const dataPointCount = pressureChart.data.datasets[datasetIndex].data.length;
                    if (dataPointCount >= 2) {
                        pressureChart.data.datasets[datasetIndex].showLine = true;
                        pressureChart.data.datasets[datasetIndex].pointRadius = 3;
                        console.log(`📈 트렌드 선 활성화: ${dataPointCount}개 데이터 포인트`);
                    } else {
                        console.log(`📊 단일 데이터 포인트: ${dataPointCount}개 (선 대기 중)`);
                    }
                    
                    console.log(`📊 현재 데이터셋 길이: ${pressureChart.data.datasets[datasetIndex].data.length}`);
                    
                    try {
                        pressureChart.update('none');
                        console.log(`✅ SDP810 차압 차트 업데이트 성공`);
                        
                        // 업데이트 후 차트 실제 렌더링 상태 확인
                        try {
                            const canvas = document.getElementById('differential-pressure-chart');
                            if (canvas && pressureChart) {
                                const currentDataset = pressureChart.data.datasets[datasetIndex];
                                console.log(`🔎 차트 업데이트 후 상태:`, {
                                    chartVisible: canvas.style.display !== 'none',
                                    dataPointCount: currentDataset.data.length,
                                    showLine: currentDataset.showLine,
                                    borderWidth: currentDataset.borderWidth,
                                    lastDataPoint: currentDataset.data[currentDataset.data.length - 1],
                                    firstDataPoint: currentDataset.data.length > 0 ? currentDataset.data[0] : null,
                                    canvasInDOM: document.body.contains(canvas),
                                    canvasDisplay: getComputedStyle(canvas).display,
                                    chartType: pressureChart.config.type
                                });
                                
                                // 트렌드 선이 보이지 않는 경우 강제 설정
                                if (currentDataset.data.length >= 2 && !currentDataset.showLine) {
                                    console.log(`🔧 트렌드 선 강제 활성화`);
                                    currentDataset.showLine = true;
                                    pressureChart.update('none');
                                }
                            }
                        } catch (updateCheckError) {
                            console.error(`❌ 차트 업데이트 상태 확인 실패: ${updateCheckError.message}`);
                        }
                        
                        this.errorCount = 0; // 성공 시 에러 카운트 리셋
                    } catch (updateError) {
                        this.errorCount++;
                        console.warn(`⚠️ SDP810 차압 차트 에러 (${this.errorCount}/${this.maxErrors}): ${updateError.message}`);
                        // 차트 재생성 시도
                        if (this.errorCount < this.maxErrors) {
                            setTimeout(() => {
                                this.recreateChart();
                            }, 100);
                        }
                    }
                } else {
                    console.warn(`⚠️ 차압 차트 데이터셋[${datasetIndex}] 없음 (총 ${pressureChart.data.datasets.length}개 데이터셋)`);
                }
            } else {
                console.warn(`⚠️ 차압 차트 'differential-pressure-chart' 없음`);
            }
        }
        
        // 업데이트 완료 플래그 해제
        this.isUpdating = false;
    }

    // 대기 중인 데이터 버퍼에 추가
    bufferData(sensorId, data, timestamp) {
        this.pendingData.push({ sensorId, data, timestamp });
        console.log(`📦 SDP810 데이터 버퍼에 추가: ${sensorId} (총 ${this.pendingData.length}개)`);
    }
    
    // 대기 중인 데이터 처리
    processPendingData() {
        if (this.pendingData.length === 0) {
            console.log(`✅ SDP810 대기 데이터 없음`);
            return;
        }
        
        console.log(`🔄 SDP810 대기 데이터 ${this.pendingData.length}개 처리 시작`);
        
        const dataToProcess = [...this.pendingData];
        this.pendingData = []; // 버퍼 초기화
        
        dataToProcess.forEach(({ sensorId, data, timestamp }) => {
            this.updateChartsWithRealtimeData(sensorId, data, timestamp);
        });
        
        console.log(`✅ SDP810 대기 데이터 처리 완료`);
    }

    // 초기화 상태 확인
    isReady() {
        return this.isInitialized;
    }
    
    // 차트 재생성 (오류 복구용)
    recreateChart() {
        console.log(`🔄 SDP810 차트 재생성 시도`);
        try {
            // 기존 차트 완전 제거
            const existingChart = this.dashboard.charts['differential-pressure-chart'];
            if (existingChart) {
                existingChart.destroy();
                delete this.dashboard.charts['differential-pressure-chart'];
            }
            
            // DOM 요소 확인 후 재생성
            const canvas = document.getElementById('differential-pressure-chart');
            if (canvas && canvas.ownerDocument) {
                const pressureLabels = this.sensors.map(sensor => 
                    `SDP810-${sensor.bus}.${sensor.mux_channel} 차압`
                );
                this.createSingleSensorChart('differential-pressure-chart', 'pressure', pressureLabels[0]);
                console.log(`✅ SDP810 차트 재생성 완료`);
            } else {
                console.warn(`⚠️ SDP810 차트 DOM 요소 없음, 재생성 건너뜀`);
            }
        } catch (error) {
            console.error(`❌ SDP810 차트 재생성 실패: ${error.message}`);
        }
    }
}

// 전역으로 내보내기
window.SDP810ChartHandler = SDP810ChartHandler;