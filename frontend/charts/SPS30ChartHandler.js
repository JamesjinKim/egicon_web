/**
 * SPS30 차트 전용 핸들러
 * ========================
 * SPS30 미세먼지 센서의 차트 생성, 업데이트, 관리를 담당
 */

class SPS30ChartHandler {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.isInitialized = false;
        
        // SPS30ChartHandler 초기화 완료
    }
    
    // SPS30 차트 초기화
    initializeCharts() {
        console.log('📊 SPS30 차트 초기화 시작');
        
        // 메인 차트가 있다면 초기화
        this.createMainChart();
        
        this.isInitialized = true;
        console.log('✅ SPS30 차트 초기화 완료');
    }
    
    // SPS30 메인 차트 생성
    createMainChart() {
        const canvasId = 'sps30-main-chart';
        const canvas = document.getElementById(canvasId);
        
        if (!canvas) {
            // 메인 차트 캔버스가 없으면 생성하지 않음
            return;
        }
        
        // 기존 차트 파괴
        const existingChart = Chart.getChart(canvasId);
        if (existingChart) {
            existingChart.destroy();
        }
        
        if (this.dashboard.charts[canvasId]) {
            delete this.dashboard.charts[canvasId];
        }
        
        // Chart.js 차트 생성
        this.dashboard.charts[canvasId] = new Chart(canvas, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'PM2.5 (μg/m³)',
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
                    },
                    {
                        label: 'PM10 (μg/m³)',
                        data: [],
                        borderColor: '#36a2eb',
                        backgroundColor: '#36a2eb20',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        pointRadius: 2,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#ffffff',
                        pointBorderColor: '#36a2eb',
                        pointBorderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'SPS30 미세먼지 트렌드'
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
                            text: '농도 (μg/m³)'
                        },
                        min: 0,
                        max: 200,
                        grid: { 
                            color: 'rgba(0, 0, 0, 0.05)' 
                        }
                    }
                }
            }
        });
        
        console.log('✅ SPS30 메인 차트 생성 완료');
    }
    
    // 차트 데이터 업데이트
    updateChart(values) {
        const chart = this.dashboard.charts['sps30-main-chart'];
        if (!chart) {
            return;
        }
        
        try {
            // 현재 데이터 길이 확인
            const currentDataLength = chart.data.datasets[0].data.length;
            
            // X축 위치 계산 (30개 범위 내에서 슬라이딩)
            let xPosition = currentDataLength;
            if (currentDataLength >= 30) {
                // 30개 이후부터는 슬라이딩 윈도우 적용
                xPosition = 29; // 마지막 위치에 고정
                // 기존 데이터를 왼쪽으로 이동
                chart.data.datasets.forEach(dataset => {
                    dataset.data.forEach((point, index) => {
                        if (point && typeof point === 'object') {
                            point.x = index;
                        }
                    });
                });
            }
            
            // X축 레이블 관리
            if (currentDataLength < 30) {
                chart.data.labels.push(currentDataLength);
            }
            
            // PM2.5 데이터 추가
            if (values.pm25 !== undefined) {
                chart.data.datasets[0].data.push({
                    x: xPosition,
                    y: values.pm25
                });
                
                // 30개 이상이면 첫 번째 데이터 제거
                if (chart.data.datasets[0].data.length > 30) {
                    chart.data.datasets[0].data.shift();
                }
            }
            
            // PM10 데이터 추가
            if (values.pm10 !== undefined) {
                chart.data.datasets[1].data.push({
                    x: xPosition,
                    y: values.pm10
                });
                
                // 30개 이상이면 첫 번째 데이터 제거
                if (chart.data.datasets[1].data.length > 30) {
                    chart.data.datasets[1].data.shift();
                }
            }
            
            // 레이블 관리 (30개 이상이면 제거)
            if (chart.data.labels.length > 30) {
                chart.data.labels.shift();
            }
            
            chart.update('none');
            // SPS30 차트 업데이트 완료
            
        } catch (error) {
            console.warn('⚠️ SPS30 차트 업데이트 에러:', error.message);
        }
    }
    
    // 초기화 상태 확인
    isReady() {
        return this.isInitialized;
    }
    
    // 차트 재생성 (오류 복구용)
    recreateChart() {
        console.log('🔄 SPS30 차트 재생성 시도');
        try {
            this.createMainChart();
            console.log('✅ SPS30 차트 재생성 완료');
        } catch (error) {
            console.error('❌ SPS30 차트 재생성 실패:', error.message);
        }
    }
}

// 전역으로 내보내기
window.SPS30ChartHandler = SPS30ChartHandler;