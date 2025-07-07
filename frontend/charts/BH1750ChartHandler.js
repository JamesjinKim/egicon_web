/**
 * BH1750 차트 전용 핸들러
 * ========================
 * BH1750 조도 센서의 차트 생성, 업데이트, 관리를 담당
 */

class BH1750ChartHandler {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.isInitialized = false;
        this.pendingData = []; // 초기화 전에 받은 데이터 버퍼
        this.sensors = [];
        this.isUpdating = false; // 차트 업데이트 중 플래그
        this.errorCount = 0; // 연속 에러 카운트
        this.maxErrors = 5; // 최대 연속 에러 허용 수
        
        // BH1750ChartHandler 초기화 완료
    }
    
    // BH1750 전체 센서 차트 초기화
    initializeCharts(sensors) {
        console.log(`📊 BH1750 차트 초기화: ${sensors.length}개 센서`);
        
        if (sensors.length === 0) {
            console.warn(`⚠️ BH1750 센서가 없어 차트 생성 중단`);
            return;
        }
        
        // DOM 요소 존재 확인
        const lightCanvas = document.getElementById('light-multi-chart');
        
        if (!lightCanvas) {
            console.error(`❌ 캔버스 요소 누락, 1초 후 재시도`);
            setTimeout(() => {
                this.initializeCharts(sensors);
            }, 1000);
            return;
        }
        
        // 모든 센서에 대한 라벨 생성
        const lightLabels = sensors.map(sensor => 
            `BH1750-${sensor.bus}.${sensor.mux_channel} 조도`
        );
        
        console.log(`📊 BH1750 차트 라벨:`, lightLabels);
        
        // 멀티 센서 차트 생성
        this.createMultiSensorChart('light-multi-chart', 'light', lightLabels);
        
        console.log(`✅ BH1750 차트 생성 완료: ${sensors.length}개`);
        
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

    // 멀티 센서 차트 생성 (여러 데이터셋)
    createMultiSensorChart(canvasId, sensorType, labels) {
        console.log(`🔧 BH1750 멀티 센서 차트 생성 시작: ${canvasId}`);
        console.log(`📊 센서 타입: ${sensorType}, 라벨 개수: ${labels.length}`);
        console.log(`📊 전달된 라벨들:`, labels);
        
        const ctx = document.getElementById(canvasId);
        console.log(`🔍 캔버스 요소 확인 (${canvasId}):`, ctx);
        console.log(`🔍 캔버스 요소 속성:`, ctx ? {
            id: ctx.id,
            width: ctx.width,
            height: ctx.height,
            display: getComputedStyle(ctx).display,
            visibility: getComputedStyle(ctx).visibility
        } : 'null');
        
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
        
        // 컬러 팔레트 (노란색 계열)
        const colorPalette = [
            '#ffd700', '#ffeb3b', '#fff176', '#ffcc02', '#ffc107',
            '#ff9800', '#ffb74d', '#ffa000', '#f57f17', '#f9a825'
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
        
        // 실제 생성된 데이터셋
        
        try {
            console.log(`📊 Chart.js 차트 생성 시도 중...`);
            console.log(`📊 데이터셋 미리보기:`, datasets.map(d => ({ label: d.label, dataLength: d.data.length })));
            
            // 차트 생성 전 캔버스 크기 강제 설정
            ctx.width = ctx.parentElement.clientWidth || 400;
            ctx.height = ctx.parentElement.clientHeight || 300;
            console.log(`📐 캔버스 크기 설정: ${ctx.width}x${ctx.height}`);
            
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
                                text: '조도 (lux)'
                            },
                            min: 0,
                            max: 10000,
                            grid: { 
                                color: 'rgba(0, 0, 0, 0.05)' 
                            }
                        }
                    }
                }
            });
            
            console.log(`✅ BH1750 Chart.js 차트 객체 생성 성공: ${canvasId}`);
            
            // 단계별 디버깅으로 오류 지점 특정
            try {
                console.log(`🔍 1단계: 생성된 차트 확인`);
                console.log(`📊 생성된 차트:`, this.dashboard.charts[canvasId]);
                console.log(`📊 데이터셋 개수: ${datasets.length}`);
            } catch (step1Error) {
                console.error(`❌ 1단계 실패:`, step1Error.message);
            }
            
            try {
                console.log(`🔍 2단계: 캔버스 상태 확인`);
                console.log(`📊 차트 캔버스 상태:`, {
                    chartExists: !!this.dashboard.charts[canvasId],
                    canvasWidth: ctx.width,
                    canvasHeight: ctx.height,
                    isVisible: getComputedStyle(ctx).display !== 'none'
                });
            } catch (step2Error) {
                console.error(`❌ 2단계 실패:`, step2Error.message);
            }
            
            try {
                console.log(`🔍 3단계: DOM 요소 찾기`);
                const canvas = document.getElementById(canvasId);
                console.log(`📊 캔버스 요소:`, !!canvas);
                
                if (canvas) {
                    console.log(`🔍 4단계: 컨테이너 요소 찾기`);
                    const chartContainer = canvas.closest('.chart-container');
                    const chartCard = canvas.closest('.chart-card');
                    console.log(`📊 컨테이너들:`, {
                        chartContainer: !!chartContainer,
                        chartCard: !!chartCard
                    });
                    
                    console.log(`🔍 5단계: CSS 스타일 확인`);
                    console.log(`🖼️ 차트 캔버스 표시 상태:`, {
                        canvasId: canvasId,
                        canvasSize: {width: canvas.width, height: canvas.height},
                        canvasStyle: {
                            display: getComputedStyle(canvas).display,
                            visibility: getComputedStyle(canvas).visibility,
                            width: getComputedStyle(canvas).width,
                            height: getComputedStyle(canvas).height
                        }
                    });
                }
            } catch (step3Error) {
                console.error(`❌ 3-5단계 실패:`, step3Error.message);
                console.error(step3Error.stack);
            }
            
            try {
                console.log(`🔍 6단계: 차트 렌더링`);
                this.dashboard.charts[canvasId].resize();
                this.dashboard.charts[canvasId].update();
                console.log(`🔄 BH1750 차트 강제 렌더링 완료: ${canvasId}`);
            } catch (step6Error) {
                console.error(`❌ 6단계 실패:`, step6Error.message);
            }
            
        } catch (chartError) {
            console.error(`❌ BH1750 차트 생성 실패: ${chartError.message}`);
            console.error('차트 생성 상세 에러:', chartError);
            console.error('Stack trace:', chartError.stack);
        }
        
        // 멀티 센서 차트 생성 완료
    }

    // BH1750 차트 최종 확인
    verifyCharts() {
        const lightChart = this.dashboard.charts['light-multi-chart'];
        
        if (!lightChart) {
            console.error('❌ BH1750 차트 생성 실패');
            return;
        }
        
        console.log(`✅ BH1750 차트 초기화 완료`);
    }

    // 실시간 데이터를 차트에 업데이트
    updateChartsWithRealtimeData(sensorId, data, timestamp) {
        console.log(`🔄 BH1750 차트 데이터 업데이트 시작: ${sensorId}`, data);
        
        // sensorId에서 bus와 channel 추출하여 인덱스 찾기
        const sensorIndex = this.findSensorIndex(sensorId);
        
        console.log(`🔍 센서 인덱스 검색 결과: ${sensorId} → ${sensorIndex}`);
        console.log(`📊 현재 등록된 센서들:`, this.sensors);
        
        if (sensorIndex === -1) {
            console.warn(`⚠️ BH1750 센서 인덱스 찾기 실패: ${sensorId}`);
            console.warn(`📊 검색 대상 센서들:`, this.sensors.map(s => ({bus: s.bus, mux_channel: s.mux_channel})));
            return;
        }
        
        // 차트 직접 업데이트
        this.updateChartDataDirectly(sensorId, data, timestamp, sensorIndex);
    }
    
    // 센서 ID로부터 차트 인덱스 찾기
    findSensorIndex(sensorId) {
        console.log(`🔍 센서 인덱스 검색 시작: ${sensorId}`);
        
        // sensorId 형식: "bh1750_1_4" (prefix_bus_channel)
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
    
    // 차트에 직접 데이터 업데이트 (BH1750 전용)
    updateChartDataDirectly(sensorId, data, timestamp, sensorIndex) {
        console.log(`🔄 BH1750 차트 직접 업데이트 시작: sensorIndex=${sensorIndex}`, data);
        
        // 연속 에러가 너무 많으면 업데이트 중단
        if (this.errorCount >= this.maxErrors) {
            console.warn(`⚠️ BH1750 차트 에러 한계 도달 (${this.errorCount}/${this.maxErrors}), 업데이트 중단`);
            return;
        }
        
        // 이미 업데이트 중이면 건너뜀 (동시 업데이트 방지)
        if (this.isUpdating) {
            return;
        }
        
        this.isUpdating = true;
        
        // 조도 차트 업데이트
        if (data.light !== undefined) {
            console.log(`📊 조도 데이터 업데이트 시작: ${data.light} lux`);
            const lightChart = this.dashboard.charts['light-multi-chart'];
            console.log(`📊 조도 차트 객체 확인:`, {
                exists: !!lightChart,
                hasData: !!(lightChart && lightChart.data),
                hasDatasets: !!(lightChart && lightChart.data && lightChart.data.datasets),
                datasetCount: lightChart && lightChart.data && lightChart.data.datasets ? lightChart.data.datasets.length : 0
            });
            
            if (lightChart && lightChart.data && lightChart.data.datasets) {
                console.log(`📊 센서 인덱스 ${sensorIndex} 데이터셋 존재 여부:`, !!lightChart.data.datasets[sensorIndex]);
                if (lightChart.data.datasets[sensorIndex]) {
                    // 현재 데이터 길이 확인
                    const currentDataLength = lightChart.data.datasets[sensorIndex].data.length;
                    
                    // X축 위치 계산 (30개 범위 내에서 슬라이딩)
                    let xPosition = currentDataLength;
                    if (currentDataLength >= 30) {
                        // 30개 이후부터는 슬라이딩 윈도우 적용
                        xPosition = 29; // 마지막 위치에 고정
                        // 기존 데이터를 왼쪽으로 이동
                        lightChart.data.datasets[sensorIndex].data.forEach((point, index) => {
                            if (point && typeof point === 'object') {
                                point.x = index;
                            }
                        });
                    }
                    
                    // 첫 번째 센서만 X축 레이블 관리
                    if (sensorIndex === 0) {
                        if (currentDataLength < 30) {
                            lightChart.data.labels.push(currentDataLength);
                        }
                    }
                    
                    // 새 데이터 추가
                    const newDataPoint = {
                        x: xPosition,
                        y: data.light
                    };
                    console.log(`📊 새 데이터 포인트 추가:`, newDataPoint);
                    lightChart.data.datasets[sensorIndex].data.push(newDataPoint);
                    
                    // 30개 이상이면 첫 번째 데이터 제거
                    if (lightChart.data.datasets[sensorIndex].data.length > 30) {
                        lightChart.data.datasets[sensorIndex].data.shift();
                        console.log(`📊 30개 초과로 첫 번째 데이터 제거됨`);
                    }
                    
                    console.log(`📊 현재 데이터셋 길이: ${lightChart.data.datasets[sensorIndex].data.length}`);
                    
                    try {
                        lightChart.update('none');
                        console.log(`✅ BH1750 조도 차트 업데이트 성공`);
                        
                        // 업데이트 후 차트 실제 렌더링 상태 확인 (즉시 실행)
                        try {
                            const canvas = document.getElementById('light-multi-chart');
                            if (canvas && lightChart) {
                                console.log(`🔎 차트 업데이트 후 상태:`, {
                                    chartVisible: canvas.style.display !== 'none',
                                    chartData: lightChart.data.datasets[sensorIndex].data.length,
                                    lastDataPoint: lightChart.data.datasets[sensorIndex].data[lightChart.data.datasets[sensorIndex].data.length - 1],
                                    canvasInDOM: document.body.contains(canvas),
                                    canvasDisplay: getComputedStyle(canvas).display,
                                    canvasVisibility: getComputedStyle(canvas).visibility
                                });
                            }
                        } catch (updateCheckError) {
                            console.error(`❌ 차트 업데이트 상태 확인 실패: ${updateCheckError.message}`);
                        }
                        
                        this.errorCount = 0; // 성공 시 에러 카운트 리셋
                    } catch (updateError) {
                        this.errorCount++;
                        console.warn(`⚠️ BH1750 조도 차트 에러 (${this.errorCount}/${this.maxErrors}): ${updateError.message}`);
                        // 차트 재생성 시도
                        if (this.errorCount < this.maxErrors) {
                            setTimeout(() => {
                                this.recreateChart();
                            }, 100);
                        }
                    }
                } else {
                    console.warn(`⚠️ 조도 차트 데이터셋[${sensorIndex}] 없음 (총 ${lightChart.data.datasets.length}개 데이터셋)`);
                }
            } else {
                console.warn(`⚠️ 조도 차트 'light-multi-chart' 없음`);
            }
        }
        
        // 업데이트 완료 플래그 해제
        this.isUpdating = false;
    }

    // 대기 중인 데이터 버퍼에 추가
    bufferData(sensorId, data, timestamp) {
        this.pendingData.push({ sensorId, data, timestamp });
        console.log(`📦 BH1750 데이터 버퍼에 추가: ${sensorId} (총 ${this.pendingData.length}개)`);
    }
    
    // 대기 중인 데이터 처리
    processPendingData() {
        if (this.pendingData.length === 0) {
            console.log(`✅ BH1750 대기 데이터 없음`);
            return;
        }
        
        console.log(`🔄 BH1750 대기 데이터 ${this.pendingData.length}개 처리 시작`);
        
        const dataToProcess = [...this.pendingData];
        this.pendingData = []; // 버퍼 초기화
        
        dataToProcess.forEach(({ sensorId, data, timestamp }) => {
            this.updateChartsWithRealtimeData(sensorId, data, timestamp);
        });
        
        console.log(`✅ BH1750 대기 데이터 처리 완료`);
    }

    // 초기화 상태 확인
    isReady() {
        return this.isInitialized;
    }
    
    // 차트 재생성 (오류 복구용)
    recreateChart() {
        console.log(`🔄 BH1750 차트 재생성 시도`);
        try {
            // 기존 차트 완전 제거
            const existingChart = this.dashboard.charts['light-multi-chart'];
            if (existingChart) {
                existingChart.destroy();
                delete this.dashboard.charts['light-multi-chart'];
            }
            
            // DOM 요소 확인 후 재생성
            const canvas = document.getElementById('light-multi-chart');
            if (canvas && canvas.ownerDocument) {
                const lightLabels = this.sensors.map(sensor => 
                    `BH1750-${sensor.bus}.${sensor.mux_channel} 조도`
                );
                this.createMultiSensorChart('light-multi-chart', 'light', lightLabels);
                console.log(`✅ BH1750 차트 재생성 완료`);
            } else {
                console.warn(`⚠️ BH1750 차트 DOM 요소 없음, 재생성 건너뜀`);
            }
        } catch (error) {
            console.error(`❌ BH1750 차트 재생성 실패: ${error.message}`);
        }
    }
}

// 전역으로 내보내기
window.BH1750ChartHandler = BH1750ChartHandler;