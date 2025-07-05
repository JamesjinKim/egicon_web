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

        // 센서 그룹 정의 (통합보기 기준)
        this.sensorGroups = {
            "temp-humidity": {
                title: "온습도 센서",
                icon: "🌡️💧",
                metrics: ["temperature", "humidity"],
                sensors: {
                    // BME688 센서 6개 (CH2 채널 0-5)
                    bme688: ["bme688_1_0", "bme688_1_1", "bme688_1_2", "bme688_1_3", "bme688_1_4", "bme688_1_5"],
                    // SHT40 센서 1개 (CH1 채널 0)  
                    sht40: ["sht40_0_0"]
                },
                totalSensors: 7,
                containerId: "temp-humidity-widgets"
            },
            "pressure": {
                title: "압력 센서",
                icon: "📏",
                metrics: ["pressure", "airquality"],
                sensors: {
                    // BME688 센서 6개에서 압력 데이터
                    bme688: ["bme688_1_0", "bme688_1_1", "bme688_1_2", "bme688_1_3", "bme688_1_4", "bme688_1_5"]
                },
                totalSensors: 6,
                containerId: "pressure-widgets"
            },
            "light": {
                title: "조도 센서",
                icon: "☀️",
                metrics: ["light"],
                sensors: {
                    // BH1750 센서 2개 (CH2 채널 3, 5)
                    bh1750: ["bh1750_1_3", "bh1750_1_5"]
                },
                totalSensors: 2,
                containerId: "light-widgets"
            },
            "vibration": {
                title: "진동 센서",
                icon: "〜",
                metrics: ["vibration"],
                sensors: {
                    // 진동센서 준비 중
                },
                totalSensors: 0,
                containerId: "vibration-widgets"
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
        
        // 동적 센서 그룹 로드 (새로운 기능)
        await this.loadSensorGroups();
        
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

    // 동적 센서 그룹 로드
    async loadSensorGroups() {
        try {
            console.log('🔍 동적 센서 그룹 로딩 중...');
            
            const response = await fetch('/api/sensors/groups');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const dynamicGroups = await response.json();
            console.log('📡 동적 센서 그룹 데이터:', dynamicGroups);
            
            // 기존 하드코딩된 그룹을 동적 그룹으로 교체
            this.updateSensorGroupsFromAPI(dynamicGroups);
            
            // HTML 구조 동적 업데이트
            this.buildDynamicSensorGroups(dynamicGroups);
            
            console.log('✅ 동적 센서 그룹 로딩 완료');
            
        } catch (error) {
            console.warn('⚠️ 동적 센서 그룹 로딩 실패, 하드코딩 모드 사용:', error);
            // 실패 시 기존 하드코딩된 그룹 사용
            this.generateMockSensors();
        }
    }

    // API에서 받은 그룹 데이터로 sensorGroups 업데이트
    updateSensorGroupsFromAPI(apiResponse) {
        console.log('🔍 API 응답 구조 확인:', apiResponse);
        
        // API 응답에서 groups 데이터 추출
        const dynamicGroups = apiResponse.groups || apiResponse;
        
        if (!dynamicGroups || typeof dynamicGroups !== 'object') {
            console.error('❌ 잘못된 API 응답 구조:', apiResponse);
            return;
        }
        
        Object.entries(dynamicGroups).forEach(([groupName, groupData]) => {
            if (this.sensorGroups[groupName] && groupData.sensors) {
                // 기존 그룹 구조 유지하되 동적 데이터로 업데이트
                this.sensorGroups[groupName] = {
                    ...this.sensorGroups[groupName],
                    totalSensors: groupData.count || groupData.sensors.length,
                    sensors: this.extractSensorIds(groupData.sensors),
                    dynamicConfig: {
                        statusText: `${groupData.count || 0}개 연결됨`,
                        typesSummary: this.generateTypesSummary(groupData.sensors),
                        isOnline: (groupData.count || 0) > 0
                    }
                };
                
                // 연결된 센서 목록 업데이트
                groupData.sensors.forEach(sensor => {
                    const sensorId = sensor.sensor_name || sensor.sensor_type || 'unknown';
                    this.connectedSensors.add(`${sensorId}_${sensor.bus}_${sensor.mux_channel}`);
                });
                
                console.log(`📊 그룹 ${groupName} 업데이트: ${groupData.count}개 센서`);
            }
        });
        
        console.log('📊 센서 그룹 업데이트 완료:', this.sensorGroups);
    }

    // 센서 데이터에서 센서 ID 목록 추출
    extractSensorIds(sensors) {
        const sensorIds = {};
        
        if (!Array.isArray(sensors)) {
            console.warn('⚠️ sensors가 배열이 아닙니다:', sensors);
            return sensorIds;
        }
        
        sensors.forEach(sensor => {
            const sensorType = (sensor.sensor_type || sensor.type || 'unknown').toLowerCase();
            if (!sensorIds[sensorType]) {
                sensorIds[sensorType] = [];
            }
            
            // 센서 ID 생성 (센서명_버스_채널)
            const sensorId = `${sensorType}_${sensor.bus}_${sensor.mux_channel}`;
            sensorIds[sensorType].push(sensorId);
        });
        
        return sensorIds;
    }
    
    // 센서 타입 요약 생성
    generateTypesSummary(sensors) {
        if (!Array.isArray(sensors)) {
            return "센서 없음";
        }
        
        const typeCounts = {};
        sensors.forEach(sensor => {
            const type = sensor.sensor_type || sensor.type || 'Unknown';
            typeCounts[type] = (typeCounts[type] || 0) + 1;
        });
        
        return Object.entries(typeCounts)
            .map(([type, count]) => `${type}×${count}`)
            .join(' + ');
    }

    // HTML 구조를 동적으로 업데이트
    buildDynamicSensorGroups(apiResponse) {
        console.log('🏗️ HTML 구조 동적 업데이트 시작:', apiResponse);
        
        // API 응답에서 groups 데이터 추출
        const dynamicGroups = apiResponse.groups || apiResponse;
        
        if (!dynamicGroups || typeof dynamicGroups !== 'object') {
            console.error('❌ buildDynamicSensorGroups: 잘못된 데이터 구조');
            return;
        }
        
        Object.entries(dynamicGroups).forEach(([groupName, groupData]) => {
            if (!groupData || !groupData.sensors) {
                console.warn(`⚠️ 그룹 ${groupName}에 센서 데이터가 없습니다`);
                return;
            }
            this.updateGroupHeader(groupName, groupData);
            this.updateGroupCharts(groupName, groupData);
            
            // 초기 센서 상태 설정 (한 번만 실행)
            this.initializeSensorStatus(groupName, groupData);
        });
    }

    // 초기 센서 상태 설정
    initializeSensorStatus(groupName, groupData) {
        console.log(`🔧 초기 센서 상태 설정: ${groupName} - ${groupData.total_count}개 센서`);
        
        // 그룹별 상태 엘리먼트 업데이트
        if (groupName === 'temp-humidity') {
            const groupStatusElement = document.getElementById('temp-humidity-status');
            if (groupStatusElement) {
                const activeCount = groupData.active_count || groupData.total_count;
                const totalCount = groupData.total_count;
                groupStatusElement.textContent = `${activeCount}/${totalCount} 활성`;
                console.log(`✅ 온습도 그룹 상태 초기 설정: ${activeCount}/${totalCount} 활성`);
            }
        } else if (groupName === 'pressure') {
            const groupStatusElement = document.getElementById('pressure-status');
            if (groupStatusElement) {
                const activeCount = groupData.active_count || groupData.total_count;
                const totalCount = groupData.total_count;
                groupStatusElement.textContent = `${activeCount}/${totalCount} 활성`;
                console.log(`✅ 압력 그룹 상태 초기 설정: ${activeCount}/${totalCount} 활성`);
            }
        } else if (groupName === 'light') {
            const groupStatusElement = document.getElementById('light-status');
            if (groupStatusElement) {
                const activeCount = groupData.active_count || groupData.total_count;
                const totalCount = groupData.total_count;
                groupStatusElement.textContent = `${activeCount}/${totalCount} 활성`;
                console.log(`✅ 조도 그룹 상태 초기 설정: ${activeCount}/${totalCount} 활성`);
            }
        }
    }

    // 그룹 헤더 정보 업데이트
    updateGroupHeader(groupName, groupData) {
        const groupElement = document.querySelector(`[data-group="${groupName}"]`);
        if (!groupElement) {
            // 그룹 엘리먼트가 없으면 기존 방식으로 찾기
            return this.updateGroupHeaderByClass(groupName, groupData);
        }
        
        // 상태 텍스트 업데이트
        const statusElement = groupElement.querySelector('.sensor-group-status');
        if (statusElement) {
            statusElement.textContent = groupData.status_text;
            statusElement.className = `sensor-group-status ${groupData.status}`;
        }
        
        // 타입 요약 업데이트
        const summaryElement = groupElement.querySelector('.summary-item');
        if (summaryElement) {
            summaryElement.textContent = groupData.types_summary;
        }
    }

    // 클래스 기반으로 그룹 헤더 업데이트 (폴백)
    updateGroupHeaderByClass(groupName, groupData) {
        // 온습도 센서 그룹
        if (groupName === 'temp-humidity') {
            const statusElement = document.querySelector('.sensor-group .sensor-group-status');
            if (statusElement) {
                statusElement.textContent = groupData.status_text;
                statusElement.className = `sensor-group-status ${groupData.status}`;
            }
            
            const summaryElement = document.querySelector('.sensor-group .summary-item');
            if (summaryElement) {
                summaryElement.textContent = groupData.types_summary;
            }
        }
        
        // 다른 그룹들도 필요시 추가
    }

    // 그룹별 차트 라벨 동적 업데이트
    updateGroupCharts(groupName, groupData) {
        console.log(`🔄 그룹 ${groupName} 차트 업데이트:`, groupData);
        
        if (!groupData.sensors || !Array.isArray(groupData.sensors)) {
            console.warn(`⚠️ 그룹 ${groupName}의 센서 데이터가 배열이 아닙니다:`, groupData.sensors);
            return;
        }
        
        // 센서 라벨 생성
        const sensorLabels = groupData.sensors.map(sensor => {
            const busLabel = sensor.bus === 0 ? 'CH1' : 'CH2';
            const sensorType = sensor.sensor_type || sensor.type || 'Unknown';
            const channel = sensor.mux_channel !== undefined ? sensor.mux_channel : sensor.channel;
            return `${sensorType} ${busLabel}-Ch${channel}`;
        });
        
        // 해당 그룹의 메트릭별로 차트 업데이트
        const group = this.sensorGroups[groupName];
        if (group && group.metrics) {
            group.metrics.forEach(metric => {
                const chartId = `${metric}-multi-chart`;
                if (this.charts[chartId]) {
                    this.updateChartLabels(chartId, sensorLabels);
                }
            });
        }
    }

    // 차트 라벨 동적 업데이트
    updateChartLabels(chartId, newLabels) {
        const chart = this.charts[chartId];
        if (!chart) return;
        
        // 기존 데이터셋 수와 새 라벨 수가 다르면 차트 재생성
        if (chart.data.datasets.length !== newLabels.length) {
            console.log(`🔄 차트 ${chartId} 재생성 중 (${chart.data.datasets.length} -> ${newLabels.length})`);
            this.recreateChart(chartId, newLabels);
        } else {
            // 라벨만 업데이트
            chart.data.datasets.forEach((dataset, index) => {
                if (newLabels[index]) {
                    dataset.label = newLabels[index];
                }
            });
            chart.update();
        }
    }

    // 차트 재생성
    recreateChart(chartId, sensorLabels) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;
        
        // 기존 차트 삭제
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
            delete this.charts[chartId];
        }
        
        // 센서 타입 추출 (차트 ID에서)
        const sensorType = chartId.replace('-multi-chart', '');
        
        // 새 차트 생성
        this.createMultiSensorChart(chartId, sensorType, sensorLabels);
    }

    // Mock 센서 생성 (그룹 기준)
    generateMockSensors() {
        console.log('🔧 Mock 센서 생성 중...');
        
        // 각 그룹의 센서들을 connectedSensors에 추가
        Object.values(this.sensorGroups).forEach(group => {
            if (group.sensors && typeof group.sensors === 'object') {
                // sensors가 객체인 경우 (센서 타입별로 분류된 경우)
                Object.values(group.sensors).forEach(sensorArray => {
                    if (Array.isArray(sensorArray)) {
                        sensorArray.forEach(sensorId => {
                            this.connectedSensors.add(sensorId);
                        });
                    }
                });
            } else if (Array.isArray(group.sensors)) {
                // sensors가 배열인 경우
                group.sensors.forEach(sensorId => {
                    this.connectedSensors.add(sensorId);
                });
            }
        });
        
        console.log('✅ Mock 센서 생성 완료:', this.connectedSensors.size, '개');
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

    // 차트 초기화 (동적 센서 그룹 지원)
    initCharts() {
        // 동적 센서 그룹이 로드된 후 차트 생성
        this.createChartsFromSensorGroups();
    }

    // 센서 그룹 기반 차트 생성
    createChartsFromSensorGroups() {
        Object.entries(this.sensorGroups).forEach(([groupName, group]) => {
            if (group.totalSensors > 0) {
                // 각 메트릭별로 차트 생성
                group.metrics.forEach(metric => {
                    const chartId = `${metric}-multi-chart`;
                    const sensorLabels = this.generateSensorLabels(group, metric);
                    
                    if (sensorLabels.length > 1) {
                        // 멀티 센서 차트
                        this.createMultiSensorChart(chartId, metric, sensorLabels);
                    } else if (sensorLabels.length === 1) {
                        // 단일 센서 차트
                        this.createGroupChart(chartId, metric, sensorLabels[0]);
                    }
                });
            }
        });
    }

    // 센서 그룹에서 라벨 생성
    generateSensorLabels(group, metric) {
        const labels = [];
        
        // 동적 구성이 있으면 사용
        if (group.dynamicConfig && group.sensors) {
            Object.values(group.sensors).forEach(sensorList => {
                if (Array.isArray(sensorList)) {
                    sensorList.forEach((sensorId, index) => {
                        // 센서 ID에서 타입과 채널 정보 추출
                        const parts = sensorId.split('_');
                        if (parts.length >= 3) {
                            const sensorType = parts[0].toUpperCase();
                            const bus = parseInt(parts[1]);
                            const channel = parseInt(parts[2]);
                            const busLabel = bus === 0 ? 'CH1' : 'CH2';
                            labels.push(`${sensorType} ${busLabel}-Ch${channel}`);
                        } else {
                            // 폴백: 기본 라벨
                            labels.push(`${group.title} ${index + 1}`);
                        }
                    });
                }
            });
        } else {
            // 기존 하드코딩 방식 (폴백)
            return this.generateFallbackLabels(group, metric);
        }
        
        return labels;
    }

    // 폴백 라벨 생성 (동적 센서 구성 기반)
    generateFallbackLabels(group, metric) {
        const labels = [];
        
        // 동적 센서 구성이 있으면 사용
        if (group.sensors && typeof group.sensors === 'object') {
            // 센서 타입별로 분류된 경우
            Object.entries(group.sensors).forEach(([sensorType, sensorList]) => {
                if (Array.isArray(sensorList)) {
                    sensorList.forEach((sensorId) => {
                        // 센서 ID에서 라벨 생성 (예: bme688_1_0 -> BME688 CH2-Ch0)
                        const parts = sensorId.split('_');
                        if (parts.length >= 3) {
                            const type = parts[0].toUpperCase();
                            const bus = parseInt(parts[1]);
                            const channel = parseInt(parts[2]);
                            const busLabel = bus === 0 ? 'CH1' : 'CH2';
                            labels.push(`${type} ${busLabel}-Ch${channel}`);
                        } else {
                            labels.push(`${sensorType.toUpperCase()} 센서`);
                        }
                    });
                }
            });
        }
        
        // 동적 구성이 없거나 비어있으면 기본 라벨
        if (labels.length === 0) {
            switch (metric) {
                case 'temperature':
                case 'humidity':
                    return ['온습도 센서 1', '온습도 센서 2', '온습도 센서 3'];
                case 'pressure':
                case 'airquality':
                    return ['압력 센서 1', '압력 센서 2'];
                case 'light':
                    return ['조도 센서 1', '조도 센서 2'];
                case 'vibration':
                    return ['진동 센서'];
                default:
                    return [`${group.title} 센서`];
            }
        }
        
        return labels;
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

    // Multi-line 차트 생성 (복수 센서 통합)
    createMultiSensorChart(canvasId, sensorType, sensorLabels) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const sensorConfig = this.sensorTypes[sensorType];
        
        // 색상 팔레트 정의 (센서별 구분)
        const colorPalette = [
            '#ff6384', '#36a2eb', '#4bc0c0', '#ff9f40', 
            '#9966ff', '#ffcd56', '#c9cbcf', '#ff6384'
        ];
        
        // 각 센서별 데이터셋 생성
        const datasets = sensorLabels.map((label, index) => {
            const color = colorPalette[index % colorPalette.length];
            return {
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
        });

        this.charts[canvasId] = new Chart(ctx, {
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
                        position: 'top',
                        labels: {
                            boxWidth: 20,
                            padding: 15,
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#333',
                        bodyColor: '#666',
                        borderColor: '#ddd',
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}${sensorConfig.unit}`;
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
                            maxTicksLimit: 8,
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
                    duration: 300
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    // 색상 팔레트 반환
    getColorPalette(index) {
        const colors = [
            '#ff6384', '#36a2eb', '#4bc0c0', '#ff9f40', 
            '#9966ff', '#ffcd56', '#c9cbcf', '#ff6384'
        ];
        return colors[index % colors.length];
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
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log('🔗 WebSocket 연결 시도:', wsUrl);
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
            console.error('📡 WebSocket 연결 오류:', {
                url: wsUrl,
                error: error,
                readyState: this.ws.readyState
            });
            this.attemptReconnect();
        };
    }

    // 실시간 데이터 처리 (BME688 세분화 센서 지원)
    handleRealtimeData(sensorData) {
        const now = new Date();
        
        // 센서 타입별 데이터 그룹화
        const groupedData = {
            temperature: [],
            humidity: [],
            pressure: [],
            light: []
        };
        
        // sensorData가 배열인지 객체인지 확인
        let dataArray = [];
        if (Array.isArray(sensorData)) {
            dataArray = sensorData;
        } else if (typeof sensorData === 'object') {
            dataArray = Object.entries(sensorData).map(([id, data]) => ({
                sensorId: id,
                ...data
            }));
        }
        
        // WebSocket 데이터 처리 및 그룹화
        dataArray.forEach((data) => {
            // SPS30 센서 데이터 처리
            if (data.sensor_type === 'SPS30' && data.interface === 'UART') {
                this.updateSPS30Data(data);
                return;
            }
            
            // 기존 I2C 센서 데이터 처리
            const sensorId = data.sensorId || data.sensor_id;
            if (sensorId) {
                this.connectedSensors.add(sensorId);
                
                // 서버에서 오는 데이터 구조 처리
                // 각 센서 타입별로 개별 메트릭을 추출
                ['temperature', 'humidity', 'pressure', 'light'].forEach(metric => {
                    if (data[metric] !== undefined) {
                        const sensorIndex = this.extractSensorIndex(sensorId);
                        
                        groupedData[metric].push({
                            sensorId: sensorId,
                            value: data[metric],
                            sensorIndex: sensorIndex,
                            timestamp: now
                        });
                        
                        console.log(`📊 실시간 데이터: ${sensorId} ${metric} = ${data[metric]} (인덱스: ${sensorIndex})`);
                    }
                });
            }
        });
        
        // 그룹별 차트 및 위젯 업데이트
        Object.entries(groupedData).forEach(([metric, sensorDataArray]) => {
            if (sensorDataArray.length > 0) {
                console.log(`🔍 그룹 데이터 처리: ${metric} - ${sensorDataArray.length}개 센서`);
                
                // Multi-line 차트 업데이트
                this.updateMultiSensorChartRealtime(metric, sensorDataArray, now);
                
                // 센서 타입에 맞는 그룹 매핑
                const groupName = this.getGroupNameForMetric(metric);
                if (groupName) {
                    console.log(`📋 그룹 매핑: ${metric} → ${groupName}`);
                    // 실시간 업데이트에서는 상태 업데이트 건너뛰기 (skipStatusUpdate = true)
                    this.updateSummaryWidgets(groupName, metric, sensorDataArray, true);
                } else {
                    console.warn(`⚠️ 그룹 매핑 실패: ${metric}`);
                }
            }
        });
        
        this.updateStatusBar();
    }

    // 실제 센서 데이터 가져오기
    async loadRealSensorData() {
        try {
            console.log('🔍 실제 센서 데이터 로딩 중...');
            
            const response = await fetch('/api/sensors');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const sensors = await response.json();
            console.log('📡 실제 센서 데이터:', sensors);
            
            if (sensors && Array.isArray(sensors) && sensors.length > 0) {
                // 실제 센서 데이터가 있으면 Mock 데이터와 병합
                this.mergeRealSensorData(sensors);
                console.log(`✅ 실제 센서 ${sensors.length}개 연결됨`);
            } else {
                console.log('⚠️ 실제 센서 데이터 없음, Mock 데이터 사용');
            }
            
        } catch (error) {
            console.error('❌ 실제 센서 데이터 로딩 실패:', error);
        }
    }

    // 실제 센서 데이터와 Mock 데이터 병합
    mergeRealSensorData(sensors) {
        if (!Array.isArray(sensors)) {
            console.error('❌ 센서 데이터가 배열이 아닙니다:', sensors);
            return;
        }
        
        sensors.forEach((sensor) => {
            // BH1750 조도 센서의 경우 light_1 위젯 교체
            if (sensor.sensor_type === 'BH1750') {
                const sensorId = `${sensor.sensor_type.toLowerCase()}_${sensor.bus}_${sensor.mux_channel || 0}`;
                
                // 기존 light_1 Mock 센서를 실제 센서로 교체
                this.replaceMockSensor('light_1', sensorId, sensor);
                
                // 위젯 제목 업데이트
                const widget = document.querySelector('[data-sensor="light_1"]');
                if (widget) {
                    const titleElement = widget.querySelector('.widget-title');
                    if (titleElement) {
                        titleElement.textContent = `BH1750 조도 (Bus${sensor.bus}:Ch${sensor.mux_channel})`;
                    }
                    // 실제 센서 ID로 data 속성 변경
                    widget.setAttribute('data-sensor', sensorId);
                    widget.setAttribute('data-real-sensor', 'true');
                }
            }
            
            // SPS30 공기질 센서 처리
            if (sensor.sensor_type === 'SPS30' && sensor.interface === 'UART') {
                console.log('📊 SPS30 공기질 센서 발견:', sensor);
                this.updateSPS30Status(sensor);
            }
        });
    }

    // SPS30 센서 상태 업데이트
    updateSPS30Status(sensor) {
        const statusElement = document.getElementById('sps30-status');
        if (statusElement) {
            statusElement.textContent = '1개 연결됨';
            statusElement.className = 'sensor-group-status online';
        }

        const modelElement = document.getElementById('sps30-model');
        if (modelElement) {
            modelElement.textContent = `SPS30 (${sensor.serial_number?.substring(0, 8) || 'UART'})`;
        }
    }

    // SPS30 실시간 데이터 처리
    updateSPS30Data(sensorData) {
        if (sensorData.sensor_type === 'SPS30' && sensorData.values) {
            const values = sensorData.values;
            
            // PM2.5 위젯 업데이트
            const pm25Element = document.getElementById('pm25-value');
            if (pm25Element) {
                pm25Element.textContent = `${values.pm25?.toFixed(1) || '--'} μg/m³`;
            }
            
            const pm25LevelElement = document.getElementById('pm25-level');
            if (pm25LevelElement) {
                pm25LevelElement.textContent = this.getAirQualityLevel(values.pm25);
            }

            // PM10 위젯 업데이트
            const pm10Element = document.getElementById('pm10-value');
            if (pm10Element) {
                pm10Element.textContent = `${values.pm10?.toFixed(1) || '--'} μg/m³`;
            }
            
            const pm10LevelElement = document.getElementById('pm10-level');
            if (pm10LevelElement) {
                pm10LevelElement.textContent = this.getAirQualityLevel(values.pm10);
            }

            // 공기질 등급 업데이트
            const qualityElement = document.getElementById('air-quality-grade');
            const descElement = document.getElementById('air-quality-desc');
            
            if (qualityElement && descElement) {
                const { grade, description } = this.getAirQualityInfo(values.pm25);
                qualityElement.textContent = grade;
                descElement.textContent = description;
            }

            // 메인 차트 업데이트 (있다면)
            this.updateSPS30MainChart(values);
            
            console.log('📊 SPS30 메인 위젯 업데이트:', values);
        }
    }

    // 공기질 등급 계산
    getAirQualityLevel(pmValue) {
        if (pmValue <= 15) return '좋음';
        else if (pmValue <= 35) return '보통';
        else if (pmValue <= 75) return '나쁨';
        else return '매우나쁨';
    }

    // 공기질 정보 반환
    getAirQualityInfo(pm25Value) {
        if (pm25Value <= 15) {
            return { grade: '좋음', description: '공기질이 좋습니다' };
        } else if (pm25Value <= 35) {
            return { grade: '보통', description: '민감한 사람은 주의하세요' };
        } else if (pm25Value <= 75) {
            return { grade: '나쁨', description: '외출 시 마스크 착용' };
        } else {
            return { grade: '매우나쁨', description: '외출을 자제하세요' };
        }
    }

    // SPS30 메인 차트 업데이트
    updateSPS30MainChart(values) {
        // 간단한 메인 차트가 있다면 업데이트
        const chart = Chart.getChart('sps30-main-chart');
        if (chart) {
            // 차트 데이터 업데이트 로직 구현
            console.log('📊 SPS30 메인 차트 업데이트');
        }
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
            const delay = 1000 * this.reconnectAttempts;
            console.log(`🔄 WebSocket 재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts} (${delay}ms 후)`);
            
            setTimeout(() => {
                console.log('🔗 WebSocket 재연결 실행 중...');
                this.connectWebSocket();
            }, delay);
        } else {
            console.error('❌ WebSocket 재연결 포기, 로컬 Mock 데이터로 전환');
            console.log('📊 서버 연결 없이 Mock 데이터 모드로 동작합니다');
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

    // Mock 데이터 업데이트 (Multi-line 차트 지원)
    updateMockData() {
        const now = new Date();
        
        // 센서 그룹별 데이터 생성 및 업데이트
        this.updateSensorGroupData('temp-humidity', now);
        this.updateSensorGroupData('pressure', now);
        this.updateSensorGroupData('light', now);
        this.updateSensorGroupData('vibration', now);

        this.updateStatusBar();
    }

    // 센서 그룹별 데이터 업데이트 (동적 센서 지원)
    updateSensorGroupData(groupName, timestamp) {
        const group = this.sensorGroups[groupName];
        if (!group) return;

        group.metrics.forEach(metric => {
            const sensorData = [];
            let sensorIndex = 0;

            // 동적 센서 구성 지원
            if (group.sensors && typeof group.sensors === 'object') {
                // 각 센서 타입별로 Mock 데이터 생성
                Object.values(group.sensors).forEach(sensorList => {
                    if (Array.isArray(sensorList)) {
                        sensorList.forEach(sensorId => {
                            const mockValue = this.generateMockValueForSensor(metric, sensorIndex, timestamp);
                            sensorData.push({
                                sensorId: sensorId,
                                value: mockValue,
                                sensorIndex: sensorIndex
                            });
                            sensorIndex++;
                        });
                    }
                });
            } else {
                // 폴백: 기본 센서 수 사용
                const defaultSensorCount = group.totalSensors || 1;
                for (let i = 0; i < defaultSensorCount; i++) {
                    const mockValue = this.generateMockValueForSensor(metric, i, timestamp);
                    sensorData.push({
                        sensorId: `${metric}_${i}`,
                        value: mockValue,
                        sensorIndex: i
                    });
                }
            }

            // 센서 데이터가 있을 때만 업데이트
            if (sensorData.length > 0) {
                // Multi-line 차트 업데이트
                this.updateMultiSensorChart(groupName, metric, sensorData, timestamp);
                
                // 요약 위젯 업데이트
                this.updateSummaryWidgets(groupName, metric, sensorData);
            }
        });
    }

    // 센서별 고유 Mock 값 생성
    generateMockValueForSensor(sensorType, sensorIndex, timestamp) {
        const timeMs = timestamp.getTime();
        const baseOffset = sensorIndex * 0.5; // 센서별 오프셋
        const phaseOffset = sensorIndex * Math.PI / 4; // 위상 차이
        
        switch (sensorType) {
            case 'temperature':
                return 22 + baseOffset + 3 * Math.sin(timeMs / 60000 + phaseOffset) + (Math.random() - 0.5) * 1;
            case 'humidity':
                return 60 + baseOffset * 2 + 10 * Math.sin(timeMs / 80000 + phaseOffset) + (Math.random() - 0.5) * 2;
            case 'pressure':
                return 1013 + baseOffset + 5 * Math.sin(timeMs / 120000 + phaseOffset) + (Math.random() - 0.5) * 1;
            case 'light':
                const hour = timestamp.getHours();
                const daylight = Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
                return daylight * 1000 + baseOffset * 100 + Math.random() * 100;
            case 'airquality':
                return 80 + baseOffset * 3 + 20 * Math.sin(timeMs / 180000 + phaseOffset) + (Math.random() - 0.5) * 10;
            case 'vibration':
                return Math.random() * 15 + (Math.random() > 0.9 ? Math.random() * 20 : 0);
            default:
                return Math.random() * 100;
        }
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
        let sensorType = this.getSensorTypeFromId(sensorId);
        
        if (!this.sensorTypes[sensorType]) {
            console.warn(`알 수 없는 센서 타입: ${sensorType} (ID: ${sensorId})`);
            return;
        }
        
        const unit = this.sensorTypes[sensorType].unit;
        
        // data-sensor 속성으로 특정 위젯 찾기 (더 정확한 매칭)
        const specificWidget = document.querySelector(`[data-sensor="${sensorId}"] .widget-value`);
        if (specificWidget) {
            specificWidget.innerHTML = `${value.toFixed(1)}<span class="widget-unit">${unit}</span>`;
            return;
        }
        
        // 타입별 위젯 찾기 (폴백)
        const widgets = document.querySelectorAll(`.sensor-widget.${sensorType} .widget-value`);
        widgets.forEach(widget => {
            widget.innerHTML = `${value.toFixed(1)}<span class="widget-unit">${unit}</span>`;
        });
    }

    // 센서 ID에서 센서 타입 추출 (BME688 세분화 지원)
    getSensorTypeFromId(sensorId) {
        // BME688 세분화 센서 처리
        if (sensorId.includes('_temp')) {
            return 'temperature';
        }
        if (sensorId.includes('_humidity')) {
            return 'humidity';
        }
        if (sensorId.includes('_pressure')) {
            return 'pressure';
        }
        
        // 기타 센서 타입
        if (sensorId.startsWith('bh1750_')) {
            return 'light';
        }
        if (sensorId.startsWith('sht40_')) {
            return 'temperature'; // SHT40은 기본적으로 온도
        }
        if (sensorId.startsWith('bme688_')) {
            return 'temperature'; // 기본값
        }
        
        // Mock 센서 ID (기존 방식)
        const [type] = sensorId.split('_');
        return type;
    }

    // 센서 ID에서 인덱스 추출 (차트 라인 매핑용)
    extractSensorIndex(sensorId) {
        // 동적 센서 구성에서 실제 센서 순서를 기반으로 인덱스 결정
        // 하드코딩된 채널 매핑 대신 실제 스캔된 센서 순서 사용
        
        // 현재 그룹의 센서 목록에서 해당 센서의 위치 찾기
        for (const [groupName, groupData] of Object.entries(this.sensorGroups)) {
            if (groupData.sensors && Array.isArray(groupData.sensors)) {
                const sensorIndex = groupData.sensors.findIndex(sensor => 
                    sensor === sensorId || sensor.sensor_id === sensorId
                );
                if (sensorIndex !== -1) {
                    return sensorIndex;
                }
            } else if (groupData.sensors && typeof groupData.sensors === 'object') {
                // 센서 타입별로 분류된 경우
                let globalIndex = 0;
                for (const [sensorType, sensorList] of Object.entries(groupData.sensors)) {
                    if (Array.isArray(sensorList)) {
                        const typeIndex = sensorList.indexOf(sensorId);
                        if (typeIndex !== -1) {
                            return globalIndex + typeIndex;
                        }
                        globalIndex += sensorList.length;
                    }
                }
            }
        }
        
        // 폴백: 센서 ID에서 채널 번호 사용 (기존 방식)
        const parts = sensorId.split('_');
        if (parts.length >= 3) {
            return parseInt(parts[2]);
        }
        
        return 0; // 기본값
    }

    // 센서 타입에서 그룹명 매핑
    getGroupNameForMetric(metric) {
        const metricToGroup = {
            'temperature': 'temp-humidity',
            'humidity': 'temp-humidity',
            'pressure': 'pressure',
            'light': 'light',
            'vibration': 'vibration',
            'airquality': 'pressure'
        };
        
        return metricToGroup[metric] || null;
    }

    // 실시간 Multi-line 차트 업데이트
    updateMultiSensorChartRealtime(metric, sensorDataArray, timestamp) {
        const chartId = `${metric}-multi-chart`;
        const chart = this.charts[chartId];
        
        if (!chart) {
            console.warn(`차트를 찾을 수 없음: ${chartId}`);
            return;
        }
        
        const data = chart.data;
        
        // 메모리 최적화: 최대 데이터 포인트 제한
        if (data.labels.length >= this.config.maxDataPoints) {
            data.labels.shift();
            data.datasets.forEach(dataset => dataset.data.shift());
        }
        
        // 시간 라벨 추가
        data.labels.push(timestamp.toLocaleTimeString('ko-KR', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        }));
        
        // 각 센서별 데이터 추가 (인덱스 매핑 사용)
        sensorDataArray.forEach((sensor) => {
            const datasetIndex = sensor.sensorIndex;
            if (data.datasets[datasetIndex]) {
                data.datasets[datasetIndex].data.push(sensor.value);
                console.log(`📈 차트 업데이트: ${metric} 인덱스 ${datasetIndex} = ${sensor.value}`);
            } else {
                console.warn(`데이터셋 인덱스 ${datasetIndex}를 찾을 수 없음 (${metric})`);
            }
        });
        
        // 빈 데이터셋에 null 추가 (라인 길이 맞춤)
        data.datasets.forEach((dataset, index) => {
            if (dataset.data.length < data.labels.length) {
                dataset.data.push(null);
            }
        });
        
        chart.update('none'); // 애니메이션 없이 업데이트
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

    // Multi-line 차트 업데이트
    updateMultiSensorChart(groupName, metric, sensorData, timestamp) {
        const chartId = `${metric}-multi-chart`;
        const chart = this.charts[chartId];
        
        if (!chart) return;
        
        const data = chart.data;
        
        // 메모리 최적화: 최대 데이터 포인트 제한
        if (data.labels.length >= this.config.maxDataPoints) {
            data.labels.shift();
            data.datasets.forEach(dataset => dataset.data.shift());
        }
        
        // 시간 라벨 추가
        data.labels.push(timestamp.toLocaleTimeString('ko-KR', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        }));
        
        // 각 센서별 데이터 추가
        sensorData.forEach((sensor, index) => {
            if (data.datasets[index]) {
                data.datasets[index].data.push(sensor.value);
            }
        });
        
        chart.update('none'); // 애니메이션 없이 업데이트
    }

    // 요약 위젯 업데이트 (실시간용 - 상태 제외)
    updateSummaryWidgets(groupName, metric, sensorData, skipStatusUpdate = false) {
        if (!sensorData || sensorData.length === 0) {
            console.warn(`⚠️ updateSummaryWidgets: 센서 데이터 없음 (${groupName}, ${metric})`);
            return;
        }
        
        // 안전한 숫자 값 추출 및 유효성 검사
        const values = sensorData.map(s => {
            const value = s.value || s.values || s;
            return typeof value === 'number' && !isNaN(value) ? value : 0;
        }).filter(val => typeof val === 'number' && !isNaN(val));
        
        if (values.length === 0) {
            console.warn(`⚠️ ${metric}: 유효한 숫자 데이터가 없습니다`);
            return;
        }
        
        const average = values.reduce((a, b) => a + b, 0) / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        
        const unit = this.sensorTypes[metric]?.unit || '';
        
        console.log(`📊 요약 위젯 업데이트: ${metric} - 평균: ${average.toFixed(1)}${unit}, 범위: ${min.toFixed(1)}~${max.toFixed(1)}${unit}, 센서수: ${sensorData.length}`);
        
        // pressure와 airquality는 메인 대시보드에서 제거되었으므로 스킵
        if (metric === 'pressure' || metric === 'airquality') {
            console.log(`⚠️ ${metric} 위젯은 메인 대시보드에서 제거되어 스킵합니다`);
            return;
        }
        
        // 평균값 업데이트
        const averageElement = document.getElementById(`${metric}-average`);
        if (averageElement) {
            averageElement.textContent = `${average.toFixed(1)}${unit}`;
            console.log(`✅ 평균값 업데이트 성공: ${metric}-average = ${average.toFixed(1)}${unit}`);
        } else {
            console.warn(`⚠️ 평균값 엘리먼트를 찾을 수 없음: ${metric}-average (정상적으로 제거된 위젯일 수 있습니다)`);
        }
        
        // 범위 업데이트
        const rangeElement = document.getElementById(`${metric}-range`);
        if (rangeElement) {
            rangeElement.textContent = `${min.toFixed(1)} ~ ${max.toFixed(1)}${unit}`;
            console.log(`✅ 범위 업데이트 성공: ${metric}-range = ${min.toFixed(1)} ~ ${max.toFixed(1)}${unit}`);
        } else {
            console.warn(`⚠️ 범위 엘리먼트를 찾을 수 없음: ${metric}-range (정상적으로 제거된 위젯일 수 있습니다)`);
        }
        
        // 상태 업데이트 (실시간에서는 스킵)
        if (!skipStatusUpdate) {
            const statusElement = document.getElementById(`${metric}-status`);
            if (statusElement) {
                const activeCount = sensorData.length;
                const totalCount = this.sensorGroups[groupName]?.totalSensors || activeCount;
                statusElement.textContent = `${activeCount}/${totalCount} 활성`;
            } else if (metric !== 'pressure' && metric !== 'airquality' && metric !== 'temperature' && metric !== 'humidity') {
                // 온습도 센서는 통합 상태만 있고 개별 상태 엘리먼트는 없음
                console.warn(`⚠️ 상태 엘리먼트를 찾을 수 없음: ${metric}-status`);
            }
            
            // 그룹 통합 상태 업데이트 (온습도 센서의 경우)
            if (groupName === 'temp-humidity') {
                const groupStatusElement = document.getElementById('temp-humidity-status');
                if (groupStatusElement && metric === 'temperature') {
                    // BME688 물리적 센서 수에 기반한 계산 (온도 센서 수 = 물리적 센서 수)
                    const physicalSensorCount = sensorData.length; // 온도 센서 7개 = 물리적 BME688 7개
                    const totalPhysicalSensors = this.sensorGroups[groupName]?.totalSensors || physicalSensorCount;
                    
                    groupStatusElement.textContent = `${physicalSensorCount}/${totalPhysicalSensors} 활성`;
                    console.log(`📊 온습도 그룹 상태 업데이트: ${physicalSensorCount}/${totalPhysicalSensors} (물리적 센서 기준)`);
                }
            }
        }
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