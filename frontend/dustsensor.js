/**
 * SPS30 미세먼지 센서 전용 대시보드
 * ===============================
 * PM1.0, PM2.5, PM4.0, PM10 실시간 모니터링
 */

class DustSensorDashboard {
    constructor() {
        this.config = {
            maxDataPoints: 60,      // 최대 데이터 포인트 (1시간분)
            updateInterval: 2000,   // 2초 간격 업데이트
            reconnectDelay: 5000,   // WebSocket 재연결 지연
            chartRange: '6h'        // 기본 차트 범위
        };

        // 데이터 저장
        this.sensorData = {
            pm1: [],
            pm25: [],
            pm4: [],
            pm10: [],
            timestamps: []
        };

        // 통계 데이터
        this.statistics = {
            today: { pm25: 0, pm10: 0 },
            max: { pm25: 0, pm10: 0 },
            min: { pm25: Infinity, pm10: Infinity }
        };

        // WebSocket 연결
        this.websocket = null;
        this.isConnected = false;

        // 차트 인스턴스
        this.trendChart = null;
        this.comparisonChart = null;

        // 센서 상태
        this.sensorStatus = {
            connected: false,
            serialNumber: null,
            port: null,
            successRate: 0
        };

        this.init();
    }

    async init() {
        console.log('🌪️ SPS30 미세먼지 대시보드 초기화 시작');
        
        try {
            // UI 초기화
            this.initializeUI();
            
            // 차트 초기화
            this.initializeCharts();
            
            // 센서 상태 로드
            await this.loadSensorStatus();
            
            // WebSocket 연결
            this.connectWebSocket();
            
            // 이벤트 리스너 설정
            this.setupEventListeners();
            
            console.log('✅ SPS30 대시보드 초기화 완료');
            
        } catch (error) {
            console.error('❌ 대시보드 초기화 실패:', error);
        } finally {
            this.hideLoading();
        }
    }

    initializeUI() {
        console.log('🎨 UI 초기화 중...');
        
        // 사이드바 토글
        const sidebarToggle = document.getElementById('sidebar-toggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', this.toggleSidebar);
        }

        // 현재 시간 표시
        this.updateTimestamp();
        setInterval(() => this.updateTimestamp(), 1000);
    }

    initializeCharts() {
        console.log('📊 차트 초기화 중...');
        
        // 트렌드 차트
        this.initializeTrendChart();
        
        // 비교 차트
        this.initializeComparisonChart();
    }

    initializeTrendChart() {
        const ctx = document.getElementById('dust-trend-chart');
        if (!ctx) return;

        this.trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'PM1.0',
                        data: [],
                        borderColor: '#FCBF49',
                        backgroundColor: 'rgba(252, 191, 73, 0.1)',
                        borderWidth: 2,
                        tension: 0.4
                    },
                    {
                        label: 'PM2.5',
                        data: [],
                        borderColor: '#E63946',
                        backgroundColor: 'rgba(230, 57, 70, 0.1)',
                        borderWidth: 3,
                        tension: 0.4
                    },
                    {
                        label: 'PM4.0',
                        data: [],
                        borderColor: '#A663CC',
                        backgroundColor: 'rgba(166, 99, 204, 0.1)',
                        borderWidth: 2,
                        tension: 0.4
                    },
                    {
                        label: 'PM10',
                        data: [],
                        borderColor: '#F77F00',
                        backgroundColor: 'rgba(247, 127, 0, 0.1)',
                        borderWidth: 2,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#333'
                        }
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '시간'
                        },
                        grid: {
                            color: '#e0e0e0'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: '농도 (μg/m³)'
                        },
                        beginAtZero: true,
                        grid: {
                            color: '#e0e0e0'
                        }
                    }
                }
            }
        });
    }

    initializeComparisonChart() {
        const ctx = document.getElementById('pm-comparison-chart');
        if (!ctx) return;

        this.comparisonChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['PM1.0', 'PM2.5', 'PM4.0', 'PM10'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        '#FCBF49',
                        '#E63946',
                        '#A663CC',
                        '#F77F00'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            color: '#333'
                        }
                    }
                }
            }
        });
    }

    async loadSensorStatus() {
        try {
            console.log('📡 센서 상태 로딩 중...');
            
            const response = await fetch('/api/sensors/sps30/status');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('📊 센서 상태:', result);
            
            if (result.success && result.status) {
                this.updateSensorInfo(result.status);
                this.sensorStatus.connected = result.status.current_connected;
            } else {
                console.warn('⚠️ 센서 상태 정보 없음');
                this.updateSensorConnection(false);
            }
            
        } catch (error) {
            console.error('❌ 센서 상태 로딩 실패:', error);
            this.updateSensorConnection(false);
        }
    }

    updateSensorInfo(status) {
        // 센서 정보 업데이트
        const elements = {
            'sensor-serial': status.serial_number || '--',
            'sensor-port': status.port_path || '--',
            'success-rate': `${status.success_rate?.toFixed(1) || 0}%`
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });

        // 연결 상태 업데이트
        this.updateSensorConnection(status.current_connected);
    }

    updateSensorConnection(connected) {
        this.sensorStatus.connected = connected;
        
        const connectionElement = document.getElementById('sensor-connection');
        if (connectionElement) {
            connectionElement.textContent = connected 
                ? '센서 연결: 정상' 
                : '센서 연결: 끊어짐';
            connectionElement.className = connected ? 'status-connected' : 'status-disconnected';
        }
    }

    connectWebSocket() {
        try {
            const wsUrl = `ws://${window.location.host}/ws`;
            console.log('🔌 WebSocket 연결 시도:', wsUrl);
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket 연결 성공');
                this.isConnected = true;
                this.updateWebSocketStatus(true);
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('❌ WebSocket 메시지 파싱 실패:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('🔌 WebSocket 연결 종료');
                this.isConnected = false;
                this.updateWebSocketStatus(false);
                
                // 5초 후 재연결 시도
                setTimeout(() => this.connectWebSocket(), this.config.reconnectDelay);
            };
            
            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket 오류:', error);
                this.updateWebSocketStatus(false);
            };
            
        } catch (error) {
            console.error('❌ WebSocket 연결 실패:', error);
            this.updateWebSocketStatus(false);
        }
    }

    handleWebSocketMessage(data) {
        if (data.type === 'sensor_data' && data.data) {
            // SPS30 센서 데이터 찾기
            const sps30Data = data.data.find(sensor => 
                sensor.sensor_type === 'SPS30' && sensor.interface === 'UART'
            );
            
            if (sps30Data && sps30Data.values) {
                this.updateSensorData(sps30Data.values);
                this.updateCharts();
                this.updateStatistics(sps30Data.values);
            }
        }
    }

    updateSensorData(values) {
        const timestamp = new Date().toLocaleTimeString();
        
        // 데이터 추가
        this.sensorData.timestamps.push(timestamp);
        this.sensorData.pm1.push(values.pm1 || 0);
        this.sensorData.pm25.push(values.pm25 || 0);
        this.sensorData.pm4.push(values.pm4 || 0);
        this.sensorData.pm10.push(values.pm10 || 0);
        
        // 최대 데이터 포인트 유지
        if (this.sensorData.timestamps.length > this.config.maxDataPoints) {
            this.sensorData.timestamps.shift();
            this.sensorData.pm1.shift();
            this.sensorData.pm25.shift();
            this.sensorData.pm4.shift();
            this.sensorData.pm10.shift();
        }
        
        // UI 위젯 업데이트
        this.updateWidgets(values);
        
        // 공기질 등급 업데이트
        this.updateAirQuality(values.pm25);
        
        console.log('📊 센서 데이터 업데이트:', values);
    }

    updateWidgets(values) {
        const widgets = {
            'pm1-value': values.pm1?.toFixed(1) || '--',
            'pm25-value': values.pm25?.toFixed(1) || '--',
            'pm4-value': values.pm4?.toFixed(1) || '--',
            'pm10-value': values.pm10?.toFixed(1) || '--'
        };

        Object.entries(widgets).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });

        // 상태 메시지 업데이트
        const status = this.getParticleStatus(values.pm25);
        ['pm1-status', 'pm25-status', 'pm4-status', 'pm10-status'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.textContent = status;
        });
    }

    updateAirQuality(pm25Value) {
        const { grade, description, color } = this.getAirQualityInfo(pm25Value);
        
        const gradeElement = document.getElementById('aqi-grade');
        const descElement = document.getElementById('aqi-description');
        
        if (gradeElement) {
            gradeElement.textContent = grade;
            gradeElement.style.color = color;
        }
        
        if (descElement) {
            descElement.textContent = description;
        }
    }

    getAirQualityInfo(pm25Value) {
        if (pm25Value <= 15) {
            return { grade: '좋음', description: '공기질이 좋습니다', color: '#6A994E' };
        } else if (pm25Value <= 35) {
            return { grade: '보통', description: '민감한 사람은 주의하세요', color: '#F18F01' };
        } else if (pm25Value <= 75) {
            return { grade: '나쁨', description: '외출 시 마스크를 착용하세요', color: '#F77F00' };
        } else {
            return { grade: '매우나쁨', description: '외출을 자제하세요', color: '#E63946' };
        }
    }

    getParticleStatus(pm25Value) {
        if (pm25Value <= 15) return '좋음';
        else if (pm25Value <= 35) return '보통';
        else if (pm25Value <= 75) return '나쁨';
        else return '매우나쁨';
    }

    updateCharts() {
        // 트렌드 차트 업데이트
        if (this.trendChart) {
            this.trendChart.data.labels = this.sensorData.timestamps;
            this.trendChart.data.datasets[0].data = this.sensorData.pm1;
            this.trendChart.data.datasets[1].data = this.sensorData.pm25;
            this.trendChart.data.datasets[2].data = this.sensorData.pm4;
            this.trendChart.data.datasets[3].data = this.sensorData.pm10;
            this.trendChart.update('none');
        }
        
        // 비교 차트 업데이트 (최신값으로)
        if (this.comparisonChart && this.sensorData.pm1.length > 0) {
            const latest = this.sensorData.pm1.length - 1;
            this.comparisonChart.data.datasets[0].data = [
                this.sensorData.pm1[latest] || 0,
                this.sensorData.pm25[latest] || 0,
                this.sensorData.pm4[latest] || 0,
                this.sensorData.pm10[latest] || 0
            ];
            this.comparisonChart.update('none');
        }
    }

    updateStatistics(values) {
        // 오늘 평균 업데이트 (간단히 현재값으로 표시)
        document.getElementById('today-avg-pm25').textContent = `${values.pm25?.toFixed(1) || '--'} μg/m³`;
        document.getElementById('today-avg-pm10').textContent = `${values.pm10?.toFixed(1) || '--'} μg/m³`;
        
        // 최고/최저 값 추적
        if (values.pm25 > this.statistics.max.pm25) {
            this.statistics.max.pm25 = values.pm25;
            document.getElementById('max-pm25').textContent = `${values.pm25.toFixed(1)} μg/m³`;
        }
        
        if (values.pm10 > this.statistics.max.pm10) {
            this.statistics.max.pm10 = values.pm10;
            document.getElementById('max-pm10').textContent = `${values.pm10.toFixed(1)} μg/m³`;
        }
        
        if (values.pm25 < this.statistics.min.pm25) {
            this.statistics.min.pm25 = values.pm25;
            document.getElementById('min-pm25').textContent = `${values.pm25.toFixed(1)} μg/m³`;
        }
        
        if (values.pm10 < this.statistics.min.pm10) {
            this.statistics.min.pm10 = values.pm10;
            document.getElementById('min-pm10').textContent = `${values.pm10.toFixed(1)} μg/m³`;
        }
    }

    updateWebSocketStatus(connected) {
        const statusElement = document.getElementById('websocket-status');
        if (statusElement) {
            statusElement.textContent = connected 
                ? '실시간 연결: 정상' 
                : '실시간 연결: 끊어짐';
            statusElement.className = connected ? 'status-connected' : 'status-disconnected';
        }
    }

    updateTimestamp() {
        const now = new Date();
        const timeString = now.toLocaleString('ko-KR');
        const element = document.getElementById('last-update');
        if (element) {
            element.textContent = `마지막 업데이트: ${timeString}`;
        }
    }

    setupEventListeners() {
        // 차트 범위 버튼
        const rangeButtons = ['1h', '6h', '24h'];
        rangeButtons.forEach(range => {
            const button = document.getElementById(`chart-range-${range}`);
            if (button) {
                button.addEventListener('click', () => this.changeChartRange(range));
            }
        });
    }

    changeChartRange(range) {
        this.config.chartRange = range;
        
        // 버튼 상태 변경
        document.querySelectorAll('.chart-controls .btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`chart-range-${range}`).classList.add('active');
        
        // 차트 데이터 범위 조정 (구현 필요)
        console.log(`📊 차트 범위 변경: ${range}`);
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        
        if (sidebar && mainContent) {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');
        }
    }

    hideLoading() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }
}

// 페이지 로드 시 대시보드 시작
document.addEventListener('DOMContentLoaded', () => {
    window.dustDashboard = new DustSensorDashboard();
});