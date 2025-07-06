/**
 * 차트 관리자 - 통합 차트 생성 및 관리
 * =====================================
 * 모든 센서 타입의 차트 생성, 업데이트, 삭제를 중앙 집중식으로 관리
 */

class ChartManager {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.charts = {}; // 차트 인스턴스 저장
        this.colorPalette = [
            '#ff6384', '#36a2eb', '#4bc0c0', '#ff9f40', '#9966ff',
            '#ff6384', '#c9cbcf', '#4bc0c0', '#ff9f40', '#9966ff'
        ];
        
        console.log('📊 ChartManager 초기화 완료');
    }
    
    // 멀티 센서 차트 생성 (기존 dashboard.js에서 이동)
    createMultiSensorChart(chartId, sensorType, sensorLabels) {
        console.log(`📊 멀티 센서 차트 생성: ${chartId}, 타입: ${sensorType}, 라벨 수: ${sensorLabels.length}`);
        console.log(`📊 라벨 상세:`, sensorLabels);
        
        // 중복 생성 방지
        if (this.charts[chartId]) {
            console.warn(`⚠️ ${sensorType} 차트 ${chartId} 이미 ${this.charts[chartId].data.datasets.length}개 데이터셋으로 생성됨, 중복 생성 방지`);
            return;
        }
        
        const canvas = document.getElementById(chartId);
        if (!canvas) {
            console.error(`❌ 캔버스 요소 없음: ${chartId}`);
            return;
        }
        
        const sensorConfig = this.dashboard.sensorTypes[sensorType];
        if (!sensorConfig) {
            console.error(`❌ 센서 설정 없음: ${sensorType}`);
            return;
        }
        
        // 기존 차트 정리
        const existingChart = Chart.getChart(chartId);
        if (existingChart) {
            existingChart.destroy();
        }
        
        // 데이터셋 생성
        const datasets = sensorLabels.map((label, index) => ({
            label: label,
            data: [],
            borderColor: this.colorPalette[index % this.colorPalette.length],
            backgroundColor: this.colorPalette[index % this.colorPalette.length] + '20',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 5,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: this.colorPalette[index % this.colorPalette.length],
            pointBorderWidth: 2
        }));
        
        console.log(`📊 실제 생성된 데이터셋:`, datasets.map((d, i) => `${i}: ${d.label}`));
        
        // Chart.js 인스턴스 생성
        this.charts[chartId] = new Chart(canvas, {
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
        
        // dashboard의 charts에도 참조 저장 (기존 코드 호환성)
        this.dashboard.charts[chartId] = this.charts[chartId];
        
        console.log(`✅ 멀티 센서 차트 생성 완료: ${chartId} (${datasets.length}개 데이터셋)`);
    }
    
    // 차트에 데이터 추가
    addDataToChart(chartId, datasetIndex, value, timestamp) {
        const chart = this.charts[chartId];
        if (!chart) {
            console.warn(`⚠️ 차트 없음: ${chartId}`);
            return;
        }
        
        if (!chart.data.datasets[datasetIndex]) {
            console.warn(`⚠️ 데이터셋 인덱스 ${datasetIndex} 없음 (${chartId})`);
            return;
        }
        
        const time = new Date(timestamp * 1000).toLocaleTimeString();
        
        // 레이블과 데이터 추가
        if (datasetIndex === 0) {
            // 첫 번째 데이터셋일 때만 레이블 추가
            chart.data.labels.push(time);
        }
        
        chart.data.datasets[datasetIndex].data.push(value);
        
        // 최대 데이터 포인트 제한
        if (chart.data.labels.length > this.dashboard.config.maxDataPoints) {
            if (datasetIndex === 0) {
                chart.data.labels.shift();
            }
            chart.data.datasets[datasetIndex].data.shift();
        }
        
        chart.update('none');
    }
    
    // 차트 삭제
    destroyChart(chartId) {
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
            delete this.charts[chartId];
            delete this.dashboard.charts[chartId];
            console.log(`🗑️ 차트 삭제됨: ${chartId}`);
        }
    }
    
    // 모든 차트 삭제
    destroyAllCharts() {
        Object.keys(this.charts).forEach(chartId => {
            this.destroyChart(chartId);
        });
        console.log(`🗑️ 모든 차트 삭제됨`);
    }
    
    // 차트 존재 확인
    hasChart(chartId) {
        return !!this.charts[chartId];
    }
    
    // 차트 가져오기
    getChart(chartId) {
        return this.charts[chartId];
    }
    
    // 차트 상태 확인
    getChartStatus() {
        const status = {};
        Object.keys(this.charts).forEach(chartId => {
            const chart = this.charts[chartId];
            status[chartId] = {
                exists: !!chart,
                datasets: chart ? chart.data.datasets.length : 0,
                labels: chart ? chart.data.labels.length : 0
            };
        });
        return status;
    }
}

// 전역으로 내보내기
window.ChartManager = ChartManager;