/**
 * EG-ICON Dashboard - 센서 그룹핑 시스템
 * ==========================================
 * egicon_dash 기반 + 센서 그룹별 관리
 * 성능 최적화: 메모리 > 실시간성 > 응답속도
 */

class EGIconDashboard {
    constructor() {
        // 성능 최적화 설정
        this.config = {
            maxDataPoints: 30,        // 메모리 최적화: 차트 데이터 포인트 제한
            updateInterval: 2000,     // 실시간성: 2초 간격 업데이트
            batchSize: 4,            // 응답속도: 배치 처리 크기
            enableAnimations: true,   // 모던 차트 애니메이션
        };

        // 센서 그룹 정의 (b.png 기준)
        this.sensorGroups = {
            "SHT40": {
                title: "SHT40 온습도 센서",
                icon: "🌡️",
                sensors: ["temperature_1", "humidity_1"],
                containerId: "sht40-widgets"
            },
            "BME688": {
                title: "BME688 환경센서",
                icon: "🍃",
                sensors: ["temperature_2", "humidity_2", "pressure_1", "airquality_1"],
                containerId: "bme688-widgets"
            },
            "기타": {
                title: "기타 센서",
                icon: "☀️",
                sensors: ["light_1", "vibration_1"],
                containerId: "other-widgets"
            }
        };

        // 센서 설정
        this.sensorTypes = {
            temperature: {
                label: '온도',
                icon: '🌡️',
                unit: '°C',
                color: '#ff6384',
                min: -10,
                max: 50
            },
            humidity: {
                label: '습도',
                icon: '💧',
                unit: '%',
                color: '#36a2eb',
                min: 0,
                max: 100
            },
            pressure: {
                label: '압력',
                icon: '📏',
                unit: 'hPa',
                color: '#4bc0c0',
                min: 950,
                max: 1050
            },
            light: {
                label: '조도',
                icon: '☀️',
                unit: 'lux',
                color: '#ffce56',
                min: 0,
                max: 2000
            },
            vibration: {
                label: '진동',
                icon: '〜',
                unit: 'Hz',
                color: '#9966ff',
                min: 0,
                max: 100
            },
            airquality: {
                label: '공기질',
                icon: '🍃',
                unit: '/100',
                color: '#00d084',
                min: 0,
                max: 100
            }
        };

        // 데이터 저장소 (메모리 최적화)
        this.sensorData = {};
        this.charts = {};
        this.connectedSensors = new Set();
        
        // WebSocket 연결
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        // Mock 데이터 인터벌
        this.mockDataInterval = null;

        this.init();
    }

    async init() {
        this.hideLoading();
        this.initSensorData();
        this.generateMockSensors();
        this.initSidebarEvents();
        this.initCharts();
        
        // 실제 센서 데이터 로드 (WebSocket 연결 전)
        await this.loadRealSensorData();
        
        this.startRealtimeConnection();
        this.updateStatusBar();
        
        console.log('🚀 EG-ICON Dashboard 초기화 완료');
    }

    // 센서 데이터 초기화
    initSensorData() {
        Object.keys(this.sensorTypes).forEach(type => {
            this.sensorData[type] = [];
        });
    }

    // Mock 센서 생성 (그룹 기준)
    generateMockSensors() {
        // 각 그룹의 센서들을 connectedSensors에 추가
        Object.values(this.sensorGroups).forEach(group => {
            group.sensors.forEach(sensorId => {
                this.connectedSensors.add(sensorId);
            });
        });
    }

    // 사이드바 이벤트 초기화
    initSidebarEvents() {
        // 사이드바 토글
        const toggleBtn = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.toggle('expanded');
                mainContent.classList.toggle('sidebar-expanded');
            });
        }

        // 메뉴 아이템 클릭 이벤트
        document.querySelectorAll('.menu-item[data-menu]').forEach(item => {
            item.addEventListener('click', (e) => {
                const menu = item.getAttribute('data-menu');
                
                // 설정 메뉴는 페이지 이동을 허용
                if (menu === 'settings') {
                    return; // preventDefault 하지 않고 기본 링크 동작 허용
                }
                
                e.preventDefault();
                
                // 활성 메뉴 변경
                document.querySelectorAll('.menu-item').forEach(menu => {
                    menu.classList.remove('active');
                });
                item.classList.add('active');
                
                // 헤더 제목 변경
                const titles = {
                    'home': 'EG-icon 센서 대시보드',
                    'temperature': '온도 센서 모니터링',
                    'humidity': '습도 센서 모니터링',
                    'light': '조도 센서 모니터링',
                    'pressure': '압력 센서 모니터링',
                    'vibration': '진동 센서 모니터링',
                    'settings': '시스템 설정'
                };
                
                const headerTitle = document.getElementById('header-title');
                if (headerTitle) {
                    headerTitle.textContent = titles[menu] || 'EG-icon 센서 대시보드';
                }
            });
        });

        // 데이터 갱신 버튼
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.updateStatusBar();
                console.log('📊 데이터 갱신됨');
            });
        }
    }

    // 차트 초기화 (그룹별)
    initCharts() {
        // SHT40 차트들
        this.createGroupChart('sht40-temperature-chart', 'temperature', 'SHT40 온도');
        this.createGroupChart('sht40-humidity-chart', 'humidity', 'SHT40 습도');
        
        // BME688 차트들
        this.createGroupChart('bme688-temperature-chart', 'temperature', 'BME688 온도');
        this.createGroupChart('bme688-humidity-chart', 'humidity', 'BME688 습도');
        this.createGroupChart('bme688-pressure-chart', 'pressure', 'BME688 압력');
        this.createGroupChart('bme688-airquality-chart', 'airquality', 'BME688 공기질');
        
        // 기타 센서 차트들
        this.createGroupChart('light-chart', 'light', 'BH1750 조도');
        this.createGroupChart('vibration-chart', 'vibration', '진동센서');
    }

    // 그룹 차트 생성
    createGroupChart(canvasId, sensorType, title) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const sensorConfig = this.sensorTypes[sensorType];
        
        // 그라데이션 생성
        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 200);
        gradient.addColorStop(0, sensorConfig.color + '40');
        gradient.addColorStop(1, sensorConfig.color + '10');

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: title,
                    data: [],
                    borderColor: sensorConfig.color,
                    backgroundColor: gradient,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: sensorConfig.color,
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#333',
                        bodyColor: '#666',
                        borderColor: sensorConfig.color,
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                return `${title}: ${context.parsed.y.toFixed(1)}${sensorConfig.unit}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            maxTicksLimit: 6,
                            color: '#666',
                            font: {
                                size: 10
                            }
                        }
                    },
                    y: {
                        display: true,
                        min: sensorConfig.min,
                        max: sensorConfig.max,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            color: '#666',
                            font: {
                                size: 10
                            },
                            callback: function(value) {
                                return value.toFixed(0) + sensorConfig.unit;
                            }
                        }
                    }
                },
                animation: {
                    duration: 500
                }
            }
        });
    }

    // 실시간 연결 시작
    startRealtimeConnection() {
        // 먼저 로컬 Mock 데이터로 시작
        this.startLocalMockData();
        
        // 그 다음 WebSocket 연결 시도
        setTimeout(() => {
            this.connectWebSocket();
        }, 1000);
    }

    // WebSocket 연결
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/realtime`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('📡 WebSocket 연결됨');
            this.reconnectAttempts = 0;
        };
        
        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.type === 'sensor_data') {
                    this.handleRealtimeData(message.data);
                }
            } catch (error) {
                console.error('WebSocket 메시지 파싱 오류:', error);
            }
        };
        
        this.ws.onclose = () => {
            console.log('📡 WebSocket 연결 종료됨');
            this.attemptReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('📡 WebSocket 오류:', error);
            this.attemptReconnect();
        };
    }

    // 실시간 데이터 처리
    handleRealtimeData(sensorData) {
        const now = new Date();
        
        // WebSocket 데이터로 위젯 및 차트 업데이트
        Object.entries(sensorData).forEach(([sensorId, data]) => {
            this.connectedSensors.add(sensorId);
            this.updateSensorWidget(sensorId, data.value);
            this.updateChartData(data.type, data.value, now);
        });
        
        this.updateStatusBar();
    }

    // 실제 센서 데이터 가져오기
    async loadRealSensorData() {
        try {
            console.log('🔍 실제 센서 데이터 로딩 중...');
            
            const response = await fetch('/api/sensors/real-status');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('📡 실제 센서 데이터:', result);
            
            if (result.sensors && Object.keys(result.sensors).length > 0) {
                // 실제 센서 데이터가 있으면 Mock 데이터와 병합
                this.mergeRealSensorData(result.sensors);
                console.log(`✅ 실제 센서 ${Object.keys(result.sensors).length}개 연결됨`);
            } else {
                console.log('⚠️ 실제 센서 데이터 없음, Mock 데이터 사용');
            }
            
        } catch (error) {
            console.error('❌ 실제 센서 데이터 로딩 실패:', error);
        }
    }

    // 실제 센서 데이터와 Mock 데이터 병합
    mergeRealSensorData(realSensors) {
        Object.entries(realSensors).forEach(([sensorId, sensorData]) => {
            // BH1750 조도 센서의 경우 light_1 위젯 교체
            if (sensorData.type === 'light') {
                // 기존 light_1 Mock 센서를 실제 센서로 교체
                this.replaceMockSensor('light_1', sensorId, sensorData);
                
                // 위젯 제목 업데이트
                const widget = document.querySelector('[data-sensor="light_1"]');
                if (widget) {
                    const titleElement = widget.querySelector('.widget-title');
                    if (titleElement) {
                        titleElement.textContent = `BH1750 조도 (Ch${sensorData.channel + 1})`;
                    }
                    // 실제 센서 ID로 data 속성 변경
                    widget.setAttribute('data-sensor', sensorId);
                    widget.setAttribute('data-real-sensor', 'true');
                }
            }
        });
    }

    // Mock 센서를 실제 센서로 교체
    replaceMockSensor(mockSensorId, realSensorId, realSensorData) {
        // 연결된 센서 목록에서 교체
        this.connectedSensors.delete(mockSensorId);
        this.connectedSensors.add(realSensorId);
        
        // 센서 그룹에서 교체
        Object.values(this.sensorGroups).forEach(group => {
            const index = group.sensors.indexOf(mockSensorId);
            if (index !== -1) {
                group.sensors[index] = realSensorId;
            }
        });
        
        // 차트 데이터에서 교체
        if (this.charts[realSensorData.type]) {
            this.charts[realSensorData.type].data.datasets.forEach(dataset => {
                if (dataset.label.includes(mockSensorId)) {
                    dataset.label = `BH1750 조도 (Ch${realSensorData.channel + 1})`;
                }
            });
        }
        
        console.log(`🔄 Mock 센서 ${mockSensorId}를 실제 센서 ${realSensorId}로 교체됨`);
    }

    // WebSocket 재연결
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`🔄 WebSocket 재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, 1000 * this.reconnectAttempts);
        } else {
            console.error('❌ WebSocket 재연결 포기, 로컬 Mock 데이터로 전환');
            this.startLocalMockData();
        }
    }

    // 로컬 Mock 데이터 시작
    startLocalMockData() {
        if (this.mockDataInterval) return;
        
        console.log('🔄 로컬 Mock 데이터 모드로 전환');
        
        // 첫 번째 데이터 즉시 업데이트
        this.updateMockData();
        
        // 주기적 업데이트 시작
        this.mockDataInterval = setInterval(() => {
            this.updateMockData();
        }, this.config.updateInterval);
    }

    // Mock 데이터 업데이트
    updateMockData() {
        const now = new Date();
        
        // 배치로 센서 데이터 업데이트
        this.connectedSensors.forEach(sensorId => {
            const [type] = sensorId.split('_');
            const mockValue = this.generateMockValue(type, now);
            
            this.updateSensorWidget(sensorId, mockValue);
            this.updateChartData(type, mockValue, now);
        });

        this.updateStatusBar();
    }

    // 센서별 Mock 값 생성
    generateMockValue(sensorType, timestamp) {
        const timeMs = timestamp.getTime();
        
        switch (sensorType) {
            case 'temperature':
                return 20 + 10 * Math.sin(timeMs / 60000) + (Math.random() - 0.5) * 3;
            case 'humidity':
                return 50 + 20 * Math.sin(timeMs / 80000 + 1) + (Math.random() - 0.5) * 5;
            case 'pressure':
                return 1013 + 10 * Math.sin(timeMs / 120000 + 2) + (Math.random() - 0.5) * 2;
            case 'light':
                const hour = timestamp.getHours();
                const daylight = Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
                return daylight * 1500 + Math.random() * 200;
            case 'vibration':
                return Math.random() * 20 + (Math.random() > 0.9 ? Math.random() * 30 : 0);
            case 'airquality':
                return 100 + 50 * Math.sin(timeMs / 180000 + 3) + (Math.random() - 0.5) * 20;
            default:
                return Math.random() * 100;
        }
    }

    // 센서 위젯 업데이트
    updateSensorWidget(sensorId, value) {
        // 센서 ID에 따라 해당 위젯 찾기
        const [type] = sensorId.split('_');
        const unit = this.sensorTypes[type].unit;
        
        // 모든 해당 타입의 위젯을 찾아서 업데이트
        const widgets = document.querySelectorAll(`.sensor-widget.${type} .widget-value`);
        widgets.forEach(widget => {
            widget.innerHTML = `${value.toFixed(1)}<span class="widget-unit">${unit}</span>`;
        });
    }

    // 차트 데이터 업데이트 (그룹별)
    updateChartData(sensorType, value, timestamp) {
        // 해당 센서 타입의 모든 차트 업데이트
        Object.entries(this.charts).forEach(([chartId, chart]) => {
            if (chartId.includes(sensorType)) {
                const data = chart.data;
                
                // 메모리 최적화: 최대 데이터 포인트 제한
                if (data.labels.length >= this.config.maxDataPoints) {
                    data.labels.shift();
                    data.datasets[0].data.shift();
                }

                data.labels.push(timestamp.toLocaleTimeString('ko-KR', { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    second: '2-digit'
                }));
                data.datasets[0].data.push(value);
                
                chart.update('none'); // 애니메이션 없이 업데이트
            }
        });
    }

    // 상태바 업데이트
    updateStatusBar() {
        const now = new Date();
        const timeString = now.toLocaleString('ko-KR', {
            year: 'numeric',
            month: 'numeric', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = `마지막 업데이트: ${timeString}`;
        }
        
        const dbStatusElement = document.getElementById('db-status');
        if (dbStatusElement) {
            dbStatusElement.textContent = `데이터베이스 상태: 연결됨`;
        }
    }

    // 로딩 숨김
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            setTimeout(() => {
                overlay.style.opacity = '0';
                setTimeout(() => overlay.remove(), 300);
            }, 500);
        }
    }
}

// 문서 로드 완료 후 대시보드 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new EGIconDashboard();
});

// 페이지 언로드 시 리소스 정리 (메모리 최적화)
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        Object.values(window.dashboard.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        if (window.dashboard.ws) {
            window.dashboard.ws.close();
        }
        if (window.dashboard.mockDataInterval) {
            clearInterval(window.dashboard.mockDataInterval);
        }
    }
});